from datetime import datetime, timezone
import libsql
import pandas as pd
import streamlit as st

DB_URL = st.secrets["TURSO_DATABASE_URL"]
AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]


@st.cache_resource
def get_conn():
  conn = libsql.connect(database=DB_URL, auth_token=AUTH_TOKEN)
  conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_by TEXT NOT NULL,
            player_name TEXT NOT NULL,
            power_b REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
  conn.commit()
  return conn


def append_submission(submitted_by: str, player_name: str, power_b: float):
  conn = get_conn()
  timestamp = datetime.now(timezone.utc).isoformat()
  conn.execute(
      """
        INSERT INTO submissions (submitted_by, player_name, power_b, created_at)
        VALUES (?, ?, ?, ?)
        """,
      (submitted_by.strip(), player_name.strip(), float(power_b), timestamp),
  )
  conn.commit()
  st.cache_data.clear()


@st.cache_data(ttl=15)
def load_submissions() -> pd.DataFrame:
  conn = get_conn()
  cur = conn.execute(
      "SELECT id, submitted_by, player_name, power_b, created_at FROM submissions ORDER BY id DESC"
  )
  rows = cur.fetchall()
  cols = ["id", "submitted_by", "player_name", "power_b", "created_at"]
  return pd.DataFrame(rows, columns=cols)


st.title("Live Roster & Power Submissions")

with st.form("append_form", clear_on_submit=True):
  submitted_by = st.text_input("Your Name / Group")
  player_name = st.text_input("Player Name")
  power_b = st.number_input("Power (b)", min_value=0.0, step=0.1, format="%.3f")
  submitted = st.form_submit_button("Append Row")

  if submitted:
    if not player_name.strip():
      st.warning("Please enter a player name.")
    else:
      append_submission(submitted_by or "Anonymous", player_name, power_b)
      st.success("Row appended to Turso!")

st.subheader("Current Data")
st.dataframe(load_submissions(), use_container_width=True)
