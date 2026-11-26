import math
import re
from typing import Optional
from google import genai
from google.genai import types
import pandas as pd
from pydantic import BaseModel
import streamlit as st
from pvp_utils import format_si_3sf, save_roster_to_github, sum_roster_power


### GEMINI SCREENSHOT READER ###
import math
import re
from typing import Optional
from google import genai
from google.genai import types
import pandas as pd
from pydantic import BaseModel
import streamlit as st


class EnemyRow(BaseModel):
  player_name: str
  rank: Optional[str] = None
  power_raw: str


class EnemyRosterExtraction(BaseModel):
  entries: list[EnemyRow]


def parse_power_to_billions(raw_val) -> Optional[float]:
  """Converts strings like '850m', '436b', '3.82t', or '1.88q' into numeric Power (b)."""
  if raw_val is None:
    return None
  if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
    return None if math.isnan(float(raw_val)) else float(raw_val)

  text = str(raw_val).strip().replace(",", "")
  match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]*)$", text)
  if not match:
    return None

  num = float(match.group(1))
  suffix = match.group(2)

  suffix_to_b = {
      "": 1.0,
      "b": 1.0,
      "B": 1.0,
      "m": 1e-3,
      "M": 1e-3,
      "t": 1e3,
      "T": 1e3,
      "q": 1e6,
      "Q": 1e6,
  }
  factor = suffix_to_b.get(suffix, suffix_to_b.get(suffix.lower(), 1.0))
  return round(num * factor, 6)


def extract_enemies_from_image(image_bytes: bytes, mime_type: str) -> list[dict]:
  """Calls Gemini to extract enemy roster rows from a single screenshot."""
  api_key = st.secrets.get("GEMINI_API_KEY")
  if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in st.secrets.")

  client = genai.Client(api_key=api_key)
  prompt = (
      "Extract all visible enemy players from this roster screenshot. "
      "For each row, return player_name, rank (if visible), and power_raw "
      "exactly as shown with its unit suffix (for example: 516t, 3.82t, 14b, 850m). "
      "Ignore UI status labels like online/offline timestamps or icons."
  )

  response = client.models.generate_content(
      model="gemini-3.8-flash",
      contents=[
          prompt,
          types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
      ],
      config=types.GenerateContentConfig(
          response_mime_type="application/json",
          response_schema=EnemyRosterExtraction,
          temperature=0,
      ),
  )

  parsed = response.parsed
  if not parsed or not parsed.entries:
    return []

  rows = []
  for item in parsed.entries:
    name = (item.player_name or "").strip()
    if not name:
      continue
    rows.append({
        "Include": True,
        "Player Name": name,
        "Rank": (item.rank or "").strip(),
        "Power (b)": parse_power_to_billions(item.power_raw),
        "Raw Extracted": item.power_raw,
    })
  return rows

####

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

if st.session_state.push_unlocked:
  st.subheader("Import Enemy Roster From Screenshots")

  uploaded_files = st.file_uploader(
      "Upload enemy roster screenshots",
      type=["png", "jpg", "jpeg", "webp"],
      accept_multiple_files=True,
      key="enemy_roster_uploads",
  )
  st.write("push_unlocked:",st.session_state.get("push_unlocked"))
  st.write("uploaded_files count:", len(uploaded_files) if uploaded_files else 0)


  if st.button(
      "Extract Enemy Roster",
      disabled=not uploaded_files,
      key="btn_extract_enemies",
  ):
    all_rows = []
    with st.spinner("Reading screenshots with Gemini..."):
      for f in uploaded_files:
        mime = f.type or "image/png"
        all_rows.extend(extract_enemies_from_image(f.getvalue(), mime))

    # Deduplicate by Player Name (case-insensitive), keeping first non-null raw power
    deduped = {}
    for r in all_rows:
      key = r["Player Name"].lower()
      if key not in deduped:
        deduped[key] = r
      elif deduped[key]["power"] is None and r["power"] is not None:
        deduped[key] = r

    st.session_state["pending_enemy_ocr_df"] = pd.DataFrame(
        list(deduped.values())
    )

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
      st.success("Enemy roster updated with raw power values.")
      st.rerun()


