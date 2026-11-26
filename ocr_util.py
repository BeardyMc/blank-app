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

# Known rank labels/aliases seen in roster lists
RANK_MAP = {
    "leader": "Leader",
    "commander": "Commander",
    "captain": "Captain",
    "R1": "r1",
    "R2": "r2",
    "R3": "r3",
    "R4": "r4",
    "R5": "r5",
}

# Matches standalone or trailing rank tokens like "R4", "r4", "Leader", "Commander", "Captain"
TRAILING_RANK_RE = re.compile(
    r"^(.*?)\s*\b(leader|commander|captain|r[1-5])\b\s*$",
    re.IGNORECASE,
)

# Ignore clan summary / header lines
IGNORE_LINE_RE = re.compile(
    r"^(war progress|day \d+|tier-|total power|clan tech|members:|online|offline|\d+\s*[smhd]\s*ago)$",
    re.IGNORECASE,
)

# Match standalone power strings like 516t, 3.82t, 14b, 850m (avoid timestamps like 40m ago / 4h)
POWER_PATTERN = re.compile(r"^(\d+(?:[.,]\d+)?)\s*([kmbtqKMBTQ])$")
NOISE_PATTERN = re.compile(
    r"^(online|offline|\d+\s*[smhd]\s*ago|\d+\s*h|\d+\s*d|lv\.?\s*\d+)$",
    re.IGNORECASE,
)


@st.cache_resource
def get_rapidocr_engine() -> RapidOCR:
  """Caches the RapidOCR ONNX model so subsequent screenshot reads are near-instant."""
  return RapidOCR()


def parse_power_to_raw(raw_val) -> Optional[float]:
  """Converts strings like '850m', '436b', '3.82t', or '1.88q' into raw numeric power."""
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
    detections: list, y_tolerance_ratio: float = 0.65
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


def _parse_single_row(row_tokens: list[dict]) -> Optional[dict]:
  detected_power_raw = None
  detected_rank = ""
  name_candidates = []

  for tok in row_tokens:
    txt = tok["text"].strip()
    if not txt or IGNORE_LINE_RE.match(txt):
      continue

    lower_txt = txt.lower()
    if lower_txt in RANK_MAP:
      detected_rank = RANK_MAP[lower_txt]
      continue

    compact = txt.replace(" ", "")
    if POWER_PATTERN.match(compact):
      detected_power_raw = compact
      continue

    if compact.isdigit() and len(compact) <= 3:
      continue

    # If a rank got glued onto the end of a name token (e.g. "SharksL o R4")
    m_rank = TRAILING_RANK_RE.match(txt)
    if m_rank:
      prefix_name = m_rank.group(1).strip()
      rank_token = m_rank.group(2).lower()
      if rank_token in RANK_MAP and not detected_rank:
        detected_rank = RANK_MAP[rank_token]
      if prefix_name:
        name_candidates.append(prefix_name)
      continue

    name_candidates.append(txt)

  if not name_candidates or not detected_power_raw:
    return None

  player_name = " ".join(name_candidates).strip()
  return {
      "Include": True,
      "Player Name": player_name,
      "Rank": detected_rank,
      "power": parse_power_to_raw(detected_power_raw),
      "Raw Extracted": detected_power_raw,
  }


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

  grouped_rows = _group_detections_into_rows(result)
  parsed_rows = []
  for row_tokens in grouped_rows:
    parsed = _parse_single_row(row_tokens)
    if parsed:
      parsed_rows.append(parsed)

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
