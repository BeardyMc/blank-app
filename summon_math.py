from pathlib import Path
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"

SUMMARY_COLS = [
    "player_name",
    "Skill ticket points without ascending",
    "Skill ticket points if ascend",
    "Egg Points from mergers",
    "Ascend pet tier",
    "Mount summon points without ascending",
    "Mount summon points if ascending",
    "Mount mergers if ascending",
]


def _prep_summon_table(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict]]:
  """Normalizes summon CSV columns and returns (sorted_df, level_lookup_dict)."""
  clean = df.copy()
  clean["Level"] = clean["Level"].astype(str).str.strip()
  clean["Summon"] = (
      pd.to_numeric(clean["Summon"], errors="coerce").fillna(0).astype(int)
  )
  clean["Total required"] = (
      pd.to_numeric(clean["Total required"], errors="coerce").fillna(0).astype(int)
  )
  clean = clean.sort_values("Total required").reset_index(drop=True)
  by_level = clean.set_index("Level").to_dict(orient="index")
  return clean, by_level


@st.cache_data
def load_summon_tables(
    data_dir: Path = DATA_DIR,
) -> dict[str, tuple[pd.DataFrame, dict[str, dict]]]:
  base = Path(data_dir)
  files = {
      "skill": base / "skill_summons.csv",
      "egg": base / "egg_summons.csv",
      "mount": base / "mount_summons.csv",
  }
  return {pillar: _prep_summon_table(pd.read_csv(path)) for pillar, path in files.items()}
 


def parse_current_summons(lvl_str: str, by_level: dict[str, dict]) -> tuple[int, dict]:
  """Converts '{level}_{summon}_{ascension}' into cumulative summons done so far.

    Matches '{level}_0_{ascension}' in 'Level'. If 'summon' is within [0, row['Summon']),
    adds 'summon' to 'Total required'; if 'summon' >= row['Summon'] (or invalid/at cap),
    resets summon offset to 0.
    """
  parts = str(lvl_str or "").strip().split("_")
  if len(parts) != 3:
    anchor_row = by_level.get("1_0_0", {"Summon": 0, "Total required": 0})
    return 0, anchor_row

  lvl, raw_summon, asc = parts[0].strip(), parts[1].strip(), parts[2].strip()
  try:
    summon_offset = int(raw_summon)
  except ValueError:
    summon_offset = 0

  anchor_key = f"{lvl}_0_{asc}"
  row = by_level.get(anchor_key)
  if row is None:
    anchor_row = by_level.get("1_0_0", {"Summon": 0, "Total required": 0})
    return 0, anchor_row

  step_cap = int(row["Summon"])
  base_total = int(row["Total required"])

  # Sanity check: only add summon_offset if strictly less than summons required in this level
  valid_offset = summon_offset if 0 <= summon_offset < step_cap else 0
  current_total_summons = base_total + valid_offset
  return current_total_summons, row


def find_reached_row(target_summons: int, sorted_df: pd.DataFrame) -> pd.Series:
  """Finds the highest CSV row whose 'Total required' is <= target_summons."""
  reached = sorted_df[sorted_df["Total required"] <= max(0, int(target_summons))]
  if reached.empty:
    return sorted_df.iloc[0]
  return reached.iloc[-1]
