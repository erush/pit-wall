from __future__ import annotations

from src.pitwall.schemas import (
    AvailableActionResponse,
    CarStateResponse,
    DecisionResponse,
    EventResponse,
    FieldCarResponse,
    FieldStateResponse,
    FieldStrategyResponse,
    RaceResultResponse,
    RaceStateResponse,
    RecentRunAnalysisResponse,
    StageResultResponse,
    StageRunningOrderEntryResponse,
    StrategyActionCountResponse,
)
from src.simulation.models import CarState, RaceConfig, RaceEvent, RacePhase, RaceResult, StrategyAction, StrategyDecision


def stage_for_lap(config: RaceConfig, lap: int) -> int:
    stage = 1
    for stage_end in config.stage_ends:
        if lap > stage_end:
            stage += 1
    return stage


def laps_to_stage_end(config: RaceConfig, lap: int) -> int | None:
    next_stage = min([stage_end for stage_end in config.stage_ends if stage_end > lap], default=None)
    if next_stage is None:
        return None
    return next_stage - lap


def leader_label(car: CarState) -> str:
    return f"#{car.car_number} {car.driver.display_name}"


def car_label(car: CarState | None) -> str | None:
    if car is None:
        return None
    return f"#{car.car_number} {car.driver.display_name}"


def recent_pace(car: CarState, laps: int = 5) -> float | None:
    sample = car.recent_lap_times[-laps:]
    if not sample:
        return None
    return round(sum(sample) / len(sample), 3)


def gap_to_leader(car: CarState, leader: CarState) -> float:
    return round(max(0.0, car.total_time_seconds - leader.total_time_seconds), 3)


def recent_run_analysis(field: list[CarState], car: CarState, snapshots: list, baseline_tire_life: int) -> RecentRunAnalysisResponse:
    def relative_pace(laps: int) -> float | None:
        user_sample = car.recent_lap_times[-laps:]
        field_samples = [lap for other in field if other.active for lap in other.recent_lap_times[-laps:]]
        if not user_sample or not field_samples:
            return None
        return round((sum(user_sample) / len(user_sample)) - (sum(field_samples) / len(field_samples)), 3)

    previous_position = snapshots[-6].user_position if len(snapshots) >= 6 else car.start_position
    delta = previous_position - car.position
    if car.tire.age_laps >= baseline_tire_life:
        falloff = "HIGH"
    elif car.tire.age_laps >= int(baseline_tire_life * 0.7):
        falloff = "MEDIUM"
    else:
        falloff = "LOW"
    return RecentRunAnalysisResponse(
        last_5_lap_relative_pace=relative_pace(5),
        last_10_lap_relative_pace=relative_pace(10),
        positions_gained_recently=max(0, delta),
        positions_lost_recently=max(0, -delta),
        simulated_tire_falloff_signal=falloff,
    )


def race_state_response(session) -> RaceStateResponse:
    sim = session.simulation
    total_laps = int(sim.config.scheduled_laps.value)
    current_stage = stage_for_lap(sim.config, sim.lap)
    return RaceStateResponse(
        session_id=session.session_id,
        track_id=sim.config.track.track_id,
        track_name=sim.config.track.name,
        track_type=sim.config.track.track_type,
        track_length_miles=float(sim.config.track.length_miles.value),
        race_laps=total_laps,
        lap=sim.lap,
        total_laps=total_laps,
        stage=current_stage,
        race_status=sim.phase.value,
        caution_status="NONE" if sim.phase == RacePhase.GREEN else sim.phase.value,
        leader=leader_label(sim.field[0]),
        user_position=sim.user_car.position,
        cars_active=sum(1 for car in sim.field if car.active),
        laps_remaining=max(0, total_laps - sim.lap),
        control_mode=session.control_mode,
        current_controller=session.current_controller,
        delegation_status=session.delegation_status,
        objective=session.objective,
        current_stage=current_stage,
        completed_stages=stage_result_responses(session),
    )


def car_state_response(session) -> CarStateResponse:
    sim = session.simulation
    car = sim.user_car
    return CarStateResponse(
        car_number=car.car_number,
        driver_name=car.driver.display_name,
        team_name=car.team.display_name,
        position=car.position,
        starting_position=car.start_position,
        fuel_remaining=round(car.fuel.remaining_laps, 2),
        estimated_fuel_laps=round(car.fuel.remaining_laps, 2),
        tire_age=car.tire.age_laps,
        pace_mode=car.current_action.value,
        recent_pace=recent_pace(car),
        gap_to_leader=gap_to_leader(car, sim.field[0]),
        pit_stops=len(car.pit_stops),
        provenance={
            "fuel": "MODELED",
            "tires": "MODELED",
            "recent_pace": "SIMULATED",
            "position": "SIMULATED",
        },
        recent_run=recent_run_analysis(sim.field, car, sim.snapshots, int(sim.config.baseline_tire_life_laps.value)),
    )


