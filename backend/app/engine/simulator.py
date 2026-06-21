"""Main possession-event match simulation loop."""

import random

from app.engine.actions import (
    advance_position,
    choose_action,
    choose_pass_target,
    compute_dribble_success,
    compute_pass_success,
    compute_shot_xg,
    compute_tackle_success,
    decay_stamina,
    maybe_foul_card,
    nearest_player,
    pick_ball_carrier,
    recover_stamina_halftime,
)
from app.engine.events import make_event
from app.engine.management import apply_game_plan, maybe_substitute, update_score_state_tactics
from app.engine.penalties import resolve_shootout
from app.engine.pitch import attacking_progress, distance, zone_for_progress
from app.engine.state import TeamState, build_team_state

EVENT_DURATION_RANGE = (0.3, 0.6)


def _other(team: TeamState, home: TeamState, away: TeamState) -> TeamState:
    return away if team is home else home


def simulate_match(
    home_team_id: str,
    away_team_id: str,
    home_players: list[dict],
    away_players: list[dict],
    home_formation: str,
    away_formation: str,
    seed: int,
    allow_draw: bool = True,
    home_tactical_profile: dict | None = None,
    away_tactical_profile: dict | None = None,
) -> dict:
    rng = random.Random(seed)
    home = build_team_state(home_team_id, home_players, home_formation, attacking_direction=1, tactical_profile=home_tactical_profile)
    away = build_team_state(away_team_id, away_players, away_formation, attacking_direction=-1, tactical_profile=away_tactical_profile)
    apply_game_plan(home, away)

    def lineup_snapshot(team: TeamState) -> list[dict]:
        return [
            {"player_id": p.player_id, "name": p.display_name, "slot_position": p.slot_position, "x": p.home_x, "y": p.home_y}
            for p in team.lineup
        ]

    home_lineup = lineup_snapshot(home)
    away_lineup = lineup_snapshot(away)
    # Name lookup for every player who actually appeared (starters + subs
    # brought on), used for post-match player-rating display. Kept separate
    # from home_lineup/away_lineup (starting XI only) so the pitch view's
    # static formation dots aren't affected by substitutions.
    home_roster = {p["player_id"]: p["name"] for p in home_lineup}
    away_roster = {p["player_id"]: p["name"] for p in away_lineup}

    events: list[dict] = []
    ball_x, ball_y = 50.0, 50.0
    clock = 0.0
    halftime_done = False
    et_halftime_done = False
    final_minute = 90.0
    went_to_extra_time = False
    possession_time = {home.team_id: 0.0, away.team_id: 0.0}

    possession = home if rng.random() < 0.5 else away
    events.append(make_event(0, "kickoff", possession.team_id, "キックオフ。", x=50, y=50))
    last_minute_processed = -1

    while True:
        if clock >= final_minute:
            if final_minute == 90.0 and not allow_draw and home.score == away.score:
                went_to_extra_time = True
                final_minute = 120.0
                events.append(make_event(90, "extra_time_start", home.team_id, "延長戦開始。", x=50, y=50))
                recover_stamina_halftime(home)
                recover_stamina_halftime(away)
                ball_x, ball_y = 50.0, 50.0
                continue
            break

        minute = int(clock)
        if minute != last_minute_processed:
            last_minute_processed = minute
            update_score_state_tactics(home, away, clock, final_minute)
            update_score_state_tactics(away, home, clock, final_minute)
            for team, roster in ((home, home_roster), (away, away_roster)):
                sub_event = maybe_substitute(team, minute, rng)
                if sub_event is not None:
                    sub_in = next((p for p in team.lineup if p.player_id == sub_event["player_id"]), None)
                    if sub_in is not None:
                        roster[sub_in.player_id] = sub_in.display_name
                    events.append(sub_event)

        attacker = possession
        defender = _other(possession, home, away)
        possession_time[attacker.team_id] += 1.0

        carrier = pick_ball_carrier(attacker, ball_x, ball_y, rng)
        nearest_def = nearest_player(defender, ball_x, ball_y, exclude_gk=True)
        decay_stamina(carrier, 1.0 + (defender.press_intensity() - 50.0) / 200.0)
        decay_stamina(nearest_def, 0.8 * (1 + (defender.press_intensity() - 50.0) / 100.0))

        action = choose_action(carrier, ball_x, ball_y, attacker.attacking_direction, rng, possession_style=attacker.possession_style())

        if action == "SHOOT":
            keeper = defender.goalkeeper()
            pressure = max(0.0, 1.0 - distance((nearest_def.x, nearest_def.y), (ball_x, ball_y)) / 15.0)
            xg = compute_shot_xg(
                carrier, keeper, ball_x, ball_y, pressure, attacker.attacking_direction,
                defensive_line_height=defender.defensive_line_height(),
            )
            is_goal = rng.random() < xg

            if is_goal:
                attacker.score += 1
                events.append(make_event(
                    minute, "goal", attacker.team_id,
                    f"{carrier.display_name} がゴール!",
                    player_id=carrier.player_id, x=ball_x, y=ball_y,
                    event_metadata={"xg": round(xg, 3)},
                ))
                ball_x, ball_y = 50.0, 50.0
                possession = defender
            else:
                # Real-world shots-on-target rate is ~33% of all shots, not ~60% --
                # a too-high "saved" chance here was inflating shots_on_target far
                # past goals, suppressing the goals/SOT ratio well below reality.
                saved = rng.random() < 0.28
                outcome = "saved" if saved else "off target"
                description = (
                    f"{carrier.display_name} のシュートは {keeper.display_name} にセーブされた。"
                    if saved
                    else f"{carrier.display_name} のシュートは枠を外れた。"
                )
                events.append(make_event(
                    minute, "shot", attacker.team_id,
                    description,
                    player_id=carrier.player_id,
                    secondary_player_id=keeper.player_id if saved else None,
                    x=ball_x, y=ball_y,
                    event_metadata={"xg": round(xg, 3), "outcome": outcome},
                ))
                # Ball stays near the goal that was just shot at (defender's own box),
                # regardless of who restarts play from there.
                gx = 92.0 if attacker.attacking_direction == 1 else 8.0
                gy = 50.0 + rng.uniform(-8, 8)
                ball_x, ball_y = gx, gy
                possession = defender

        elif action in ("PASS", "LONG_BALL"):
            target = choose_pass_target(attacker, carrier, rng)
            pass_distance = distance((carrier.x, carrier.y), (target.x, target.y))
            success_prob = compute_pass_success(carrier, nearest_def, pass_distance, press_intensity=defender.press_intensity())

            if rng.random() < success_prob:
                ball_x, ball_y = target.x, target.y
                progress = attacking_progress(ball_x, attacker.attacking_direction)
                if zone_for_progress(progress) == "ATT_THIRD" and action == "PASS":
                    events.append(make_event(
                        minute, "key_pass", attacker.team_id,
                        f"{carrier.display_name} から {target.display_name} へ決定的なパス。",
                        player_id=carrier.player_id, secondary_player_id=target.player_id,
                        x=ball_x, y=ball_y,
                    ))
            else:
                tackler = nearest_def
                events.append(make_event(
                    minute, "tackle", defender.team_id,
                    f"{tackler.display_name} が {carrier.display_name} のパスをカット。",
                    player_id=tackler.player_id, secondary_player_id=carrier.player_id,
                    x=ball_x, y=ball_y,
                ))
                # A clean interception is usually not a foul -- low card rate.
                card = maybe_foul_card(rng, base_rate=0.03)
                if card is not None:
                    events.append(make_event(
                        minute, f"{card}_card", defender.team_id,
                        f"{tackler.display_name} に {carrier.display_name} へのファウルで{'レッド' if card == 'red' else 'イエロー'}カード。",
                        player_id=tackler.player_id,
                        x=ball_x, y=ball_y,
                    ))
                ball_x, ball_y = tackler.x, tackler.y
                possession = defender

        else:  # DRIBBLE
            new_pos = advance_position((ball_x, ball_y), attacker.attacking_direction, step=10.0, rng=rng)
            success_prob = compute_dribble_success(
                carrier, nearest_def,
                press_intensity=defender.press_intensity(),
                defensive_line_height=defender.defensive_line_height(),
            )

            if rng.random() < success_prob:
                ball_x, ball_y = new_pos
                carrier.x, carrier.y = ball_x, ball_y
            else:
                events.append(make_event(
                    minute, "tackle", defender.team_id,
                    f"{nearest_def.display_name} が {carrier.display_name} からボールを奪った。",
                    player_id=nearest_def.player_id, secondary_player_id=carrier.player_id,
                    x=ball_x, y=ball_y,
                ))
                # Duels for the ball during a dribble are the main real-world
                # foul source -- calibrated against analyze_simulation_quality.py
                # to land near real-world ~3-4 yellows/match combined.
                card = maybe_foul_card(rng, base_rate=0.16)
                if card is not None:
                    events.append(make_event(
                        minute, f"{card}_card", defender.team_id,
                        f"{nearest_def.display_name} に {carrier.display_name} へのファウルで{'レッド' if card == 'red' else 'イエロー'}カード。",
                        player_id=nearest_def.player_id,
                        x=ball_x, y=ball_y,
                    ))
                ball_x, ball_y = nearest_def.x, nearest_def.y
                possession = defender

        clock += rng.uniform(*EVENT_DURATION_RANGE)

        if not halftime_done and clock >= 45.0:
            halftime_done = True
            events.append(make_event(45, "halftime", home.team_id, "前半終了。", x=50, y=50))
            recover_stamina_halftime(home)
            recover_stamina_halftime(away)
            ball_x, ball_y = 50.0, 50.0
        elif went_to_extra_time and not et_halftime_done and clock >= 105.0:
            et_halftime_done = True
            events.append(make_event(105, "extra_time_halftime", home.team_id, "延長前半終了。", x=50, y=50))
            recover_stamina_halftime(home)
            recover_stamina_halftime(away)
            ball_x, ball_y = 50.0, 50.0

    final_event_minute = 120 if went_to_extra_time else 90
    events.append(make_event(final_event_minute, "fulltime", home.team_id, "試合終了。", x=50, y=50, event_metadata={
        "home_score": home.score, "away_score": away.score,
    }))

    went_to_penalties = False
    penalty_home_score = None
    penalty_away_score = None
    if not allow_draw and home.score == away.score:
        went_to_penalties = True
        shootout = resolve_shootout(home, away, rng, start_minute=final_event_minute)
        penalty_home_score = shootout["home_penalty_score"]
        penalty_away_score = shootout["away_penalty_score"]
        events.extend(shootout["events"])

    total_possession_time = possession_time[home.team_id] + possession_time[away.team_id]
    home_possession_pct = (
        round(100.0 * possession_time[home.team_id] / total_possession_time, 1)
        if total_possession_time > 0
        else 50.0
    )

    def _count(event_type: str, team_id: str) -> int:
        return sum(1 for e in events if e["event_type"] == event_type and e["team_id"] == team_id)

    stats = {}
    for team in (home, away):
        shots_on_target = _count("goal", team.team_id) + sum(
            1 for e in events
            if e["event_type"] == "shot" and e["team_id"] == team.team_id and e["event_metadata"].get("outcome") == "saved"
        )
        stats[team.team_id] = {
            "shots": _count("goal", team.team_id) + _count("shot", team.team_id),
            "shots_on_target": shots_on_target,
            "yellow_cards": _count("yellow_card", team.team_id),
            "red_cards": _count("red_card", team.team_id),
        }

    return {
        "home_score": home.score,
        "away_score": away.score,
        "went_to_extra_time": went_to_extra_time,
        "went_to_penalties": went_to_penalties,
        "penalty_home_score": penalty_home_score,
        "penalty_away_score": penalty_away_score,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "home_roster": home_roster,
        "away_roster": away_roster,
        "home_possession_pct": home_possession_pct,
        "away_possession_pct": round(100.0 - home_possession_pct, 1),
        "home_shots": stats[home.team_id]["shots"],
        "away_shots": stats[away.team_id]["shots"],
        "home_shots_on_target": stats[home.team_id]["shots_on_target"],
        "away_shots_on_target": stats[away.team_id]["shots_on_target"],
        "home_yellow_cards": stats[home.team_id]["yellow_cards"],
        "away_yellow_cards": stats[away.team_id]["yellow_cards"],
        "home_red_cards": stats[home.team_id]["red_cards"],
        "away_red_cards": stats[away.team_id]["red_cards"],
        "events": events,
    }
