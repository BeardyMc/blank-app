import math
import re
from typing import Optional
import pandas as pd
from rapidocr_onnxruntime import RapidOCR
import streamlit as st

RAW_MULTIPLIERS = {
    "": 1.0,
    "k": 1e3,
    "m": 1e6,
    "b": 1e9,
    "t": 1e12,
    "q": 1e15,
}

RANK_MAP = {
    "leader": "Leader",
    "commander": "Commander",
    "captain": "Captain",
    "r1": "r1",
    "r2": "r2",
    "r3": "r3",
    "r4": "r4",
    "r5": "r5",
}

# Extracts power like "91b", "74.9b", "34.7t" even after stray icon chars like "X" or ","
POWER_EXTRACT_RE = re.compile(
    r"(?<![a-zA-Z]{2})(?<![\d.])(\d+(?:[.,]\d+)?)\s*([kmbtrqKMBTRQ])(?![a-zA-Z])"
)

# Timestamp / UI noise patterns
TIMESTAMP_RE = re.compile(
    r"^(\d+\s*[smhd]\s*ago|[a-z]*\s*ago|\d+\s*[smhd])$",
    re.IGNORECASE,
)
IGNORE_TEXT_RE = re.compile(
    r"^(war progress|day\s*\d+|tier-|total\s*power|clan\s*tech|members:|"
    r"members|missions|war|online|offline|[+\-]?\d+|l\+|x)$",
    re.IGNORECASE,
)


@st.cache_resource
def get_rapidocr_engine() -> RapidOCR:
  """Caches the RapidOCR ONNX model so subsequent screenshot reads are near-instant."""
  return RapidOCR()


def parse_power_to_raw(raw_val) -> Optional[float]:
  """Converts strings like '850m', '91b', '74.9b', or '34.7t' into raw numeric power."""
  if raw_val is None:
    return None
  if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
    return None if math.isnan(float(raw_val)) else float(raw_val)

  text = str(raw_val).strip().replace(",", ".")
  match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]*)$", text)
  if not match:
    return None

  num = float(match.group(1))
  suffix = match.group(2).lower()
  if suffix == "r":
    suffix = "b"
  if suffix not in RAW_MULTIPLIERS:
    return None

  return round(num * RAW_MULTIPLIERS[suffix], 2)


def _box_metrics(box: list[list[float]]) -> tuple[float, float, float]:
  """Returns (x_left, y_center, height) for a 4-point OCR bounding box."""
  xs = [pt[0] for pt in box]
  ys = [pt[1] for pt in box]
  x_left = min(xs)
  y_min, y_max = min(ys), max(ys)
  return x_left, (y_min + y_max) / 2.0, max(y_max - y_min, 1.0)


def _group_detections_into_rows(
    detections: list, y_tolerance_ratio: float = 0.45
) -> list[list[dict]]:
  """Clusters OCR detections that share the same horizontal band into sorted rows."""
  items = []
  for det in detections:
    box, text, conf = det[0], str(det[1]).strip(), float(det[2])
    if not text:
      continue
    x_left, y_center, height = _box_metrics(box)
    items.append({
        "text": text,
        "conf": conf,
        "x": x_left,
        "y": y_center,
        "h": height,
    })

  items.sort(key=lambda d: d["y"])

  rows: list[list[dict]] = []
  for item in items:
    placed = False
    for row in rows:
      avg_y = sum(d["y"] for d in row) / len(row)
      avg_h = sum(d["h"] for d in row) / len(row)
      if abs(item["y"] - avg_y) <= avg_h * y_tolerance_ratio:
        row.append(item)
        placed = True
        break
    if not placed:
      rows.append([item])

  for row in rows:
    row.sort(key=lambda d: d["x"])
  return rows


def _clean_player_name(raw_name: str) -> str:
  """Trims stray icon characters and outer punctuation from OCR name text."""
  cleaned = raw_name.strip()
  # Remove trailing single-char icon misreads like "Boloo o", "03FireFly04 d", "LD0113 0"
  cleaned = re.sub(r"\s+[od0]$", "", cleaned, flags=re.IGNORECASE).strip()
  cleaned = re.sub(r"^[,;:\-•]+\s*|\s*[,;:\-•]+$", "", cleaned).strip()
  return cleaned


