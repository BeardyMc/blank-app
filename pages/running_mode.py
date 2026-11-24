import pandas as pd
import streamlit as st
from pvp_utils import (
    assign_rank_points,
    build_battle_record,
    calc_effective_power,
    compute_iterative_multipliers,
    format_si_3sf,
    get_live_war_progress,
    get_remaining_attacks_by_side,
    recommend_next_reset_assignments,
    save_battles_to_github,
)

st.title("Running Mode — Live Battle Tracker")

col1, col2 = st.columns(2, wrap=False)
with col1:
  our_damage_lvl = st.number_input(
      "Our Damage Lvl",
      min_value=0,
      max_value=100,
      value=st.session_state.get("our_damage_lvl", 100),
      step=1,
      key="run_our_damage_lvl",
  )
  our_health_lvl = st.number_input(
      "Our Health Lvl",
      min_value=0,
      max_value=100,
      value=st.session_state.get("our_health_lvl", 84),
      step=1,
      key="run_our_health_lvl",
  )
  our_points_multiplier = st.slider(
      "Our Points Multiplier (%)",
      min_value=0,
      max_value=40,
      value=st.session_state.get("our_points_multiplier", 0),
      step=4,
      key="run_our_points_multiplier",
  )

with col2:
  enemy_damage_lvl = st.number_input(
      "Enemy Damage Lvl",
      min_value=0,
      max_value=100,
      value=st.session_state.get("enemy_damage_lvl", 74),
      step=1,
      key="run_enemy_damage_lvl",
  )
  enemy_health_lvl = st.number_input(
      "Enemy Health Lvl",
      min_value=0,
      max_value=100,
      value=st.session_state.get("enemy_health_lvl", 50),
      step=1,
      key="run_enemy_health_lvl",
  )
  enemy_points_multiplier = st.slider(
      "Enemy Points Multiplier (%)",
      min_value=0,
      max_value=40,
      value=st.session_state.get("enemy_points_multiplier", 40),
      step=4,
      key="run_enemy_points_multiplier",
  )

players_eff = assign_rank_points(
    calc_effective_power(
        st.session_state.players_df, our_damage_lvl, our_health_lvl
    ),
    power_col="Effective Power",
)
enemies_eff = assign_rank_points(
    calc_effective_power(
        st.session_state.enemies_df, enemy_damage_lvl, enemy_health_lvl
    ),
    power_col="Effective Power",
)

valid_players_eff = players_eff[
    players_eff["Player Name"].notna()
    & (players_eff["Player Name"].astype(str).str.strip() != "")
].copy()
valid_enemies_eff = enemies_eff[
    enemies_eff["Player Name"].notna()
    & (enemies_eff["Player Name"].astype(str).str.strip() != "")
].copy()

clan_names = valid_players_eff["Player Name"].tolist()
enemy_names = valid_enemies_eff["Player Name"].tolist()

war_progress = get_live_war_progress(
    st.session_state.battles_df,
    total_players=len(valid_players_eff),
    total_enemies=len(valid_enemies_eff),
    attacks_per_player=5,
)
edgr_rem_map, _ = get_remaining_attacks_by_side(
    st.session_state.battles_df,
    clan_names,
    enemy_names,
    attacks_per_player=5,
)
player_mult_map, enemy_mult_map, mult_summary_df = (
    compute_iterative_multipliers(
        st.session_state.battles_df,
        valid_players_eff,
        valid_enemies_eff,
        n_iters=8,
    )
)

st.subheader("📊 Live War Progress")
p1, p2, p3 = st.columns(3, wrap=False)
p1.metric(
    "EDGR Battles Remaining",
    f"{war_progress['remaining_battles']} / {war_progress['max_battles']}",
)
p2.metric(
    "Defeats Left to Reset",
    f"{war_progress['defeats_left_to_reset']} / {war_progress['reset_threshold']}",
)
p3.metric("Total EDGR Wins", war_progress["edgr_wins"])

st.subheader("🎯 Personal Matchups & Remaining Battles")
selected_runner = st.selectbox(
    "Who are you?", options=clan_names, key="run_selected_player"
)
run_safety_pct = st.slider(
    "Target Safety Margin (% of Adjusted Attacker Power):",
    min_value=50,
    max_value=150,
    value=90,
    step=1,
    key="run_safety_margin_pct",
)
run_safety_margin = float(run_safety_pct) / 100.0