def field_strategy_summary(session) -> tuple[str, ...]:
    sim = session.simulation
    lap = sim.lap
    recent_pitters = [event for event in sim.events if event.event_type == "PitStopCompleted" and lap - 3 <= event.lap <= lap]
    lead_lap_cars = [car for car in sim.field if car.active and car.laps_completed == sim.field[0].laps_completed]
    older_tires = [car for car in lead_lap_cars if car.tire.age_laps >= sim.user_car.tire.age_laps + 8]
    two_tire_calls = [
        event
        for event in recent_pitters
        if event.message == "PIT_2_TIRES" and sim.phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK}
    ]
    leader = sim.field[0]
    leader_recently_pitted = bool(leader.pit_stops and lap - 3 <= leader.pit_stops[-1].lap <= lap)
    return (
        f"{len(recent_pitters)} cars pitted in the last 3 laps.",
        f"{len(older_tires)} lead-lap cars remain on older tires than your car.",
        f"{len(two_tire_calls)} cars took two tires under the current caution or stage break.",
        "The leader pitted recently." if leader_recently_pitted else "The leader stayed out recently.",
    )


ACTION_LABELS = {
    StrategyAction.STAY_OUT.value: "Stay Out",
    StrategyAction.PIT_4_TIRES.value: "4 Tires + Fuel",
    StrategyAction.PIT_2_TIRES.value: "2 Tires + Fuel",
    StrategyAction.PIT_FUEL_ONLY.value: "Fuel Only",
    StrategyAction.SHORT_PIT.value: "Short Pit",
    StrategyAction.EXTEND_STINT.value: "Extend Stint",
    StrategyAction.NORMAL_PACE.value: "Normal Pace",
    StrategyAction.SAVE_FUEL.value: "Save Fuel",
}


def field_strategy_response(session, window_laps: int = 3) -> FieldStrategyResponse:
    sim = session.simulation
    minimum_lap = max(0, sim.lap - window_laps)
    latest_by_car: dict[str, RaceEvent] = {}
    for event in sim.events:
        if event.car_id is None or event.car_id == session.human_car_id or event.lap < minimum_lap or event.lap > sim.lap:
            continue
        if event.event_type not in {"CompetitorStrategyCommitted", "PitStopCompleted"}:
            continue
        latest_by_car[event.car_id] = event

    counts: dict[str, int] = {}
    for event in latest_by_car.values():
        action = event.message.replace("auto:", "")
        counts[action] = counts.get(action, 0) + 1

    action_counts = tuple(
        StrategyActionCountResponse(action=action, label=ACTION_LABELS.get(action, action.replace("_", " ").title()), count=count)
        for action, count in sorted(counts.items(), key=lambda item: (-item[1], ACTION_LABELS.get(item[0], item[0])))
    )
    acted_count = len(latest_by_car)
    autonomous_total = max(0, len(sim.field) - 1)
    distinct_actions = len(action_counts)
    if distinct_actions >= 3:
        split_level = "HIGH"
    elif distinct_actions == 2:
        split_level = "MEDIUM"
    else:
        split_level = "LOW"
    note = (
        f"Derived from recorded opponent strategy and pit-stop events from laps {minimum_lap}-{sim.lap}."
        if acted_count
        else f"No opponent strategy calls are recorded from laps {minimum_lap}-{sim.lap}."
    )
    return FieldStrategyResponse(
        lap=sim.lap,
        window_laps=window_laps,
        autonomous_pit_walls=autonomous_total,
        acted_count=acted_count,
        unrecorded_count=max(0, autonomous_total - acted_count),
        split_level=split_level,
        split_rule="LOW = 0-1 recorded action types; MEDIUM = 2; HIGH = 3+.",
        action_counts=action_counts,
        note=note,
    )


