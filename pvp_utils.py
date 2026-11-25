import base64
import json
import math
from pathlib import Path
import requests
import re
from datetime import datetime, timezone
import libsql
import pandas as pd
import streamlit as st

RESOURCE_COLUMNS = [
    "player_name",
    "damage_val",
    "health_val",
    "hammers",
    "skill_tickets",
    "skill_summon_cost",
    "skill_level",
    "pets_to_merge",
    "egg_summon_lvl",
    "egg_summon_chance",
    "mount_clockwinders",
    "mount_summon_lvl",
    "mount_cost_reduction",
    "mount_extra_chance",
    "clan_tech_vials",
    "Eggshells", 
    "updated_at",
]

_MULTIPLIERS = {
    "": 1.0,
    "k": 1e3,
    "m": 1e6,
    "b": 1e9,
    "t": 1e12,
    "q": 1e15,
}


CREATE_PLAYER_RESOURCES_SQL = """
CREATE TABLE IF NOT EXISTS player_resources (
    player_name TEXT PRIMARY KEY,
    damage_val REAL NOT NULL DEFAULT 0.0,
    health_val REAL NOT NULL DEFAULT 0.0,
    hammers INTEGER NOT NULL DEFAULT 0,
    skill_tickets INTEGER NOT NULL DEFAULT 0,
    skill_summon_cost INTEGER NOT NULL DEFAULT 0,
    skill_level TEXT NOT NULL DEFAULT "0_0_0",
    pets_to_merge INTEGER NOT NULL DEFAULT 0, 
    egg_summon_lvl TEXT NOT NULL DEFAULT "0_0_0",
    egg_summon_chance INTEGER NOT NULL DEFAULT 0,
    mount_clockwinders INTEGER NOT NULL DEFAULT 0,
    mount_summon_lvl TEXT NOT NULL DEFAULT "0_0_0",
    mount_cost_reduction INTEGER NOT NULL DEFAULT 0,
    mount_extra_chance INTEGER NOT NULL DEFAULT 0,
    clan_tech_vials INTEGER NOT NULL DEFAULT 0,
    Eggshells INTEGER NOT NULL DEFAULT 0
    updated_at TEXT NOT NULL
)
"""


def ensure_player_resources_table():
  """Creates player_resources in Turso if it doesn't exist yet."""
  conn = get_turso_conn()
  conn.execute(CREATE_PLAYER_RESOURCES_SQL)
  conn.commit()



def parse_stat_value(raw_value, default: float = 0.0) -> float:
  """Converts strings like '13b', '4.5t', '250m', or '13000000000' into a number."""
  if raw_value is None:
    return float(default)
  if isinstance(raw_value, (int, float)):
    return float(raw_value)

  text = str(raw_value).strip().lower().replace(",", "")
  if not text:
    return float(default)

  match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([a-z]*)", text)
  if not match:
    raise ValueError(f"Could not parse '{raw_value}'. Try something like 13b or 450m.")

  number = float(match.group(1))
  suffix = match.group(2)
  if suffix not in _MULTIPLIERS:
    raise ValueError(f"Unsupported suffix '{suffix}' in '{raw_value}'.")

  return number * _MULTIPLIERS[suffix]


def format_compact_input(val) -> str:
  """Formats a stored numeric stat for text_input prefill, e.g. 13000000000 -> '13b'."""
  if val is None or float(val) == 0.0:
    return "0"
  num = float(val)
  for suffix, mult in [
      ("q", 1e15),
      ("t", 1e12),
      ("b", 1e9),
      ("m", 1e6),
      ("k", 1e3),
  ]:
    if abs(num) >= mult:
      return f"{num / mult:g}{suffix}"
  return f"{num:g}"


@st.cache_resource
def get_turso_conn():
  db_url = st.secrets["TURSO_DATABASE_URL"]
  auth_token = st.secrets["TURSO_AUTH_TOKEN"]
  conn = libsql.connect(database=db_url, auth_token=auth_token)
  conn.execute(CREATE_PLAYER_RESOURCES_SQL)
  conn.commit()
  return conn


@st.cache_data(ttl=15)
def load_player_resources() -> pd.DataFrame:
  conn = get_turso_conn()
  cols_sql = ", ".join(RESOURCE_COLUMNS)
  rows = conn.execute(
      f"SELECT {cols_sql} FROM player_resources ORDER BY player_name ASC"
  ).fetchall()
  if not rows:
    return pd.DataFrame(columns=RESOURCE_COLUMNS)
  return pd.DataFrame(rows, columns=RESOURCE_COLUMNS)


