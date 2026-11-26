import math
import re
from typing import Optional
import time 
import pandas as pd
from pydantic import BaseModel
import streamlit as st
from pvp_utils import format_si_3sf, save_rosters_to_github, sum_roster_power
from ocr_util import extract_enemies_batch 


st.title("Roster Editor")
st.write(
    "Update rosters or ranks here. Changes stay in your session until you"
    " push them to GitHub. \n\nOur power vals come from database, enemy powers and ranks should be edited here"
)

DISPLAY_COLS = ["Rank", "Player Name", "power"]

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
        "If updating, please leave a message for what and why you edited."
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
        ok, updated_players, updated_enemies, msg = save_rosters_to_github(
            st.session_state.players_df,
            st.session_state.enemies_df,
            commit_message=final_commit_msg,
            power_col="power",
        )
        if ok:
          st.session_state.players_df = updated_players
          st.session_state.enemies_df = updated_enemies
          st.success(msg)
        else:
          st.error(msg)
    with col_lock:
      if st.button("Lock", key="lock_push_btn", width="stretch"):
        st.session_state.push_unlocked = False
        st.rerun()




if st.session_state.push_unlocked:
  st.subheader("Import Enemy Roster From Screenshots")

  uploaded_files = st.file_uploader(
      "Upload enemy roster screenshots",
      type=["png", "jpg", "jpeg", "webp"],
      accept_multiple_files=True,
      key="enemy_roster_uploads_v2",
  )

  if uploaded_files:
    st.caption(
        "Attached: "
        + ", ".join(f"{f.name} ({f.type}, {f.size} B)" for f in uploaded_files)
    )
  else:
    st.caption("No files attached yet.")

  show_ocr_debug = st.checkbox("Show raw OCR row grouping (debug)", value=False)

  if st.button(
      "Extract Enemy Roster",
      disabled=not uploaded_files,
      key="btn_extract_enemies",
  ):
    with st.spinner("Reading screenshots with RapidOCR..."):
      ocr_df, debug_lines = extract_enemies_batch(
          uploaded_files, return_debug=show_ocr_debug
      )
    st.session_state["pending_enemy_ocr_df"] = ocr_df
    st.session_state["pending_enemy_ocr_debug"] = (
        debug_lines if show_ocr_debug else []
    )

  if show_ocr_debug and st.session_state.get("pending_enemy_ocr_debug"):
    with st.expander("Raw OCR Row Grouping", expanded=True):
      for line in st.session_state["pending_enemy_ocr_debug"]:
        st.text(line)

  if "pending_enemy_ocr_df" in st.session_state and not st.session_state[
      "pending_enemy_ocr_df"
  ].empty:
    st.caption(
        "Review extracted raw power values before merging into `enemies_df`:"
    )
    reviewed_df = st.data_editor(
        st.session_state["pending_enemy_ocr_df"],
        num_rows="dynamic",
        use_container_width=True,
        key="enemy_ocr_review_editor",
    )

    if st.button("Merge Into Enemy Roster", key="btn_merge_enemies"):
      selected = reviewed_df[reviewed_df["Include"] == True].copy()
      enemies_df = st.session_state.get("enemies_df", pd.DataFrame()).copy()

      if enemies_df.empty:
        enemies_df = pd.DataFrame(columns=["Player Name", "Rank", "power"])

      for _, row in selected.iterrows():
        name = str(row.get("Player Name", "")).strip()
        if not name:
          continue
        new_power = row.get("power")
        new_rank = str(row.get("Rank") or "").strip()

        mask = (
            enemies_df["Player Name"].astype(str).str.lower() == name.lower()
        )
        if mask.any():
          if pd.notna(new_power):
            enemies_df.loc[mask, "power"] = float(new_power)
          if new_rank:
            enemies_df.loc[mask, "Rank"] = new_rank
        else:
          enemies_df = pd.concat(
              [
                  enemies_df,
                  pd.DataFrame([{
                      "Player Name": name,
                      "Rank": new_rank or "r4",
                      "power": (
                          float(new_power) if pd.notna(new_power) else 0.0
                      ),
                  }]),
              ],
              ignore_index=True,
          )

      st.session_state["enemies_df"] = enemies_df
      del st.session_state["pending_enemy_ocr_df"]
      st.session_state.pop("pending_enemy_ocr_debug", None)
      st.success("Enemy roster updated with raw power values.")
      st.rerun()


