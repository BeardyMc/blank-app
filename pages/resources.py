import streamlit as st
from pvp_utils import (
    ensure_player_resources_table,
    format_compact_input,
    load_player_resources,
    parse_stat_value,
    upsert_player_resources,
)

st.title("Clan Resources & Combat Stats")

# First-run check: ensure the Turso table exists before querying
if "turso_resources_ready" not in st.session_state:
  ensure_player_resources_table()
  st.session_state.turso_resources_ready = True

# Pull player names from existing clan roster in session_state if available, else fallback
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

def skill_lvl_parse(skill_lvl_t: str):
  """Parses 'L_sl_A' (e.g. '10_20_2') into (level, sub_level, ascension)."""
  parts = str(skill_lvl_t).strip().split("_")
  if len(parts) != 3:
    raise ValueError(f"Expected 'L_sl_A' format, got '{skill_lvl_t}'")

  lvl, sub_lvl, ascension = (int(p) for p in parts)
  return lvl, sub_lvl, ascension


with st.form("clan_resources_form"):
  st.subheader(f"Stats & Resources — {selected_player}")

  d1, d2 = st.columns(2, wrap=False)
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

  s1, s2 = st.columns(2,wrap=False)
  with s1:
    hammers = st.number_input(
        "Hammers", min_value=0, step=1, value=int(existing.get("hammers", 0))
    )
  with s2:
    clan_tech_vials = st.number_input(
        "Clan Tech Vials",
        min_value=0,
        step=1,
        value=int(existing.get("clan_tech_vials", 0)),
    ) 

  st.divider()

  s3, s4 = st.columns(2,wrap=False)
  with s3:
    skill_tickets = st.number_input(
        "Skill Tickets",
        min_value=0,
        step=1,
        value=int(existing.get("skill_tickets", 0)),
    )
  with s4:
    skill_summon_cost = st.slider(
        "Skill Summon Cost",
        min_value=200,
        step=1,
        max_value=140, 
        value=int(existing.get("skill_summon_cost", 200)),
    )
  s5, s6, s7 = st.columns(3, wrap=False)
  existing_skill_lvl = existing.get("skill_level", "0_0_0")
  ex_L, ex_sl, ex_A = skill_lvl_parse(existing_skill_lvl)
  with s5:
    skill_level1 = st.number_input(
        "Skill Level",
        min_value=0,
        step=1,
        max_value=150,
        value=ex_L
    )
  with s6:
    skill_level2 = st.number_input(
        "Level Progression",
        min_value=0,
        step=1,
        max_value=1500,
        value=ex_sl
    )
  with s7:
    skill_level3 = st.number_input(
        "Skill Ascensions",
        min_value=0,
        step=1,
        max_value=3,
        value=ex_A
    )
  skill_level = f"{int(skill_level1)}_{int(skill_level2)}_{int(skill_level3)}"

  st.divider() 

  e1, e2, e3 = st.columns(3, wrap=False)
  with e1:
    eggshells = st.number_input(
        "Eggshells",
        min_value=0, 
        step=1,
        value=int(existing.get("Eggshells", 0)),
    )
  with e2:
    egg_summon_chance = st.number_input(
        "Egg Summon Chance",
        min_value=0,
        step=1,
        max_value=50,
        value=int(existing.get("egg_summon_chance", 0)),
    )
  with e3:
    pets_to_merge = st.number_input(
        "Mergers Available",
        min_value=0,
        step=1,
        value=int(existing.get("pets_to_merge", 0)),
    )
  e4, e5, e6 = st.columns(3, wrap=False)
  ex_egg_summon_l = existing.get("egg_summon_lvl", "0_0_0")
  ex_e1, ex_e2, ex_e3 = skill_lvl_parse(ex_egg_summon_l)
  with e4:
    egg_summon_lvl1 = st.number_input(
        "Egg Summon Lvl",
        min_value=0,
        step=1,
        max_value=150, 
        value=ex_e1
    )
  with e5:
    egg_summon_lvl2 = st.number_input(
        "Level Progression",
        min_value=0,
        step=1,
        max_value=473, 
        value=ex_e2
    )
  with e6:
    egg_summon_lvl3 = st.number_input(
        "Pet Ascensions",
        min_value=0,
        step=1,
        max_value=3, 
        value=ex_e3
    )
  egg_summon_lvl=f"{egg_summon_lvl1}_{egg_summon_lvl2}_{egg_summon_lvl3}"

  st.divider()

  m1, m2 = st.columns(2, wrap=False)
  with m1:
    mount_clockwinders = st.number_input(
        "Mount Clockwinders",
        min_value=0,
        step=1,
        value=int(existing.get("mount_clockwinders", 0)),
    )
  with m2:
    mount_mergers = st.number_input(
        "Mount Mergers",
        min_value=0,
        step=1,
        value=int(existing.get("mount_mergers", 0)),
    )
  m3, m4 = st.columns(2, wrap=False)
  with m3:
    mount_cost_reduction = st.slider(
        "Mount Cost Reduction",
        min_value=0,
        step=1,
        max_value=30, 
        value=int(existing.get("mount_cost_reduction", 0)),
    )
  with m4:
    mount_extra_chance = st.slider(
        "Mount Summon Extra Chance",
        min_value=0,
        step=1, 
        max_value=50, 
        value=int(existing.get("mount_extra_chance", 0)),
    )

  m5, m6, m7 = st.columns(3,wrap=False)
  ex_mount_lvl = existing.get("mount_summon_lvl", "0_0_0") 
  ex_e1, ex_e2, ex_e3 = skill_lvl_parse(ex_mount_lvl)
  with m5:
    mount_summon_lvl1 = st.number_input(
        "Mount Summon Lvl",
        min_value=0,
        step=1,
        max_value=150, 
        value=ex_e1
    )
  with m6:
    mount_summon_lvl2 = st.number_input(
        "Level Progression",
        min_value=0,
        step=1,
        max_value=620,
        value=ex_e2
    )
  with m7:
    mount_summon_lvl3 = st.number_input(
        "Mount Ascensions",
        min_value=0,
        step=1,
        max_value=3,
        value=ex_e3
    )
  mount_summon_lvl = f"{mount_summon_lvl1} _{mount_summon_lvl2}_{mount_summon_lvl3}"

  st.divider()

  if st.form_submit_button("Save to Database", use_container_width=True):
    try:
      parsed_damage = parse_stat_value(damage_input)
      parsed_health = parse_stat_value(health_input)
    except ValueError as err:
      st.error(str(err))
    else:
      if upsert_player_resources({
          "player_name": selected_player,
          "damage_val": parsed_damage,
          "health_val": parsed_health,
          "hammers": hammers,
          "skill_tickets": skill_tickets,
          "skill_summon_cost": skill_summon_cost,
          "skill_level": skill_level,
          "Eggshells": eggshells,
          "egg_summon_lvl": egg_summon_lvl,
          "egg_summon_chance": egg_summon_chance,
          "pets_to_merge": pets_to_merge,
          "mount_summon_lvl": mount_summon_lvl,
          "mount_clockwinders": mount_clockwinders,
          "mount_cost_reduction": mount_cost_reduction,
          "mount_extra_chance": mount_extra_chance,
          "mount_mergers": mount_mergers, 
          "clan_tech_vials": clan_tech_vials,
      }):
        st.success(f"Saved {selected_player}'s stats and resources!")
      else:
        st.error("Failed to update database. Please try again.") 

st.divider()
st.subheader("Saved Clan Resources")
st.dataframe(load_player_resources(), width=" stretch", hide_index=True)