def upsert_player_resources(data: dict):
  conn = get_turso_conn()
  now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  conn.execute(
      """
        INSERT INTO player_resources (
            player_name, damage_val, health_val,
            hammers, skill_tickets, skill_summon_cost, skill_level,
            egg_summon_lvl, egg_summon_chance, pets_to_merge,
            mount_summon_lvl, mount_clockwinders,     mount_cost_reduction,
            mount_extra_chance, clan_tech_vials, Eggshells, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET
            damage_val = excluded.damage_val,
            health_val = excluded.health_val,
            hammers = excluded.hammers,
            skill_tickets = excluded.skill_tickets,
            skill_summon_cost = excluded.skill_summon_cost,
            skill_level = excluded.skill_level,
            egg_summon_lvl = excluded.egg_summon_lvl,
            egg_summon_chance = excluded.egg_summon_chance,
            pets_to_merge = excluded.pets_to_merge,
            mount_summon_lvl = excluded.mount_summon_lvl,
            mount_clockwinders = excluded.mount_clockwinders,
            mount_cost_reduction = excluded.mount_cost_reduction,
            mount_extra_chance = excluded.mount_extra_chance,
            clan_tech_vials = excluded.clan_tech_vials,
            Eggshells = excluded.Eggshells
            updated_at = excluded.updated_at
        """,
      (
          data["player_name"],
          float(data["damage_val"]),
          float(data["health_val"]),
          int(data["hammers"]),
          int(data["skill_tickets"]),
          int(data["skill_summon_cost"]),
          (data["skill_level"]),
          (data["egg_summon_lvl"]),
          int(data["egg_summon_chance"]),
          int(data["pets_to_merge"]),
          (data["mount_summon_lvl"]),
          int(data["mount_clockwinders"]),
          int(data["mount_cost_reduction"]),
          int(data["mount_extra_chance"]),
          int(data["clan_tech_vials"]),
          int(data["Eggshells"]), 
          now_utc,
      ),
  )
  conn.commit()
  st.cache_data.clear()


def format_compact_input(val) -> str:
  """Formats a stored number for text_input prefill, e.g. 13000000000 -> '13b'."""
  if val is None or float(val) == 0:
    return "0"
  val = float(val)
  for suffix, mult in [
      ("q", 1e15),
      ("t", 1e12),
      ("b", 1e9),
      ("m", 1e6),
      ("k", 1e3),
  ]:
    if abs(val) >= mult:
      scaled = val / mult
      return f"{scaled:g}{suffix}"
  return f"{val:g}"


def parse_stat_value(raw_value, default: float = 0.0) -> float:
  """Converts strings like '13b', '4.5t', '250m', or '13000000000' into a float."""
  if raw_value is None:
    return float(default)
  if isinstance(raw_value, (int, float)):
    return float(raw_value)

  text = str(raw_value).strip().lower().replace(",", "")
  if not text:
    return float(default)

  # Match optional sign, number (int/float), and optional suffix
  match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([a-z]*)", text)
  if not match:
    raise ValueError(f"Invalid number format: '{raw_value}'")

  num = float(match.group(1))
  suffix = match.group(2)

  # Standard + game-friendly multipliers
  multipliers = {
      "": 1.0,
      "k": 1e3,
      "m": 1e6,
      "b": 1e9,
      "t": 1e12,
      "q": 1e15,
  }
  if suffix not in multipliers:
    raise ValueError(f"Unknown suffix '{suffix}' in '{raw_value}'")

  return num * multipliers[suffix]


BATTLE_COLS = [
    "attacker_side",
    "attacker",
    "defender_side",
    "defender",
    "winner_side",
    "winner",
    "loser_side",
    "loser",
]


def _get_jsonbin_config():
  """Returns `(url, headers)` from `st.secrets`, or `(None, None)` if missing."""
  try:
    api_key = st.secrets["JSONBIN_API_KEY"]
    bin_id = st.secrets["BIN_ID"]
  except (KeyError, FileNotFoundError):
    return None, None

  url = f"https://api.jsonbin.io/v3/b/{bin_id}"
  headers = {
      "X-Master-Key": api_key,
      "Content-Type": "application/json",
  }
  return url, headers


def get_visit_count():
  """Fetches the current visit count from JSONBin without modifying it."""
  url, headers = _get_jsonbin_config()
  if not url:
    return None

  try:
    resp = requests.get(
        url, headers={"X-Master-Key": headers["X-Master-Key"]}, timeout=5
    )
    resp.raise_for_status()
    record = resp.json().get("record", {})
    return int(record.get("visits", 0))
  except Exception as exc:
    print(f"JSONBin get visit count error: {exc}", flush=True)
    return None


