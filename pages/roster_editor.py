import pandas as pd
import streamlit as st
from pvp_utils import format_si_3sf, save_roster_to_github, sum_roster_power

st.title("Roster Editor")
st.write(
    "Update player powers or ranks here. Changes stay in your session until you"
    " push them to GitHub."
)

DISPLAY_COLS = ["Rank", "Player Name", "Power (b)"]

left_col, right_col = st.columns(2, wrap=False)

with left_col:
  our_total_power = format_si_3sf(sum_roster_power(st.session_state.players_df))
  st.subheader(f"EDGR: {our_total_power}")
  edited_players = st.data_editor(
      st.session_state.players_df,
      column_order=DISPLAY_COLS,
      hide_index=True,
      num_rows="dynamic",
      key="players_editor",
  )
  st.session_state.players_df = edited_players

with right_col:
  enemy_total_power = format_si_3sf(sum_roster_power(st.session_state.enemies_df))
  st.subheader(f"Enemies: {enemy_total_power}")
  edited_enemies = st.data_editor(
      st.session_state.enemies_df,
      column_order=DISPLAY_COLS,
      hide_index=True,
      num_rows="dynamic",
      key="enemies_editor",
  )
  st.session_state.enemies_df = edited_enemies

if "push_unlocked" not in st.session_state:
  st.session_state.push_unlocked = False

with st.expander("Save / Push Rosters to GitHub", expanded=True):
  expected_push_pwd = st.secrets.get("password_user", "")

  if not st.session_state.push_unlocked:
    with st.form("push_auth_form", clear_on_submit=True):
      entered_pwd = st.text_input("Push Password", type="password")
      unlock_clicked = st.form_submit_button("Unlock Push")
      if unlock_clicked:
        if expected_push_pwd and entered_pwd == expected_push_pwd:
          st.session_state.push_unlocked = True
          st.rerun()
        else:
          st.error("Incorrect push password.")
  else:
    st.caption(
        "If updating player power, please leave a message for what and why you"
        " edited."
    )
    commit_msg_input = st.text_input(
        "Commit Message",
        placeholder="e.g. Updated [my name]'s power",
        key="roster_commit_msg_input",
    )
    final_commit_msg = (
        commit_msg_input.strip()
        if commit_msg_input and commit_msg_input.strip()
        else "Update PvP rosters from planner"
    )

    col_push, col_lock = st.columns([3, 1], vertical_alignment="bottom")
    with col_push:
      if st.button(
          "Push Rosters to GitHub", key="push_rosters_btn", width="stretch"
      ):
        ok, msg = save_roster_to_github( 
            "clan", 
            st.session_state.players_df,
            st.session_state.enemies_df,
            commit_message=final_commit_msg,
        )
        if ok:
          st.session_state.players_df = updated_df
          st.success(msg) 
        else:
          st.error(msg)
    with col_lock:
      if st.button("Lock", key="lock_push_btn", width="stretch"):
        st.session_state.push_unlocked = False
        st.rerun()
