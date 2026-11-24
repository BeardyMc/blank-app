from datetime import datetime, timezone
import libsql
import pandas as pd
import streamlit as st
import re

DB_URL = st.secrets["TURSO_DATABASE_URL"]
AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]

RESOURCE_COLUMNS = [
    "player_name",
    "damage_lvl",
    "health_lvl",
    "hammers",
    "skill_tickets",
    "skill_summon_cost",
    "skill_level",
    "egg_summon_lvl",
    "egg_summon_chance",
    "pets_to_merge",
    "mount_summon_lvl",
    "mount_clockwinders",
    "mount_summon_cost",
    "mount_extra_chance",
    "clan_tech_vials",
    "updated_at",
]


@st.cache_resource
def get_conn():
  conn = libsql.connect(database=DB_URL, auth_token=AUTH_TOKEN)
  conn.execute("""
        CREATE TABLE IF NOT EXISTS player_resources (
            player_name TEXT PRIMARY KEY,
            damage_lvl INTEGER NOT NULL DEFAULT 0,
            health_lvl INTEGER NOT NULL DEFAULT 0,
            hammers INTEGER NOT NULL DEFAULT 0,
            skill_tickets INTEGER NOT NULL DEFAULT 0,
            skill_summon_cost INTEGER NOT NULL DEFAULT 0,
            skill_level INTEGER NOT NULL DEFAULT 0,
            egg_summon_lvl INTEGER NOT NULL DEFAULT 0,
            egg_summon_chance REAL NOT NULL DEFAULT 0.0,
            pets_to_merge INTEGER NOT NULL DEFAULT 0,
            mount_summon_lvl INTEGER NOT NULL DEFAULT 0,
            mount_clockwinders INTEGER NOT NULL DEFAULT 0,
            mount_summon_cost INTEGER NOT NULL DEFAULT 0,
            mount_extra_chance REAL NOT NULL DEFAULT 0.0,
            clan_tech_vials INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
  conn.commit()
  return conn


@st.cache_data(ttl=15)
def load_all_player_resources() -> pd.DataFrame:
  conn = get_conn()
  cols_sql = ", ".join(RESOURCE_COLUMNS)
  rows = conn.execute(
      f"SELECT {cols_sql} FROM player_resources ORDER BY player_name ASC"
  ).fetchall()
  if not rows:
    return pd.DataFrame(columns=RESOURCE_COLUMNS)
  return pd.DataFrame(rows, columns=RESOURCE_COLUMNS)


def upsert_player_resources(data: dict):
  conn = get_conn()
  now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  conn.execute(
      """
        INSERT INTO player_resources (
            player_name, damage_lvl, health_lvl,
            hammers, skill_tickets, skill_summon_cost, skill_level,
            egg_summon_lvl, egg_summon_chance, pets_to_merge,
            mount_summon_lvl, mount_clockwinders, mount_summon_cost,
            mount_extra_chance, clan_tech_vials, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET
            damage_lvl = excluded.damage_lvl,
            health_lvl = excluded.health_lvl,
            hammers = excluded.hammers,
            skill_tickets = excluded.skill_tickets,
            skill_summon_cost = excluded.skill_summon_cost,
            skill_level = excluded.skill_level,
            egg_summon_lvl = excluded.egg_summon_lvl,
            egg_summon_chance = excluded.egg_summon_chance,
            pets_to_merge = excluded.pets_to_merge,
            mount_summon_lvl = excluded.mount_summon_lvl,
            mount_clockwinders = excluded.mount_clockwinders,
            mount_summon_cost = excluded.mount_summon_cost,
            mount_extra_chance = excluded.mount_extra_chance,
            clan_tech_vials = excluded.clan_tech_vials,
            updated_at = excluded.updated_at
        """,
      (
          data["player_name"],
          int(data["damage_lvl"]),
          int(data["health_lvl"]),
          int(data["hammers"]),
          int(data["skill_tickets"]),
          int(data["skill_summon_cost"]),
          int(data["skill_level"]),
          int(data["egg_summon_lvl"]),
          float(data["egg_summon_chance"]),
          int(data["pets_to_merge"]),
          int(data["mount_summon_lvl"]),
          int(data["mount_clockwinders"]),
          int(data["mount_summon_cost"]),
          float(data["mount_extra_chance"]),
          int(data["clan_tech_vials"]),
          now_utc,
      ),
  )
  conn.commit()
  st.cache_data.clear()


# --- UI SECTION ---
st.header("Clan Member Resource & Stat Tracker")

# Pull player names from your existing clan roster DataFrame if loaded, else fallback
if "players_df" in st.session_state and not st.session_state.players_df.empty:
  roster_names = sorted(
      st.session_state.players_df["Player Name"].dropna().unique().tolist()
  )
else:
  roster_names = ["BeardyMcBeard", "Mypleasure", "Kitty87"]

saved_df = load_all_player_resources()

# Select player outside the form so existing saved numbers pre-fill automatically
selected_player = st.selectbox("Select Your Name (Clan Roster)", roster_names)

existing = {}
if not saved_df.empty and selected_player in saved_df["player_name"].values:
  existing = (
      saved_df[saved_df["player_name"] == selected_player].iloc[0].to_dict()
  )

with st.form("player_resource_form"):
  st.subheader(f"Updating: {selected_player}")

  # Combat Stats & General Resources
  c1, c2, c3, c4 = st.columns(4)
  with c1:
    damage_lvl = st.number_input(
        "Damage", min_value=0, step=1, value=int(existing.get("damage_lvl", 0))
    )
  with c2:
    health_lvl = st.number_input(
        "Health", min_value=0, step=1, value=int(existing.get("health_lvl", 0))
    )
  with c3:
    hammers = st.number_input(
        "Hammers", min_value=0, step=1, value=int(existing.get("hammers", 0))
    )
  with c4:
    clan_tech_vials = st.number_input(
        "Clan Tech Vials",
        min_value=0,
        step=1,
        value=int(existing.get("clan_tech_vials", 0)),
    )

  # Skills
  s1, s2, s3 = st.columns(3)
  with s1:
    skill_tickets = st.number_input(
        "Skill Tickets",
        min_value=0,
        step=1,
        value=int(existing.get("skill_tickets", 0)),
    )
  with s2:
    skill_summon_cost = st.number_input(
        "Skill Summon Cost",
        min_value=0,
        step=1,
        value=int(existing.get("skill_summon_cost", 0)),
    )
  with s3:
    skill_level = st.number_input(
        "Skill Level",
        min_value=0,
        step=1,
        value=int(existing.get("skill_level", 0)),
    )

  # Eggs & Pets
  e1, e2, e3 = st.columns(3)
  with e1:
    egg_summon_lvl = st.number_input(
        "Egg Summon Lvl",
        min_value=0,
        step=1,
        value=int(existing.get("egg_summon_lvl", 0)),
    )
  with e2:
    egg_summon_chance = st.number_input(
        "Egg Summon Chance (%)",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        value=float(existing.get("egg_summon_chance", 0.0)),
    )
  with e3:
    pets_to_merge = st.number_input(
        "Pets Available to Merge",
        min_value=0,
        step=1,
        value=int(existing.get("pets_to_merge", 0)),
    )

  # Mounts
  m1, m2, m3, m4 = st.columns(4)
  with m1:
    mount_summon_lvl = st.number_input(
        "Mount Summon Lvl",
        min_value=0,
        step=1,
        value=int(existing.get("mount_summon_lvl", 0)),
    )
  with m2:
    mount_clockwinders = st.number_input(
        "Mount Clockwinders",
        min_value=0,
        step=1,
        value=int(existing.get("mount_clockwinders", 0)),
    )
  with m3:
    mount_summon_cost = st.number_input(
        "Mount Summon Cost",
        min_value=0,
        step=1,
        value=int(existing.get("mount_summon_cost", 0)),
    )
  with m4:
    mount_extra_chance = st.number_input(
        "Mount Summon Extra Chance (%)",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        value=float(existing.get("mount_extra_chance", 0.0)),
    )

  if st.form_submit_button("Save My Stats & Resources", use_container_width=True):
    upsert_player_resources({
        "player_name": selected_player,
        "damage_lvl": damage_lvl,
        "health_lvl": health_lvl,
        "hammers": hammers,
        "skill_tickets": skill_tickets,
        "skill_summon_cost": skill_summon_cost,
        "skill_level": skill_level,
        "egg_summon_lvl": egg_summon_lvl,
        "egg_summon_chance": egg_summon_chance,
        "pets_to_merge": pets_to_merge,
        "mount_summon_lvl": mount_summon_lvl,
        "mount_clockwinders": mount_clockwinders,
        "mount_summon_cost": mount_summon_cost,
        "mount_extra_chance": mount_extra_chance,
        "clan_tech_vials": clan_tech_vials,
    })
    st.success(f"Saved {selected_player}'s resources to Turso!")
    st.rerun()

st.subheader("Live Clan Resources")
st.dataframe(load_all_player_resources(), use_container_width=True, hide_index=True)