def set_visit_count(new_value):
  """Writes an exact `visits` count to JSONBin and returns `new_value` on success."""
  url, headers = _get_jsonbin_config()
  if not url:
    return None

  try:
    clean_value = max(0, int(new_value))
    resp = requests.put(
        url,
        headers=headers,
        json={"visits": clean_value},
        timeout=5,
    )
    resp.raise_for_status()
    return clean_value
  except Exception as exc:
    print(f"JSONBin set visit count error: {exc}", flush=True)
    return None


def calc_effective_power(df, damage_lvl, health_lvl):
  """Computes Effective Power = Power (b) * (1 + (damage + health) / 2)."""
  if df is None or df.empty:
    return pd.DataFrame(
        columns=["Rank", "Player Name", "Power (b)", "Effective Power"]
    )
  out = df.copy()
  dmg = damage_lvl or 0
  hp = health_lvl or 0
  multiplier = 1.0 + (dmg + hp) / 2.0
  pwr = pd.to_numeric(out.get("Power (b)", 0.0), errors="coerce").fillna(0.0)
  out["Power (b)"] = pwr
  out["Effective Power"] = pwr * multiplier
  return out


def format_si_3sf(value):
  """Formats a number to 3 significant figures with custom unit suffixes."""
  if value is None or (isinstance(value, float) and math.isnan(value)):
    return "0b"
  if value == 0:
    return "0b"

  sign = "-" if value < 0 else ""
  abs_val = abs(float(value))

  units = [
      (12, "T"),
      (9, "B"),
      (6, "q"),
      (3, "t"),
      (0, "b"),
      (-3, "m"),
  ]

  chosen_exp, suffix = 0, "b"
  for exp, unit in units:
    if abs_val >= 10**exp:
      chosen_exp, suffix = exp, unit
      break

  scaled = abs_val / (10**chosen_exp)
  sf_scaled = round(scaled, 3 - 1 - math.floor(math.log10(scaled)))

  if sf_scaled >= 1000 and chosen_exp < 12:
    next_exp = chosen_exp + 3
    for exp, unit in units:
      if exp == next_exp:
        scaled = abs_val / (10**exp)
        sf_scaled = round(scaled, 3 - 1 - math.floor(math.log10(scaled)))
        suffix = unit
        break

  formatted_num = f"{sf_scaled:.3g}"
  return f"{sign}{formatted_num}{suffix}"


def sum_roster_power(df, power_col="Power (b)"):
  """Sums numeric power values safely, ignoring blank or non-numeric cells."""
  if df is None or df.empty or power_col not in df.columns:
    return 0.0
  return float(pd.to_numeric(df[power_col], errors="coerce").fillna(0.0).sum())


def format_df_powers(df, power_cols=("Power (b)", "Effective Power")):
  """Returns a copy of `df` with specified power columns formatted via `format_si_3sf`."""
  if df is None or df.empty:
    return df.copy() if df is not None else pd.DataFrame()

  out = df.copy()
  for col in power_cols:
    if col in out.columns:
      out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).apply(format_si_3sf)
  return out


def get_reset_threshold(enemy_count, buffer=5):
  """Returns defeats needed for a full reset (`total_enemies - 5`, min 1)."""
  return max(1, int(enemy_count) - int(buffer))


