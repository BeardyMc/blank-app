import streamlit as st
from summon_maths import compute_player_summary, load_summon_tables

st.title("War Points Summary")

summon_tables = load_summon_tables()

# Pass your loaded player resources DataFrame in here
players_df = st.session_state.get("player_resources_df")

if players_df is None or players_df.empty:
  st.info("No player resource data available yet.")
else:
  summary_df = compute_player_summary(players_df, summon_tables)
  st.dataframe(summary_df, use_container_width=True)
