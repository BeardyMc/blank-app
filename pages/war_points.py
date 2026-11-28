import streamlit as st
from summon_maths import compute_player_summary, load_summon_tables

st.title("War Points Summary")

# csv file hosted in github, so easily edited for game expansions
summon_tables = load_summon_tables()

if "players_resources_df" not in st.session_state: 
  st.info("No player resource data available yet.")
else:
  summary_df = compute_player_summary(st.session_state.players_resources_df, summon_tables)
  st.dataframe(summary_df, use_container_width=True)