def simulate_battles(
    attackers_df,
    defenders_df,
    attacks_per_player=5,
    reset_threshold=43,
    safety_margin=1.0,
    points_multiplier=1.0,
):
  """Maximizes total points across reset cycles."""
  attackers = attackers_df.copy().reset_index(drop=True)
  attackers["eff_power"] = pd.to_numeric(
      attackers["Effective Power"], errors="coerce"
  ).fillna(0.0)
  attackers["attacks_left"] = attacks_per_player

  defenders = defenders_df.copy()
  defenders["eff_power"] = pd.to_numeric(
      defenders["Effective Power"], errors="coerce"
  ).fillna(0.0)
  defenders["pts"] = (
      pd.to_numeric(defenders["Points"], errors="coerce").fillna(0.0)
      if "Points" in defenders.columns
      else 0.0
  )
  defenders = defenders.sort_values(
      by=["pts", "eff_power"], ascending=[False, False]
  ).reset_index(drop=True)

  max_possible_battles = len(attackers) * attacks_per_player
  total_wins = 0
  total_points = 0.0
  cycles_completed = 0
  cycle_num = 1
  battle_log = []

  while attackers["attacks_left"].sum() > 0:
    cycle_matches = []

    for _, d_row in defenders.iterrows():
      if len(cycle_matches) >= reset_threshold:
        break

      d_power = d_row["eff_power"]
      d_pts = d_row["pts"]

      eligible = attackers[
          (attackers["attacks_left"] > 0)
          & ((attackers["eff_power"] * safety_margin) >= d_power)
      ]

      if eligible.empty:
        continue

      chosen_idx = eligible["eff_power"].idxmin()
      a_row = attackers.loc[chosen_idx]

      attackers.at[chosen_idx, "attacks_left"] -= 1
      gained_points = round(d_pts * points_multiplier)
      cycle_matches.append({
          "attacker_name": a_row["Player Name"],
          "attacker_power": a_row["eff_power"],
          "defender_name": d_row["Player Name"],
          "defender_power": d_power,
          "points": gained_points,
      })

    if not cycle_matches:
      break

    for m in cycle_matches:
      total_wins += 1
      total_points += m["points"]
      battle_log.append({
          "Battle #": total_wins,
          "Cycle": cycle_num,
          "Attacker": m["attacker_name"],
          "Attacker Eff Power": format_si_3sf(m["attacker_power"]),
          "Defender": m["defender_name"],
          "Defender Eff Power": format_si_3sf(m["defender_power"]),
          "Points Gained": m["points"],
      })

    if len(cycle_matches) >= reset_threshold:
      cycles_completed += 1
      cycle_num += 1
    else:
      break

  return {
      "total_wins": total_wins,
      "max_possible_battles": max_possible_battles,
      "total_points": total_points,
      "cycles_completed": cycles_completed,
      "log_df": pd.DataFrame(battle_log),
  }


def build_cycle_summary_tables(
    log_df, defenders_df, attackers_df, attacks_per_player=5
):
  """Builds cycle-by-defender and battle-by-attacker summary tables."""
  defender_names = (
      defenders_df["Player Name"].dropna().tolist()
      if defenders_df is not None and not defenders_df.empty
      else []
  )
  attacker_names = (
      attackers_df["Player Name"].dropna().tolist()
      if attackers_df is not None and not attackers_df.empty
      else []
  )

  battle_cols = [f"Battle {i}" for i in range(1, attacks_per_player + 1)]

  if log_df is None or log_df.empty:
    empty_enemies = pd.DataFrame({"Defender": defender_names})
    empty_attackers = pd.DataFrame([
        {
            "Attacker": a,
            "Attacks Used": 0,
            **{col: "" for col in battle_cols},
        }
        for a in attacker_names
    ])
    return empty_enemies, empty_attackers

  cycles = sorted(log_df["Cycle"].dropna().unique().tolist())
  cycle_cols = [f"Cycle {int(c)}" for c in cycles]

  all_defenders = list(
      dict.fromkeys(defender_names + log_df["Defender"].dropna().tolist())
  )
  enemy_rows = {d: {col: "" for col in cycle_cols} for d in all_defenders}

  all_attackers = list(
      dict.fromkeys(attacker_names + log_df["Attacker"].dropna().tolist())
  )
  attacker_entries = {a: [] for a in all_attackers}

  for _, row in log_df.iterrows():
    cyc = int(row["Cycle"])
    cyc_col = f"Cycle {cyc}"
    att = row["Attacker"]
    dfnd = row["Defender"]

    if dfnd in enemy_rows:
      if enemy_rows[dfnd][cyc_col]:
        enemy_rows[dfnd][cyc_col] = f"{enemy_rows[dfnd][cyc_col]}, {att}"
      else:
        enemy_rows[dfnd][cyc_col] = att

    if att in attacker_entries:
      attacker_entries[att].append(f"{dfnd} (Cycle {cyc})")

  enemy_cycles_df = pd.DataFrame(
      [{"Defender": d, **enemy_rows[d]} for d in all_defenders]
  )

  max_battles = max(
      attacks_per_player,
      max((len(v) for v in attacker_entries.values()), default=0),
  )
  battle_cols = [f"Battle {i}" for i in range(1, max_battles + 1)]

  attacker_records = []
  for a in all_attackers:
    battles = attacker_entries[a]
    battle_dict = {
        f"Battle {i + 1}": (battles[i] if i < len(battles) else "")
        for i in range(max_battles)
    }
    attacker_records.append({
        "Attacker": a,
        "Attacks Used": len(battles),
        **battle_dict,
    })

  attacker_targets_df = pd.DataFrame(attacker_records)
  return enemy_cycles_df, attacker_targets_df


