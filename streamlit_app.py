import base64
from pathlib import Path
import pandas as pd
from pvp_utils import (
    _filter_active_entries,
    get_visit_count,
    load_battles,
    load_rosters,
    set_visit_count,
    get_latest_turso_power_map
)
import streamlit as st

st.set_page_config(page_title="Compass Hub", layout="wide")

# ==========================================
# 2. SHARED SESSION STATE (ROSTERS & BATTLES)
# ==========================================

if "players_df" not in st.session_state or "enemies_df" not in st.session_state:
  clan_rosters = load_rosters("clan")
  enemy_rosters = load_rosters("enemy")
  st.session_state.players_df = pd.DataFrame(
      _filter_active_entries(clan_rosters.get("players", []))
  )
  
  players_df = st.session_state.players_df
  latest_power_map = get_latest_turso_power_map()
  if not players_df.empty and "Player Name" in players_df.columns:
    players_df["power"] = (
        players_df["Player Name"]
        .astype(str)
        .str.strip()
        .map(latest_power_map)
        .fillna(0.0)
    )
  else:
    players_df["power"] = 0.0 

  st.session_state.players_df = players_df
  st.session_state.enemies_df = pd.DataFrame(
      _filter_active_entries(enemy_rosters.get("enemies", []))
  )


def apply_compass_background(
    image_path: str = "assets/compass_bg.jpg", dim_overlay: float = 0.45
):
    img_bytes = Path(image_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(
                rgba(12, 15, 20, {dim_overlay}),
                rgba(12, 15, 20, {dim_overlay})
            ), url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(0, 0, 0, 0);
        }}
        [data-testid="stTextInput"] > div > div,
        [data-testid="stNumberInput"] > div > div,
        [data-testid="stSelectbox"] > div > div,
        [data-testid="stForm"] {{
            background-color: rgba(20, 24, 32, 0.82) !important;
            border-radius: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_compass_background("assets/compass_bg.jpg", dim_overlay=0.45) 


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
        "pages/war_points.py",
        title="War Points",
        icon="🪙",
    ),
    st.Page(
        "pages/roster_editor.py",
        title="Roster Editor",
        icon="✏️",
    ),
]

pg = st.navigation(pages)
pg.run()
