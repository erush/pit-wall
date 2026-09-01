from src.simulation.config import TRACK_SIMULATION_PROFILES, default_race_config
from src.simulation.decisions import available_strategy_options, validate_action
from src.simulation.engine import RaceSimulation
from src.simulation.field import generate_fictional_field
from src.simulation.models import Provenance, RacePhase, RaceResult, StrategyAction, StrategyDecision


def build_sim(seed=1847):
    config = default_race_config(seed=seed)
    field = generate_fictional_field(config)
    return RaceSimulation(config, field)


def test_field_integrity_and_provenance():
    config = default_race_config(seed=1)
    field = generate_fictional_field(config)
    assert len(field) == int(config.field_size.value)
    assert len({c.car_number for c in field}) == int(config.field_size.value)
    assert len({c.driver.driver_id for c in field}) == int(config.field_size.value)
    assert {c.driver.baseline_pace_rating.provenance for c in field} == {Provenance.DERIVED}
    assert {c.team.pit_crew_rating.provenance for c in field} == {Provenance.MODELED}


def test_deterministic_replay():
    one = build_sim(1847).run_to_finish()
    two = build_sim(1847).run_to_finish()
    assert one == two


def test_different_seeds_can_change_outcome():
    one = build_sim(1847).run_to_finish()
    two = build_sim(1848).run_to_finish()
    assert (one.winner_car_id, one.caution_count, one.lead_changes) != (two.winner_car_id, two.caution_count, two.lead_changes)


def test_running_order_unique_and_race_finishes():
    sim = build_sim(20)
    result = sim.run_to_finish()
    assert isinstance(result, RaceResult)
    assert len(result.final_order) == len(set(result.final_order)) == int(sim.config.field_size.value)
    assert sim.phase == RacePhase.FINISHED
    assert [c.position for c in sim.field] == list(range(1, int(sim.config.field_size.value) + 1))


def test_all_five_track_profiles_load_and_create_different_configs():
    configs = [default_race_config(seed=1847, track_id=track_id) for track_id in TRACK_SIMULATION_PROFILES]
    assert len(configs) == 5
    assert {config.track.track_id for config in configs} == set(TRACK_SIMULATION_PROFILES)
    assert {int(config.scheduled_laps.value) for config in configs} == {90, 160, 200, 367, 500}
    assert len({float(config.track.track_position_sensitivity.value) for config in configs}) > 1
    assert all(config.track_profile is not None for config in configs)


def test_all_five_track_races_complete_and_replay_deterministically():
    for track_id in TRACK_SIMULATION_PROFILES:
        config = default_race_config(seed=91, track_id=track_id)
        first = RaceSimulation(config, generate_fictional_field(config)).run_to_finish()
        config = default_race_config(seed=91, track_id=track_id)
        second = RaceSimulation(config, generate_fictional_field(config)).run_to_finish()
        assert first == second
        assert first.scheduled_laps == int(TRACK_SIMULATION_PROFILES[track_id].race_laps.value)


def test_fuel_bounds_and_tire_age_behavior():
    sim = build_sim(30)
    result = sim.run_to_finish()
    assert result.pit_stop_count > 0
    assert all(c.fuel.remaining_laps >= 0 for c in sim.field)
    assert any(c.tire.age_laps < sim.lap for c in sim.field)


def test_pit_stop_state_transitions():
    sim = build_sim(40)
    car = sim.user_car
    car.tire.age_laps = 30
    car.fuel.remaining_laps = 2
    sim.start()
    sim._pit(car, StrategyAction.PIT_4_TIRES)
    assert car.tire.age_laps == 0
    assert car.fuel.remaining_laps == car.fuel.capacity_laps
    assert car.pit_stops[-1].provenance == Provenance.SIMULATED


def test_strategy_eligibility_invalid_action_fails():
    sim = build_sim(50)
    sim.start()
    car = sim.user_car
    car.tire.age_laps = 40
    options = available_strategy_options(car, sim.config, RacePhase.GREEN, 100)
    try:
        validate_action(StrategyAction.PIT_FUEL_ONLY, options)
    except ValueError as exc:
        assert "invalid" in str(exc).lower()
    else:
        raise AssertionError("fuel-only on heavily worn tires should fail")


def test_decision_point_detection_and_commit():
    sim = build_sim(60)
    decision = sim.advance_to_next_decision()
    assert isinstance(decision, StrategyDecision)
    assert decision.available_actions
    eligible = next(option.action for option in decision.available_actions if option.eligible)
    sim.commit_user_decision(eligible)
    assert any(e.event_type == "StrategyDecisionCommitted" for e in sim.events)


def test_caution_and_stage_events_exist():
    sim = build_sim(70)
    result = sim.run_to_finish()
    event_types = {e.event_type for e in sim.events}
    assert "StageEnded" in event_types
    assert len(result.stage_results) == len(sim.config.stage_ends)
    assert [stage.stage_number for stage in result.stage_results] == [1, 2]
    assert [stage.completion_lap for stage in result.stage_results] == list(sim.config.stage_ends)
    assert all(stage.winner_car_id == stage.top_10[0] for stage in result.stage_results)
    assert all(1 <= stage.user_position <= int(sim.config.field_size.value) for stage in result.stage_results)
    assert result.caution_count >= 0
    assert "RaceFinished" in event_types


def test_event_log_integrity():
    sim = build_sim(80)
    sim.run_to_finish()
    assert sim.events[0].event_type == "RaceStarted"
    assert sim.events[-1].event_type == "RaceFinished"
    assert all(e.provenance == Provenance.SIMULATED for e in sim.events)