def assign_rank_points(df, power_col="Power (b)"):
  """Assigns Points with Leader = 50 and up to 49 other players receiving 49..1."""
  if df is None or df.empty:
    out = df.copy() if df is not None else pd.DataFrame()
    out["Points"] = []
    return out

  out = df.copy()
  rank_clean = out.get("Rank", pd.Series(["r4"] * len(out), index=out.index))
  rank_clean = rank_clean.fillna("r4").astype(str).str.strip().str.lower()

  r_order = {"r1": 0, "r2": 1, "r3": 2, "r4": 3, "r5": 4}

  sort_power_col = power_col if power_col in out.columns else "Power (b)"
  out["_sort_power"] = pd.to_numeric(out[sort_power_col], errors="coerce").fillna(
      0.0
  )

  def _tier_tuple(row_idx):
    rk = rank_clean.loc[row_idx]
    pwr = out.loc[row_idx, "_sort_power"]
    if rk == "leader":
      return (0, 0, -pwr, row_idx)
    if rk == "commander":
      return (1, 0, -pwr, row_idx)
    if rk == "captain":
      return (2, 0, -pwr, row_idx)
    if rk in r_order:
      return (3, r_order[rk], -pwr, row_idx)
    return (4, 99, -pwr, row_idx)

  ordered_indices = sorted(out.index.tolist(), key=_tier_tuple)

  next_points = 49
  points_map = {}
  for idx in ordered_indices:
    if rank_clean.loc[idx] == "leader":
      points_map[idx] = 50
    else:
      points_map[idx] = max(1, next_points)
      next_points -= 1

  out["Points"] = out.index.map(points_map)
  return out.drop(columns=["_sort_power"])


def _get_github_config(roster_type="clan"):
  """Reads GitHub repo settings from `st.secrets` for 'clan' or 'enemy'."""
  try:
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    if roster_type == "enemy":
      path = st.secrets.get("GITHUB_ENEMY_PATH", "data/enemy_roster.json")
    else:
      path = st.secrets.get("GITHUB_CLAN_PATH", "data/clan_roster.json")
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    return token, repo, path, branch
  except (KeyError, FileNotFoundError):
    return None, None, None, None 


def load_rosters(clan):
  """Fetches `data/pvp_rosters.json` from GitHub API, falling back to local disk."""
  token, repo, path, branch = _get_github_config(clan)

  if token and repo:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
      resp = requests.get(
          url, headers=headers, params={"ref": branch}, timeout=10
      )
      resp.raise_for_status()
      payload = resp.json()
      raw_text = base64.b64decode(payload["content"]).decode("utf-8")
      return json.loads(raw_text)
    except Exception as exc:
      st.error(f"GitHub load error for {clan}")

  return {}


def _filter_active_entries(entries):
  """Excludes any player/enemy marked `"active": false`."""
  if not isinstance(entries, list):
    return []
  return [
      entry
      for entry in entries
      if isinstance(entry, dict) and entry.get("active", True) is not False
  ]


def sort_roster_for_save(df, power_col="Power (b)"):
  """Sorts a roster DataFrame by rank tier, then power descending, then name."""
  if df is None or df.empty:
    return pd.DataFrame() if df is None else df.copy()

  out = df.dropna(how="all").copy()
  if out.empty:
    return out

  rank_series = (
      out.get("Rank", pd.Series(["r4"] * len(out), index=out.index))
      .fillna("r4")
      .astype(str)
      .str.strip()
      .str.lower()
  )
  power_series = pd.to_numeric(
      out.get(power_col, pd.Series([0.0] * len(out), index=out.index)),
      errors="coerce",
  ).fillna(0.0)
  name_series = (
      out.get("Player Name", pd.Series([""] * len(out), index=out.index))
      .fillna("")
      .astype(str)
      .str.strip()
  )

  rank_priority = {
      "leader": 0,
      "commander": 1,
      "captain": 2,
      "r1": 3,
      "r2": 4,
      "r3": 5,
      "r4": 6,
      "r5": 7,
  }

  out["_rank_ord"] = rank_series.map(rank_priority).fillna(99)
  out["_power_neg"] = -power_series
  out["_name_key"] = name_series.str.lower()

  out = out.sort_values(
      by=["_rank_ord", "_power_neg", "_name_key"],
      ascending=[True, True, True],
      kind="mergesort",
  ).drop(columns=["_rank_ord", "_power_neg", "_name_key"])

  return out.reset_index(drop=True)


