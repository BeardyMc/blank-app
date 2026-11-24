import pandas as pd
from pvp_utils import (
    _filter_active_entries,
    get_visit_count,
    load_battles,
    load_rosters,
    set_visit_count,
)
import streamlit as st

st.set_page_config(page_title="Day 6 PvP & Clan Hub", layout="wide")[span_1](start_span)[span_1](end_span)

# Visit counter & creator controls
ignore_key = st.secrets.get("IGNORE_VISIT_KEY", "")[span_2](start_span)[span_2](end_span)
is_ignored_visitor = bool(ignore_key) and st.query_params.get("key") == ignore_key[span_3](start_span)[span_3](end_span)

if "active" not in st.session_state:[span_4](start_span)[span_4](end_span)
  st.session_state.active = True[span_5](start_span)[span_5](end_span)
  current_visits = get_visit_count()[span_6](start_span)[span_6](end_span)
  if is_ignored_visitor:[span_7](start_span)[span_7](end_span)
    st.session_state.visit_count = current_visits[span_8](start_span)[span_8](end_span)
  elif current_visits is not None:[span_9](start_span)[span_9](end_span)
    st.session_state.visit_count = set_visit_count(current_visits + 1)[span_10](start_span)[span_10](end_span)
  else:[span_11](start_span)[span_11](end_span)
    st.session_state.visit_count = None[span_12](start_span)[span_12](end_span)

if is_ignored_visitor:[span_13](start_span)[span_13](end_span)
  count_display = (
      st.session_state.visit_count
      if st.session_state.visit_count is not None
      else "Unavailable"
  )[span_14](start_span)[span_14](end_span)
  st.caption(f"🔧 Creator mode active\n\nUsers so far: {count_display}")[span_15](start_span)[span_15](end_span)

# Initialize shared rosters & battle log once per session
if "players_df" not in st.session_state or "enemies_df" not in st.session_state:[span_16](start_span)[span_16](end_span)
  rosters = load_rosters()[span_17](start_span)[span_17](end_span)
  st.session_state.players_df = pd.DataFrame(
      _filter_active_entries(rosters.get("players", []))
  )[span_18](start_span)[span_18](end_span)
  st.session_state.enemies_df = pd.DataFrame(
      _filter_active_entries(rosters.get("enemies", []))
  )[span_19](start_span)[span_19](end_span)

if "battles_df" not in st.session_state:[span_20](start_span)[span_20](end_span)
  battle_cols = [
      "attacker_side",
      "attacker",
      "defender_side",
      "defender",
      "winner_side",
      "winner",
      "loser_side",
      "loser",
  ][span_21](start_span)[span_21](end_span)
  loaded_battles = load_battles()[span_22](start_span)[span_22](end_span)
  st.session_state.battles_df = (
      pd.DataFrame(loaded_battles, columns=battle_cols)
      if loaded_battles
      else pd.DataFrame(columns=battle_cols)
  )[span_23](start_span)[span_23](end_span)

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
    ),[span_24](start_span)[span_24](end_span)
    st.Page("pages/running_mode.py", title="Running Mode", icon="📡"),[span_25](start_span)[span_25](end_span)
    st.Page("pages/roster_editor.py", title="Roster Editor", icon="✏️"),[span_26](start_span)[span_26](end_span)
]

pg = st.navigation(pages)[span_27](start_span)[span_27](end_span)
pg.run()[span_28](start_span)[span_28](end_span)