def _extract_power_from_token(text: str) -> Optional[str]:
  """Extracts normalized '<number><unit>' from a token if it represents player power."""
  compact = text.replace(" ", "")
  # Avoid matching clan header like "TotalPower:34.7t"
  if "totalpower" in compact.lower():
    return None
  # Strip a single leading icon letter + optional punctuation, e.g. "X74.9b" -> "74.9b"
  compact = re.sub(r"^[a-zA-Z]?[,.;:+\-•]*", "", compact)
  m = POWER_EXTRACT_RE.search(compact)
  if not m:
    return None
  num_part = m.group(1).replace(",", ".")
  unit_part = m.group(2).lower()
  if unit_part == "r":
    unit_part = "b"
  return f"{num_part}{unit_part}"


def _parse_cards_from_rows(grouped_rows: list[list[dict]]) -> list[dict]:
  """Pairs each power row with its above player name row and nearby right-side rank."""
  row_records = []
  for idx, tokens in enumerate(grouped_rows):
    avg_y = sum(t["y"] for t in tokens) / len(tokens)
    power_val = None
    rank_val = ""
    name_parts = []

    for t in tokens:
      txt = t["text"].strip()
      if not txt:
        continue

      p = _extract_power_from_token(txt)
      if p:
        power_val = p
        continue

      low = txt.lower().strip()
      if low in RANK_MAP:
        rank_val = RANK_MAP[low]
        continue

      if TIMESTAMP_RE.match(low) or IGNORE_TEXT_RE.match(low):
        continue

      # Ignore standalone numbers, punctuation, or signed badges like "+3" / "-1"
      if re.fullmatch(r"[+\-]?\d[\d,.\s]*", txt) or re.fullmatch(
          r"[,.;:+\-•]+", txt
      ):
        continue

      name_parts.append(txt)

    row_records.append({
        "idx": idx,
        "y": avg_y,
        "power_raw": power_val,
        "rank": rank_val,
        "name": _clean_player_name(" ".join(name_parts)),
    })

  results = []
  used_name_indices = set()

  for r_idx, rec in enumerate(row_records):
    if not rec["power_raw"]:
      continue

    # Scan all rows above this power row within ~15–90 px and pick the closest valid name
    best_name_idx = None
    best_dist = float("inf")
    for cand_idx in range(r_idx - 1, -1, -1):
      cand = row_records[cand_idx]
      dy = rec["y"] - cand["y"]
      if dy < 15:
        continue
      if dy > 90:
        break
      if cand["name"] and cand_idx not in used_name_indices and dy < best_dist:
        best_dist = dy
        best_name_idx = cand_idx

    if best_name_idx is None:
      continue

    used_name_indices.add(best_name_idx)
    player_name = row_records[best_name_idx]["name"]

    rank_val = rec["rank"]
    if not rank_val:
      for adj in row_records:
        if adj["rank"] and abs(adj["y"] - rec["y"]) <= 25:
          rank_val = adj["rank"]
          break

    results.append({
        "Include": True,
        "Player Name": player_name,
        "Rank": rank_val,
        "power": parse_power_to_raw(rec["power_raw"]),
        "Raw Extracted": rec["power_raw"],
    })

  return results


def extract_enemies_from_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
    return_debug: bool = False,
):
  """Runs RapidOCR on a screenshot and parses enemy roster rows into raw power dicts."""
  ocr = get_rapidocr_engine()
  result, _ = ocr(image_bytes)
  if not result:
    return ([], []) if return_debug else []

  grouped_rows = _group_detections_into_rows(result, y_tolerance_ratio=0.45)
  parsed_rows = _parse_cards_from_rows(grouped_rows)

  if return_debug:
    debug_lines = [
        " | ".join(f"{t['text']} (x={int(t['x'])}, y={int(t['y'])})" for t in r)
        for r in grouped_rows
    ]
    return parsed_rows, debug_lines

  return parsed_rows


def extract_enemies_batch(
    uploaded_files, return_debug: bool = False
) -> tuple[pd.DataFrame, list[str]]:
  """Processes multiple Streamlit UploadedFile objects and deduplicates by Player Name."""
  all_rows = []
  all_debug = []

  for f in uploaded_files:
    mime = f.type or "image/png"
    if return_debug:
      rows, dbg = extract_enemies_from_image(
          f.getvalue(), mime, return_debug=True
      )
      all_rows.extend(rows)
      all_debug.append(f"**{f.name}**")
      all_debug.extend(dbg)
    else:
      all_rows.extend(extract_enemies_from_image(f.getvalue(), mime))

  deduped = {}
  for r in all_rows:
    key = r["Player Name"].lower()
    if key not in deduped:
      deduped[key] = r
    elif deduped[key]["power"] is None and r["power"] is not None:
      deduped[key] = r

  df = pd.DataFrame(list(deduped.values()))
  return df, all_debug