def save_roster_to_github(
    roster_type,
    roster_df,
    commit_message=None,
    power_col="Power (b)",
):
  """Sorts and pushes a single roster DataFrame ('clan' or 'enemy') to GitHub."""
  normalized_type = "enemy" if str(roster_type).strip().lower() == "enemy" else "clan"
  token, repo, path, branch = _get_github_config(normalized_type)
  if not token or not repo:
    return False, "Missing GITHUB_TOKEN or GITHUB_REPO in secrets."

  url = f"https://api.github.com/repos/{repo}/contents/{path}"
  headers = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
  }

  default_msg = (
      "Update enemy PvP roster"
      if normalized_type == "enemy"
      else "Update clan PvP roster"
  )
  final_msg = (
      commit_message.strip()
      if isinstance(commit_message, str) and commit_message.strip()
      else default_msg
  )

  try:
    get_resp = requests.get(
        url, headers=headers, params={"ref": branch}, timeout=10
    )
    get_resp.raise_for_status()
    current_sha = get_resp.json()["sha"]

    sorted_df = sort_roster_for_save(roster_df, power_col=power_col)
    records = sorted_df.to_dict(orient="records")

    # Match the top-level JSON structure each file uses
    if normalized_type == "enemy":
      roster_payload = {"enemies": records}
    else:
      # For clan_rosters.json, strip Power (b) if you only want name & rank stored there
      clan_records = [
          {k: v for k, v in rec.items() if k != "Power (b)"}
          for rec in records
      ]
      roster_payload = {"players": clan_records}

    encoded_content = base64.b64encode(
        json.dumps(roster_payload, indent=2).encode("utf-8")
    ).decode("utf-8")

    put_body = {
        "message": final_msg,
        "content": encoded_content,
        "sha": current_sha,
        "branch": branch,
    }
    put_resp = requests.put(url, headers=headers, json=put_body, timeout=10)
    put_resp.raise_for_status()

    return True, sorted_df, f"Pushed sorted `{normalized_type}` roster to `{path}` on `{branch}`."
  except Exception as exc:
    print(f"GitHub push error ({normalized_type}): {exc}", flush=True)
    return False, roster_df, f"GitHub push failed: {exc}"
  

def load_battles():
  """Fetches `data/pvp_battles.json` from GitHub API, falling back to local disk."""
  token, repo, _, branch = _get_github_config()
  battles_path = st.secrets.get("GITHUB_BATTLES_PATH", "data/pvp_battles.json")

  if token and repo:
    url = f"https://api.github.com/repos/{repo}/contents/{battles_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
      resp = requests.get(
          url, headers=headers, params={"ref": branch}, timeout=10
      )
      resp.raise_for_status()
      payload = resp.json()
      raw_text = base64.b64decode(payload["content"]).decode("utf-8")
      data = json.loads(raw_text)
      return data.get("battles", []) if isinstance(data, dict) else []
    except Exception as exc:
      print(
          f"GitHub battles load error, falling back to local file: {exc}",
          flush=True,
      )

  local_path = Path(battles_path)
  if local_path.exists():
    try:
      data = json.loads(local_path.read_text(encoding="utf-8"))
      return data.get("battles", []) if isinstance(data, dict) else []
    except Exception as exc:
      print(f"Local battles read error: {exc}", flush=True)

  return []


def save_battles_to_github(battles_df, commit_message="Update PvP battles"):
  """Pushes battle log records to `data/pvp_battles.json` on GitHub."""
  token, repo, _, branch = _get_github_config()
  battles_path = st.secrets.get("GITHUB_BATTLES_PATH", "data/pvp_battles.json")
  if not token or not repo:
    return False, "Missing GITHUB_TOKEN or GITHUB_REPO in secrets."

  url = f"https://api.github.com/repos/{repo}/contents/{battles_path}"
  headers = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
  }

  try:
    clean_df = (
        battles_df.dropna(how="all") if battles_df is not None else pd.DataFrame()
    )
    for col in BATTLE_COLS:
      if col not in clean_df.columns:
        clean_df[col] = ""
    clean_df = clean_df[BATTLE_COLS]

    payload_obj = {"battles": clean_df.to_dict(orient="records")}
    encoded = base64.b64encode(
        json.dumps(payload_obj, indent=2).encode("utf-8")
    ).decode("utf-8")

    sha = None
    get_resp = requests.get(
        url, headers=headers, params={"ref": branch}, timeout=10
    )
    if get_resp.status_code == 200:
      sha = get_resp.json().get("sha")

    put_body = {
        "message": commit_message,
        "content": encoded,
        "branch": branch,
    }
    if sha:
      put_body["sha"] = sha

    put_resp = requests.put(url, headers=headers, json=put_body, timeout=10)
    put_resp.raise_for_status()
    return True, f"Saved battle log to `{battles_path}` on `{branch}`."
  except Exception as exc:
    print(f"GitHub battles push error: {exc}", flush=True)
    return False, f"GitHub battles push failed: {exc}"