def field_state_response(session, window: int = 9, debug: bool = False) -> FieldStateResponse:
    sim = session.simulation
    total = len(sim.field)
    user_index = max(0, sim.user_car.position - 1)
    half = max(1, window // 2)
    start = max(0, min(user_index - half, total - window))
    end = min(total, start + window)
    leader = sim.field[0]
    rows = []
    for car in sim.field[start:end]:
        rows.append(_field_car_response(car, leader, debug))
    return FieldStateResponse(session.session_id, sim.lap, tuple(rows), field_strategy_summary(session), field_strategy_response(session))


def full_field_response(session, debug: bool = False) -> tuple[FieldCarResponse, ...]:
    sim = session.simulation
    leader = sim.field[0]
    return tuple(_field_car_response(car, leader, debug) for car in sim.field)


def stage_result_responses(session) -> tuple[StageResultResponse, ...]:
    sim = session.simulation
    cars_by_id = {car.car_id: car for car in sim.field}
    rows = []
    for stage in sim.stage_results:
        winner = cars_by_id[stage.winner_car_id]
        top_10 = tuple(
            StageRunningOrderEntryResponse(
                position=position,
                car_number=cars_by_id[car_id].car_number,
                driver_name=cars_by_id[car_id].driver.display_name,
            )
            for position, car_id in enumerate(stage.top_10, start=1)
            if car_id in cars_by_id
        )
        rows.append(
            StageResultResponse(
                stage_number=stage.stage_number,
                completion_lap=stage.completion_lap,
                winner_car_number=winner.car_number,
                winner_driver_name=winner.driver.display_name,
                user_position=stage.user_position,
                top_10=top_10,
            )
        )
    return tuple(rows)


def _field_car_response(car: CarState, leader: CarState, debug: bool) -> FieldCarResponse:
    return FieldCarResponse(
        position=car.position,
        car_number=car.car_number,
        driver_name=car.driver.display_name,
        team_name=car.team.display_name,
        laps_down=max(0, leader.laps_completed - car.laps_completed),
        tire_age=car.tire.age_laps,
        estimated_fuel_laps=round(car.fuel.remaining_laps, 2),
        last_pit_lap=car.pit_stops[-1].lap if car.pit_stops else None,
        gap_to_leader=gap_to_leader(car, leader),
        strategy_archetype=car.policy.archetype.value if debug else None,
    )


def decision_response(session, decision: StrategyDecision) -> DecisionResponse:
    sim = session.simulation
    car = sim.user_car
    action_rows = tuple(
        AvailableActionResponse(
            action=option.action.value,
            label=option.label,
            short_description=option.reason,
            eligible=option.eligible,
            reason=option.reason,
        )
        for option in decision.available_actions
    )
    return DecisionResponse(
        session_id=session.session_id,
        decision_id=session.current_decision_id,
        lap=decision.lap,
        position=decision.position,
        reason=decision.reason_for_decision,
        race_context=decision.race_phase.value,
        fuel_remaining=decision.fuel_remaining_laps,
        estimated_fuel_laps=decision.fuel_remaining_laps,
        tire_age=decision.tire_age_laps,
        laps_to_stage_end=laps_to_stage_end(sim.config, decision.lap),
        laps_to_race_end=max(0, int(sim.config.scheduled_laps.value) - decision.lap),
        recent_pace=decision.recent_pace_seconds,
        recent_run=recent_run_analysis(sim.field, car, sim.snapshots, int(sim.config.baseline_tire_life_laps.value)),
        field_strategy_summary=field_strategy_summary(session),
        available_actions=action_rows,
    )


def event_response(cursor: int, event: RaceEvent, session) -> EventResponse:
    car = next((candidate for candidate in session.simulation.field if candidate.car_id == event.car_id), None)
    message = event.message
    field_by_id = {candidate.car_id: candidate for candidate in session.simulation.field}
    for car_id, subject in field_by_id.items():
        label = car_label(subject)
        if label:
            message = message.replace(car_id, label)
    return EventResponse(
        cursor=cursor,
        event_type=event.event_type,
        lap=event.lap,
        message=message,
        actor=str(event.data["actor"]) if "actor" in event.data else None,
        car_number=car.car_number if car else None,
        driver_name=car.driver.display_name if car else None,
    )


def race_result_response(session, result: RaceResult) -> RaceResultResponse:
    sim = session.simulation
    winner = next(car for car in sim.field if car.car_id == result.winner_car_id)
    user = sim.user_car
    return RaceResultResponse(
        session_id=session.session_id,
        seed=result.seed,
        track_id=sim.config.track.track_id,
        track_name=sim.config.track.name,
        track_type=sim.config.track.track_type,
        track_length_miles=float(sim.config.track.length_miles.value),
        control_mode=session.control_mode,
        current_controller=session.current_controller,
        delegation_status=session.delegation_status,
        objective=session.objective,
        winner_car_number=winner.car_number,
        winner_driver_name=winner.driver.display_name,
        user_car_number=user.car_number,
        user_driver_name=user.driver.display_name,
        user_start_position=result.user_start_position,
        user_finish_position=result.user_finish_position,
        positions_changed=result.user_start_position - result.user_finish_position,
        user_best_position=min((snapshot.user_position for snapshot in sim.snapshots), default=user.position),
        stage_points=None,
        pit_stops=len(user.pit_stops),
        lead_laps=user.laps_led,
        cautions_survived=result.caution_count,
        strategy_decisions=tuple(session.decision_history),
        stage_results=stage_result_responses(session),
        caution_count=result.caution_count,
        lead_changes=result.lead_changes,
        dnf_count=result.dnf_count,
        final_order=full_field_response(session),
    )
