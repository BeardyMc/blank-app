import streamlit as st
from pvp_utils import (
    format_compact_input,
    load_player_resources,
    parse_stat_value,
    upsert_player_resources,
)

st.title("Clan Resources & Combat Stats")

# Pull player names from existing clan roster in session_state if available
if "players_df" in st.session_state and not st.session_state.players_df.empty:
  roster_names = sorted(
      st.session_state.players_df["Player Name"].dropna().unique().tolist()
  )
else:
  roster_names = ["Mypleasure", "Kitty87", "BeardyMcBeard"]

saved_df = load_player_resources()
selected_player = st.selectbox("Player Name (Clan Roster)", roster_names)

existing = {}
if not saved_df.empty and selected_player in saved_df["player_name"].values:
  existing = (
      saved_df[saved_df["player_name"] == selected_player].iloc[0].to_dict()
  )

with st.form("clan_resources_form"):
  st.subheader(f"Stats & Resources — {selected_player}")

  # Damage & Health (accepts text like '13b' -> 13000000000)
  d1, d2 = st.columns(2)
  with d1:
    damage_input = st.text_input(
        "Damage (e.g. 13b)",
        value=format_compact_input(existing.get("damage_val", 0.0)),
    )
  with d2:
    health_input = st.text_input(
        "Health (e.g. 25b)",
        value=format_compact_input(existing.get("health_val", 0.0)),
    )

  # Hammers, Skill Tickets, Skill Summon Cost, Skill Level
  s1, s2, s3, s4 = st.columns(4)
  with s1:
    hammers = st.number_input(
        "Hammers", min_value=0, step=1, value=int(existing.get("hammers", 0))
    )
  with s2:
    skill_tickets = st.number_input(
        "Skill Tickets",
        min_value=0,
        step=1,
        value=int(existing.get("skill_tickets", 0)),
    )
  with s3:
    skill_summon_cost = st.number_input(
        "Skill Summon Cost",
        min_value=0,
        step=1,
        value=int(existing.get("skill_summon_cost", 0)),
    )
  with s4:
    skill_level = st.number_input(
        "Skill Level",
        min_value=0,
        step=1,
        value=int(existing.get("skill_level", 0)),
    )

  # Egg Summon Lvl, Egg Summon Chance, Pets Available to Merge, Clan Tech Vials
  e1, e2, e3, e4 = st.columns(4)
  with e1:
    egg_summon_lvl = st.number_input(
        "Egg Summon Lvl",
        min_value=0,
        step=1,
        value=int(existing.get("egg_summon_lvl", 0)),
    )
  with e2:
    egg_summon_chance = st.number_input(
        "Egg Summon Chance",
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
  with e4:
    clan_tech_vials = st.number_input(
        "Clan Tech Vials",
        min_value=0,
        step=1,
        value=int(existing.get("clan_tech_vials", 0)),
    )

  # Mount Summon Lvl, Mount Clockwinders, Mount Summon Cost, Mount Summon Extra Chance
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
        "Mount Summon Extra Chance",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        value=float(existing.get("mount_extra_chance", 0.0)),
    )

  if st.form_submit_button("Save to Turso", use_container_width=True):
    try:
      parsed_damage = parse_stat_value(damage_input)
      parsed_health = parse_stat_value(health_input)
    except ValueError as err:
      st.error(str(err))
    else:
      upsert_player_resources({
          "player_name": selected_player,
          "damage_val": parsed_damage,
          "health_val": parsed_health,
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
      st.success(f"Saved {selected_player}'s stats and resources!")
      st.rerun()

st.divider()
st.subheader("Saved Clan Resources")
st.dataframe(load_player_resources(), use_container_width=True, hide_index=True)
 