def build_battle_record(
    attacker_side, attacker, defender_side, defender, attacker_won
):
  """Builds a normalized battle record with explicit attacker, defender, winner, and loser."""
  if attacker_won:
    winner_side, winner = attacker_side, attacker
    loser_side, loser = defender_side, defender
  else:
    winner_side, winner = defender_side, defender
    loser_side, loser = attacker_side, attacker

  return {
      "attacker_side": attacker_side,
      "attacker": attacker,
      "defender_side": defender_side,
      "defender": defender,
      "winner_side": winner_side,
      "winner": winner,
      "loser_side": loser_side,
      "loser": loser,
  }


def get_remaining_attacks_by_side(
    battles_df, player_names, enemy_names, attacks_per_player=5
):
  """Returns `(edgr_remaining_map, ex_remaining_map)` using explicit `attacker`."""
  edgr_used = {str(n).strip(): 0 for n in player_names if str(n).strip()}
  ex_used = {str(n).strip(): 0 for n in enemy_names if str(n).strip()}

  if battles_df is not None and not battles_df.empty:
    for _, row in battles_df.iterrows():
      att = str(row.get("attacker", "")).strip()
      att_side = str(row.get("attacker_side", "")).strip().upper()
      if not att:
        continue
      if not att_side:
        if att in edgr_used:
          att_side = "EDGR"
        elif att in ex_used:
          att_side = "EX"

      if att_side == "EDGR" and att in edgr_used:
        edgr_used[att] += 1
      elif att_side == "EX" and att in ex_used:
        ex_used[att] += 1

  edgr_rem = {k: max(0, attacks_per_player - v) for k, v in edgr_used.items()}
  ex_rem = {k: max(0, attacks_per_player - v) for k, v in ex_used.items()}
  return edgr_rem, ex_rem


def get_live_war_progress(
    battles_df, total_players, total_enemies, attacks_per_player=5
):
  """Computes remaining EDGR battles, cycle defeats, and enemies defeated this cycle."""
  reset_threshold = get_reset_threshold(total_enemies)
  max_battles = int(total_players) * int(attacks_per_player)

  edgr_attacks_used = 0
  edgr_win_targets = []

  if battles_df is not None and not battles_df.empty:
    for _, row in battles_df.iterrows():
      att_side = str(row.get("attacker_side", "")).strip().upper()
      win_side = str(row.get("winner_side", "")).strip().upper()
      loser_name = str(row.get("loser", "")).strip()

      if att_side == "EDGR":
        edgr_attacks_used += 1
      if win_side == "EDGR":
        edgr_win_targets.append(loser_name)

  edgr_wins = len(edgr_win_targets)
  remaining_battles = max(0, max_battles - edgr_attacks_used)
  wins_in_current_cycle = edgr_wins % reset_threshold
  defeats_left_to_reset = reset_threshold - wins_in_current_cycle

  defeated_this_cycle = (
      edgr_win_targets[-wins_in_current_cycle:]
      if wins_in_current_cycle > 0
      else []
  )

  return {
      "reset_threshold": reset_threshold,
      "max_battles": max_battles,
      "edgr_attacks_used": edgr_attacks_used,
      "remaining_battles": remaining_battles,
      "edgr_wins": edgr_wins,
      "wins_in_current_cycle": wins_in_current_cycle,
      "defeats_left_to_reset": defeats_left_to_reset,
      "defeated_this_cycle": defeated_this_cycle,
  }