if selected_runner:
  rem_count = edgr_rem_map.get(selected_runner, 5)
  st.info(f"**{selected_runner} remaining battles = {rem_count}**")

  runner_row = valid_players_eff[
      valid_players_eff["Player Name"] == selected_runner
  ].iloc[0]
  base_p = float(
      pd.to_numeric(runner_row["Effective Power"], errors="coerce") or 0.0
  )
  my_mult = float(player_mult_map.get(selected_runner, 1.0))
  my_adj_power = base_p * my_mult

  st.metric(
      label=f"{selected_runner}'s Adjusted Effective Power (x{my_mult:.3f})",
      value=format_si_3sf(my_adj_power),
      delta=f"Raw Eff Power: {format_si_3sf(base_p)}",
      delta_color="off",
  )

  defeated_set = {
      str(x).strip()
      for x in (war_progress.get("defeated_this_cycle") or [])
      if str(x).strip()
  }

  enemies_scored = valid_enemies_eff.copy()
  enemies_scored["Mult"] = enemies_scored["Player Name"].map(
      lambda n: float(enemy_mult_map.get(n, 1.0))
  )
  enemies_scored["Adj_Power_Num"] = (
      pd.to_numeric(enemies_scored["Effective Power"], errors="coerce").fillna(0.0)
      * enemies_scored["Mult"]
  )
  enemies_scored["Est Points"] = (
      pd.to_numeric(enemies_scored["Points"], errors="coerce").fillna(0)
      * (1.0 + our_points_multiplier / 100.0)
  ).apply(round)

  winnable_now = enemies_scored[
      (my_adj_power * run_safety_margin) >= enemies_scored["Adj_Power_Num"]
  ].sort_values(by=["Est Points", "Adj_Power_Num"], ascending=[False, False])

  st.write(f"**Suggested Enemies You Can Beat ({len(winnable_now)}):**")
  if rem_count <= 0:
    st.warning(f"{selected_runner} has 0 remaining battles for today.")
  elif not winnable_now.empty:
    display_winnable = winnable_now[
        ["Player Name", "Rank", "Est Points", "Mult", "Adj_Power_Num"]
    ].copy()
    display_winnable["Status"] = display_winnable["Player Name"].apply(
        lambda name: "(next cycle)"
        if str(name).strip() in defeated_set
        else "Available"
    )
    display_winnable["Adjusted Eff Power"] = display_winnable[
        "Adj_Power_Num"
    ].apply(format_si_3sf)
    display_winnable = display_winnable[
        [
            "Status",
            "Player Name",
            "Rank",
            "Est Points",
            "Mult",
            "Adjusted Eff Power",
        ]
    ]
    st.dataframe(display_winnable, hide_index=True, use_container_width=True)
  else:
    st.warning("No enemies meet your adjusted power & safety margin right now.")

st.subheader("🧭 Best Attackers for Remaining Defeats Before Next Reset")
reset_recs_df = recommend_next_reset_assignments(
    players_eff=valid_players_eff,
    enemies_eff=valid_enemies_eff,
    player_mult_map=player_mult_map,
    enemy_mult_map=enemy_mult_map,
    remaining_map=edgr_rem_map,
    safety_margin=run_safety_margin,
    reset_remaining=war_progress["defeats_left_to_reset"],
    points_multiplier=1.0 + our_points_multiplier / 100.0,
    already_defeated=war_progress["defeated_this_cycle"],
)

if not reset_recs_df.empty:
  st.dataframe(reset_recs_df, hide_index=True, use_container_width=True)
else:
  st.info(
      "No remaining eligible matchups found with current remaining battles and"
      " safety margin."
  )

st.subheader("📡 Record Battle Result & Manage Log")
with st.expander("Record a Battle Result", expanded=True):
  r_c1, r_c2 = st.columns(2, wrap=False)
  with r_c1:
    att_side = st.selectbox(
        "Attacker Side", ["EDGR", "EX"], key="live_att_side"
    )

  att_options = clan_names if att_side == "EDGR" else enemy_names

  if (
      att_side == "EDGR"
      and selected_runner in att_options
      and st.session_state.get("_last_synced_runner") != selected_runner
  ):
    st.session_state["live_att_player"] = selected_runner
    st.session_state["_last_synced_runner"] = selected_runner
  elif (
      st.session_state.get("live_att_player") not in att_options
      and att_options
  ):
    st.session_state["live_att_player"] = att_options[0]

  with r_c1:
    att_player = st.selectbox(
        "Attacker", options=att_options, key="live_att_player"
    )
  with r_c2:
    outcome_choice = st.selectbox(
        "Attacker Result", ["Won", "Lost"], key="live_att_outcome"
    )

    dfnd_options = enemy_names if att_side == "EDGR" else clan_names
    dfnd_player = st.selectbox(
        "Defender", options=dfnd_options, key="live_dfnd_player"
    )

  dfnd_side = "EX" if att_side == "EDGR" else "EDGR"

  if st.button("Log Battle", key="log_battle_btn"):
    if att_player and dfnd_player:
      record = build_battle_record(
          attacker_side=att_side,
          attacker=att_player,
          defender_side=dfnd_side,
          defender=dfnd_player,
          attacker_won=(outcome_choice == "Won"),
      )
      st.session_state.battles_df = pd.concat(
          [st.session_state.battles_df, pd.DataFrame([record])],
          ignore_index=True,
      )
      st.rerun()

st.dataframe(
    st.session_state.battles_df,
    hide_index=True,
    use_container_width=True,
)

with st.expander(
    "Save Battle Log to GitHub (`data/pvp_battles.json`)", expanded=False
):
  battle_commit_msg = st.text_input(
      "Battle Log Commit Message",
      value="Update live PvP battle log",
      key="battle_commit_msg_input",
  )
  if st.button("Push Battles to GitHub", key="push_battles_btn"):
    ok, msg = save_battles_to_github(
        st.session_state.battles_df,
        commit_message=battle_commit_msg.strip() or "Update live PvP battle log",
    )
    if ok:
      st.success(msg)
    else:
      st.error(msg)

if not mult_summary_df.empty:
  st.markdown("#### Learned Player Multipliers & Adjusted Effective Power")
  st.dataframe(mult_summary_df, hide_index=True, use_container_width=True)
