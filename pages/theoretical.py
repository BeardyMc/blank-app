import math
import pandas as pd
import streamlit as st
from pvp_utils import (
    assign_rank_points,
    build_cycle_summary_tables,
    calc_effective_power,
    format_df_powers,
    format_si_3sf,
    get_reset_threshold,
    simulate_battles,
    sum_roster_power,
)

st.title("Day 6 PvP Planner")
st.caption(
    "Read-only roster view formatted in in-game units. Use the Roster Editor"
    " page to make roster changes."
)

DISPLAY_COLS = ["Rank", "Player Name", "Power (b)"]

left_col, right_col = st.columns(2, wrap=False)

with left_col:
  our_total_power = format_si_3sf(sum_roster_power(st.session_state.players_df))
  st.subheader(f"EDGR: {our_total_power}")
  players_view = (
      st.session_state.players_df[
          [c for c in DISPLAY_COLS if c in st.session_state.players_df.columns]
      ]
      if not st.session_state.players_df.empty
      else pd.DataFrame(columns=DISPLAY_COLS)
  )
  st.dataframe(
      format_df_powers(players_view, power_cols=("Power (b)",)),
      hide_index=True,
      use_container_width=True,
  )

with right_col:
  enemy_total_power = format_si_3sf(sum_roster_power(st.session_state.enemies_df))
  st.subheader(f"Enemies: {enemy_total_power}")
  enemies_view = (
      st.session_state.enemies_df[
          [c for c in DISPLAY_COLS if c in st.session_state.enemies_df.columns]
      ]
      if not st.session_state.enemies_df.empty
      else pd.DataFrame(columns=DISPLAY_COLS)
  )
  st.dataframe(
      format_df_powers(enemies_view, power_cols=("Power (b)",)),
      hide_index=True,
      use_container_width=True,
  )

st.divider()
st.subheader("⚙️ Brawl Tech")

col1, col2 = st.columns(2, wrap=False)
with col1:
  our_damage_lvl = st.number_input(
      "Our Damage Lvl",
      min_value=0,
      max_value=100,
      value=100,
      step=1,
      key="our_damage_lvl",
  )
  our_health_lvl = st.number_input(
      "Our Health Lvl",
      min_value=0,
      max_value=100,
      value=84,
      step=1,
      key="our_health_lvl",
  )
  our_points_multiplier = st.slider(
      "Our Points Multiplier (%)",
      min_value=0,
      max_value=40,
      value=0,
      step=4,
      key="our_points_multiplier",
  )

with col2:
  enemy_damage_lvl = st.number_input(
      "Enemy Damage Lvl",
      min_value=0,
      max_value=100,
      value=74,
      step=1,
      key="enemy_damage_lvl",
  )
  enemy_health_lvl = st.number_input(
      "Enemy Health Lvl",
      min_value=0,
      max_value=100,
      value=50,
      step=1,
      key="enemy_health_lvl",
  )
  enemy_points_multiplier = st.slider(
      "Enemy Points Multiplier (%)",
      min_value=0,
      max_value=40,
      value=40,
      step=4,
      key="enemy_points_multiplier",
  )

players_eff = calc_effective_power(
    st.session_state.players_df, our_damage_lvl, our_health_lvl
)
enemies_eff = calc_effective_power(
    st.session_state.enemies_df, enemy_damage_lvl, enemy_health_lvl
)

players_eff = assign_rank_points(players_eff, power_col="Effective Power")
enemies_eff = assign_rank_points(enemies_eff, power_col="Effective Power")

valid_players_eff = players_eff[
    players_eff["Player Name"].notna()
    & (players_eff["Player Name"].astype(str).str.strip() != "")
].copy()
valid_enemies_eff = enemies_eff[
    enemies_eff["Player Name"].notna()
    & (enemies_eff["Player Name"].astype(str).str.strip() != "")
].copy()

clan_names = valid_players_eff["Player Name"].tolist()
reset_threshold = get_reset_threshold(len(valid_enemies_eff))

st.divider()
st.subheader("⚔️ Select Your Player & Find Matchups")
selected_player = st.selectbox(
    "Who are you?", options=clan_names, key="theo_selected_player"
)