def compute_iterative_multipliers(
    battles_df, players_eff, enemies_eff, n_iters=8
):
  """Computes dynamic combat multipliers from a flat battle log using iterative passes."""
  roster_info = {}
  for side, df in (("EDGR", players_eff), ("EX", enemies_eff)):
    if df is None or df.empty:
      continue
    for _, row in df.iterrows():
      name = str(row.get("Player Name", "")).strip()
      if name:
        eff = float(
            pd.to_numeric(row.get("Effective Power"), errors="coerce") or 0.0
        )
        roster_info[name] = (side, eff)

  if battles_df is None or battles_df.empty or not roster_info:
    return {}, {}, pd.DataFrame()

  valid_battles = []
  for _, row in battles_df.iterrows():
    w = str(row.get("winner", "")).strip()
    l = str(row.get("loser", "")).strip()
    if w in roster_info and l in roster_info:
      w_pwr = roster_info[w][1]
      l_pwr = roster_info[l][1]
      if w_pwr > 0 and l_pwr > 0:
        valid_battles.append((w, l))

  if not valid_battles:
    return {}, {}, pd.DataFrame()

  mult = {name: 1.0 for name in roster_info}

  for _ in range(n_iters):
    win_ratios = {name: [] for name in roster_info}
    loss_ratios = {name: [] for name in roster_info}

    for w, l in valid_battles:
      p_w = roster_info[w][1]
      p_l = roster_info[l][1]

      adj_w = p_w * mult[w]
      adj_l = p_l * mult[l]

      win_ratios[w].append(adj_l / p_w)
      loss_ratios[l].append(adj_w / p_l)

    next_mult = {}
    for name, (_, _) in roster_info.items():
      wins = win_ratios[name]
      losses = loss_ratios[name]
      n_games = len(wins) + len(losses)

      if n_games == 0:
        next_mult[name] = 1.0
        continue

      if wins:
        win_score = 0.65 * (sum(wins) / len(wins)) + 0.35 * max(wins)
      else:
        win_score = 1.0

      raw_score = win_score
      if losses:
        min_loss = min(losses)
        if min_loss < 1.05:
          raw_score = min(raw_score, min_loss)

      confidence = n_games / (n_games + 2.0)
      shrunk = 1.0 + confidence * (raw_score - 1.0)
      next_mult[name] = max(0.4, min(2.5, shrunk))

    mult = next_mult

  player_mult = {}
  enemy_mult = {}
  summary_rows = []

  win_counts = {name: 0 for name in roster_info}
  loss_counts = {name: 0 for name in roster_info}
  for w, l in valid_battles:
    win_counts[w] += 1
    loss_counts[l] += 1

  for name, (side, eff_pwr) in roster_info.items():
    m_val = round(mult[name], 3)
    if side == "EDGR":
      player_mult[name] = m_val
    else:
      enemy_mult[name] = m_val

    if win_counts[name] > 0 or loss_counts[name] > 0:
      summary_rows.append({
          "Side": side,
          "Player": name,
          "Wins": win_counts[name],
          "Losses": loss_counts[name],
          "Multiplier": m_val,
          "Adjusted Eff Power": format_si_3sf(eff_pwr * m_val),
      })

  summary_df = (
      pd.DataFrame(summary_rows).sort_values(
          by=["Side", "Multiplier"], ascending=[True, False]
      )
      if summary_rows
      else pd.DataFrame()
  )
  return player_mult, enemy_mult, summary_df


def recommend_next_reset_assignments(
    players_eff,
    enemies_eff,
    player_mult_map,
    enemy_mult_map,
    remaining_map,
    safety_margin=0.9,
    reset_remaining=43,
    points_multiplier=1.4,
    already_defeated=None,
):
  """Suggests weakest-eligible clan attackers for undefeated targets before reset."""
  defeated_set = {
      str(x).strip() for x in (already_defeated or []) if str(x).strip()
  }

  atk = players_eff.copy()
  atk["adj_power"] = atk.apply(
      lambda r: float(r["Effective Power"])
      * float(player_mult_map.get(r["Player Name"], 1.0)),
      axis=1,
  )
  atk["rem_attacks"] = atk["Player Name"].map(
      lambda n: int(remaining_map.get(n, 0))
  )
  atk = atk[atk["rem_attacks"] > 0].copy()

  dfn = enemies_eff.copy()
  if defeated_set:
    dfn = dfn[~dfn["Player Name"].isin(defeated_set)].copy()

  dfn["adj_power"] = dfn.apply(
      lambda r: float(r["Effective Power"])
      * float(enemy_mult_map.get(r["Player Name"], 1.0)),
      axis=1,
  )
  dfn["est_points"] = (
      pd.to_numeric(dfn.get("Points", 0), errors="coerce").fillna(0)
      * points_multiplier
  ).apply(round)
  dfn = dfn.sort_values(
      by=["est_points", "adj_power"], ascending=[False, False]
  ).reset_index(drop=True)

  suggestions = []
  for _, t_row in dfn.iterrows():
    if len(suggestions) >= max(1, int(reset_remaining)):
      break

    t_pow = float(t_row["adj_power"])
    eligible = atk[(atk["adj_power"] * safety_margin) >= t_pow]
    if eligible.empty:
      continue

    best_idx = eligible["adj_power"].idxmin()
    a_row = atk.loc[best_idx]
    atk.at[best_idx, "rem_attacks"] -= 1

    suggestions.append({
        "Target Enemy": t_row["Player Name"],
        "Est. Points": int(t_row["est_points"]),
        "Enemy Adj. Power": format_si_3sf(t_pow),
        "Recommended Attacker": a_row["Player Name"],
        "Attacker Adj. Power": format_si_3sf(float(a_row["adj_power"])),
        "Attacks Left After": int(atk.at[best_idx, "rem_attacks"]),
    })

  return pd.DataFrame(suggestions)

