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
# 2. SHARED SESSION STATE (ROSTERS & BATTLES)
# ==========================================
if "players_df" not in st.session_state or "enemies_df" not in st.session_state:
  clan_rosters = load_rosters("clan")
  enemy_rosters = load_rosters("enemy")
  st.session_state.players_df = pd.DataFrame(
      _filter_active_entries(clan_rosters.get("players", []))
  )
  st.session_state.enemies_df = pd.DataFrame(
      _filter_active_entries(enemy_rosters.get("enemies", []))
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
#    st.Page(
#        "pages/theoretical.py",
#        title="Theoretical Planner",
#        icon="📊",
#    ),
#    st.Page(
#        "pages/running_mode.py",
#        title="Running Mode",
#        icon="📡",
#    ),
    st.Page(
        "pages/roster_editor.py",
        title="Roster Editor",
        icon="✏️",
    ),
]

pg = st.navigation(pages)
pg.run()
