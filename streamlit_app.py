import pandas as pd
from pvp_utils import (
    _filter_active_entries,
    get_visit_count,
    load_battles,
    load_rosters,
    set_visit_count,
)
import streamlit as st

st.set_page_config(page_title="Day 6 PvP & Clan Hub", layout="wide")

# ==========================================
# 1. VISIT COUNTER & CREATOR MODE
# ==========================================
ignore_key = st.secrets.get("IGNORE_VISIT_KEY", "")
is_ignored_visitor = (
    bool(ignore_key) and st.query_params.get("key") == ignore_key
)

if "active" not in st.session_state:
  st.session_state.active = True
  current_visits = get_visit_count()
  if is_ignored_visitor:
    st.session_state.visit_count = current_visits
  elif current_visits is not None:
    st.session_state.visit_count = set_visit_count(current_visits + 1)
  else:
    st.session_state.visit_count = None

if is_ignored_visitor:
  count_display = (
      st.session_state.visit_count
      if st.session_state.visit_count is not None
      else "Unavailable"
  )
  st.caption(f"🔧 Creator mode active\n\nUsers so far: {count_display}")

# ==========================================
# 2. SHARED SESSION STATE (ROSTERS & BATTLES)
# ==========================================
if "players_df" not in st.session_state or "enemies_df" not in st.session_state:
  rosters = load_rosters()
  st.session_state.players_df = pd.DataFrame(
      _filter_active_entries(rosters.get("players", []))
  )
  st.session_state.enemies_df = pd.DataFrame(
      _filter_active_entries(rosters.get("enemies", []))
  )

if "battles_df" not in st.session_state:
  battle_cols = [
      "attacker_side",
      "attacker",
      "defender_side",
      "defender",
      "winner_side",
      "winner",
      "loser_side",
      "loser",
  ]
  loaded_battles = load_battles()
  st.session_state.battles_df = (
      pd.DataFrame(loaded_battles, columns=battle_cols)
      if loaded_battles
      else pd.DataFrame(columns=battle_cols)
  )

# ==========================================
# 3. NAVIGATION (DEFAULT: CLAN RESOURCES)
# ==========================================
pages = [
    st.Page(
        "pages/resources.py",
        title="Clan Resources",
        icon="🎒",
        default=True,
    ),
    st.Page(
        "pages/theoretical.py",
        title="Theoretical Planner",
        icon="📊",
    ),
    st.Page(
        "pages/running_mode.py",
        title="Running Mode",
        icon="📡",
    ),
    st.Page(
        "pages/roster_editor.py",
        title="Roster Editor",
        icon="✏️",
    ),
]

pg = st.navigation(pages)
pg.run()