safety_margin_pct = st.slider(
    "Target Safety Margin (% of Attacker Effective Power)\n\n(aka how good is"
    " your build vs theirs):",
    min_value=50,
    max_value=150,
    value=90,
    step=1,
    key="theo_safety_margin_pct",
)
safety_margin = float(safety_margin_pct or 100.0) / 100.0

if selected_player:
  player_matches = valid_players_eff[
      valid_players_eff["Player Name"] == selected_player
  ]
  if not player_matches.empty:
    player_row = player_matches.iloc[0]
    my_eff_power = float(
        pd.to_numeric(player_row["Effective Power"], errors="coerce") or 0.0
    )
    max_target_power = my_eff_power * safety_margin
    enemy_mult = 1.0 + ((enemy_damage_lvl or 0) + (enemy_health_lvl or 0)) / 2.0

    st.metric(
        label=f"{selected_player}'s Effective Power",
        value=format_si_3sf(my_eff_power),
        delta=(
            "Safe target cap:"
            f" {format_si_3sf(max_target_power / enemy_mult)}"
            f" ({safety_margin_pct:.0f}%)"
        ),
        delta_color="off",
    )

    winnable_enemies = valid_enemies_eff[
        pd.to_numeric(valid_enemies_eff["Effective Power"], errors="coerce")
        .fillna(math.inf)
        <= max_target_power
    ]

    st.write(f"**Battleable Enemies ({len(winnable_enemies)}):**")
    st.dataframe(
        format_df_powers(
            winnable_enemies[["Player Name", "Power (b)", "Effective Power"]]
        ),
        hide_index=True,
        use_container_width=True,
    )

st.subheader(
    f"🏆 Theoretical Max Points ({len(valid_players_eff) * 5} Battles /"
    f" {reset_threshold}-Enemy Reset)"
)

if st.button("Run Theoretical Max Simulation", key="run_theo_sim_btn"):
  sim = simulate_battles(
      valid_players_eff,
      valid_enemies_eff,
      attacks_per_player=5,
      reset_threshold=reset_threshold,
      safety_margin=safety_margin,
      points_multiplier=1 + our_points_multiplier / 100,
  )

  m1, m2, m3 = st.columns(3, wrap=False)
  m1.metric("Total Wins", f"{sim['total_wins']} / {sim['max_possible_battles']}")
  m2.metric("Projected Points", f"{sim['total_points']:,.0f}")
  m3.metric(f"Full {reset_threshold}-Defeat Resets", sim["cycles_completed"])

  if not sim["log_df"].empty:
    st.dataframe(sim["log_df"], hide_index=True, use_container_width=True)
  else:
    st.warning("No battles can be won with the current powers and levels.")

  st.divider()
  st.subheader("🛡️ Possible Enemy Wins")

  sim_enemy = simulate_battles(
      valid_enemies_eff,
      valid_players_eff,
      attacks_per_player=5,
      reset_threshold=reset_threshold,
      safety_margin=(1 / safety_margin),
      points_multiplier=1 + enemy_points_multiplier / 100,
  )

  e1, e2, e3 = st.columns(3, wrap=False)
  e1.metric(
      "Enemy Wins vs Us",
      f"{sim_enemy['total_wins']} / {sim_enemy['max_possible_battles']}",
  )
  e2.metric("Points Enemies Could Score", f"{sim_enemy['total_points']:,.0f}")
  e3.metric(f"Full {reset_threshold}-Defeat Resets", sim_enemy["cycles_completed"])

  if not sim_enemy["log_df"].empty:
    st.dataframe(sim_enemy["log_df"], hide_index=True, use_container_width=True)
  else:
    st.success("Enemies can't beat any of our players with current stats!")

  enemy_cycles_df, our_targets_df = build_cycle_summary_tables(
      sim["log_df"], valid_enemies_eff, valid_players_eff
  )

  st.markdown("#### Who should target each Enemy by Cycle")
  st.dataframe(enemy_cycles_df, hide_index=True, use_container_width=True)

  st.markdown("#### Our Players' Assigned Enemies")
  st.dataframe(our_targets_df, hide_index=True, use_container_width=True)
