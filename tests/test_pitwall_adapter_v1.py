from src.pitwall import PitWallAdapter, RaceFinishedResponse


def test_pitwall_create_and_state_contract():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, track_id="trk_bristol_motor_speedway")
    state = adapter.get_race_state(session.session_id)
    car = adapter.get_my_car_state(session.session_id)

    assert state.session_id == session.session_id
    assert state.track_id == "trk_bristol_motor_speedway"
    assert state.track_name == "Bristol Motor Speedway"
    assert state.track_type == "Short Track"
    assert state.track_length_miles == 0.533
    assert state.race_laps == 500
    assert state.total_laps == 500
    assert state.cars_active == 36
    assert state.control_mode == "HUMAN"
    assert state.current_controller == "HUMAN"
    assert state.delegation_status == "NOT_DELEGATED"
    assert state.objective == "MAXIMIZE_FINISH_POSITION"
    assert car.car_number
    assert car.estimated_fuel_laps > 0
    assert car.provenance["fuel"] == "MODELED"


def test_advance_commit_and_decision_history():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847)
    decision = adapter.advance_to_next_decision(session.session_id)

    assert not isinstance(decision, RaceFinishedResponse)
    assert decision.decision_id
    action = next(option.action for option in decision.available_actions if option.eligible)
    result = adapter.commit_strategy(session.session_id, action)

    assert result.accepted
    assert result.decision is not None
    assert result.decision.decision_id == decision.decision_id
    assert result.decision.actor == "HUMAN"
    assert session.decision_history[0].action == action


def test_commit_rejects_stale_decision_id_and_invalid_action():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847)
    decision = adapter.advance_to_next_decision(session.session_id)

    stale = adapter.commit_strategy(session.session_id, "STAY_OUT", decision_id=f"{decision.decision_id}-old")
    invalid = adapter.commit_strategy(session.session_id, "MAKE_IT_FAST", decision_id=decision.decision_id)

    assert not stale.accepted
    assert "Stale decision ID" in stale.message
    assert not invalid.accepted
    assert "Unknown strategy action" in invalid.message
    assert not session.decision_history


def test_webmcp_actor_is_recorded_in_history_and_events():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF", track_id="trk_watkins_glen_international")
    decision = adapter.advance_to_next_decision(session.session_id)
    action = next(option.action for option in decision.available_actions if option.eligible)

    result = adapter.commit_strategy(session.session_id, action, decision_id=decision.decision_id, actor="WEBMCP_AGENT")
    events = adapter.get_recent_events(session.session_id, since_cursor=0, limit=200)

    assert result.accepted
    assert result.decision.actor == "WEBMCP_AGENT"
    assert any(event.event_type == "StrategyDecisionCommitted" and event.actor == "WEBMCP_AGENT" for event in events)


def test_co_crew_webmcp_commit_is_atomic_and_returns_progression_to_human():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF")
    decision = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
    action = next(option.action for option in decision.available_actions if option.eligible)

    result = adapter.commit_strategy(session.session_id, action, decision_id=decision.decision_id, actor="WEBMCP_AGENT")

    assert result.accepted
    assert result.decision.actor == "WEBMCP_AGENT"
    assert adapter.get_current_decision(session.session_id) is None
    state = adapter.get_race_state(session.session_id)
    assert state.session_id == session.session_id
    assert state.control_mode == "CO_CREW_CHIEF"
    assert state.current_controller == "SHARED"
    assert state.delegation_status == "SHARED"

    next_decision = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
    assert not isinstance(next_decision, RaceFinishedResponse)
    assert next_decision.session_id == session.session_id


def test_advance_returns_existing_pending_decision_without_progression():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF")
    decision = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
    lap = session.simulation.lap
    event_count = len(session.simulation.events)

    repeated = adapter.advance_to_next_decision(session.session_id, actor="WEBMCP_AGENT")

    assert not isinstance(repeated, RaceFinishedResponse)
    assert repeated.decision_id == decision.decision_id
    assert repeated.lap == decision.lap == lap
    assert session.simulation.lap == lap
    assert len(session.simulation.events) == event_count
    assert session.simulation.pending_decision is not None


def test_co_crew_daytona_one_advance_stops_at_next_decision_after_human_call():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF", track_id="trk_daytona_international_speedway")
    first = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
    committed = adapter.commit_strategy(session.session_id, "STAY_OUT", decision_id=first.decision_id, actor="HUMAN")
    lap_after_commit = session.simulation.lap

    next_decision = adapter.advance_to_next_decision(session.session_id, actor="WEBMCP_AGENT")

    assert committed.accepted
    assert not isinstance(next_decision, RaceFinishedResponse)
    assert next_decision.decision_id
    assert next_decision.lap == session.simulation.lap
    assert lap_after_commit < next_decision.lap < session.config.scheduled_laps.value
    assert session.simulation.pending_decision is not None
    assert session.simulation.phase.value != "FINISHED"
    assert len(session.decision_history) == 1


def test_co_crew_pocono_one_advance_stops_at_next_fuel_decision_after_human_call():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF", track_id="trk_pocono_raceway")
    first = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
    committed = adapter.commit_strategy(session.session_id, "STAY_OUT", decision_id=first.decision_id, actor="HUMAN")
    lap_after_commit = session.simulation.lap

    next_decision = adapter.advance_to_next_decision(session.session_id, actor="WEBMCP_AGENT")

    assert committed.accepted
    assert not isinstance(next_decision, RaceFinishedResponse)
    assert next_decision.decision_id
    assert next_decision.lap == session.simulation.lap
    assert lap_after_commit < next_decision.lap < session.config.scheduled_laps.value
    assert next_decision.fuel_remaining > 0
    assert "fuel" in next_decision.reason.lower()
    assert session.simulation.pending_decision is not None
    assert session.simulation.phase.value != "FINISHED"
    assert len(session.decision_history) == 1


def test_track_selection_persists_for_each_control_mode():
    adapter = PitWallAdapter()
    for control_mode in ("HUMAN", "CO_CREW_CHIEF", "AI_CREW_CHIEF"):
        session = adapter.create_race(seed=1900, control_mode=control_mode, track_id="trk_pocono_raceway")
        state = adapter.get_race_state(session.session_id)
        assert state.track_id == "trk_pocono_raceway"
        assert state.track_name == "Pocono Raceway"
        assert state.race_laps == 160
        assert state.control_mode == control_mode


def test_control_modes_gate_webmcp_and_human_mutations():
    adapter = PitWallAdapter()

    human_session = adapter.create_race(seed=1847)
    human_decision = adapter.advance_to_next_decision(human_session.session_id)
    action = next(option.action for option in human_decision.available_actions if option.eligible)
    human_reject = adapter.commit_strategy(
        human_session.session_id,
        action,
        decision_id=human_decision.decision_id,
        actor="WEBMCP_AGENT",
    )
    assert not human_reject.accepted
    assert human_reject.control["control_mode"] == "HUMAN"
    assert "WebMCP writes are disabled" in human_reject.message

    ai_session = adapter.create_race(seed=1848, control_mode="AI_CREW_CHIEF")
    pre_activation = adapter.get_race_state(ai_session.session_id)
    assert pre_activation.current_controller == "NONE"
    assert pre_activation.delegation_status == "AWAITING_AGENT"

    human_decision = adapter.advance_to_next_decision(ai_session.session_id, actor="HUMAN")
    assert not isinstance(human_decision, RaceFinishedResponse)
    waiting_state = adapter.get_race_state(ai_session.session_id)
    assert waiting_state.current_controller == "NONE"
    assert waiting_state.delegation_status == "AWAITING_AGENT"

    ai_action = next(option.action for option in human_decision.available_actions if option.eligible)
    activated = adapter.commit_strategy(
        ai_session.session_id,
        ai_action,
        decision_id=human_decision.decision_id,
        actor="WEBMCP_AGENT",
    )
    assert activated.accepted
    ai_state = adapter.get_race_state(ai_session.session_id)
    assert ai_state.current_controller == "WEBMCP_AGENT"
    assert ai_state.delegation_status == "ACTIVE"
    control_events = adapter.get_recent_events(ai_session.session_id, since_cursor=0, limit=200)
    assert any(event.event_type == "ControlTransferred" and event.actor == "WEBMCP_AGENT" for event in control_events)

    human_locked = adapter.advance_to_next_decision(ai_session.session_id, actor="HUMAN")
    assert not human_locked.accepted
    assert "AI Crew Chief currently owns" in human_locked.message

    paused = adapter.take_control(ai_session.session_id)
    assert paused.accepted
    assert paused.current_controller == "HUMAN"
    assert paused.delegation_status == "PAUSED"

    takeover_decision = adapter.advance_to_next_decision(ai_session.session_id, actor="HUMAN")
    assert not isinstance(takeover_decision, RaceFinishedResponse)

    returned = adapter.return_to_ai(ai_session.session_id)
    assert returned.accepted
    assert returned.current_controller == "HUMAN"
    assert returned.delegation_status == "AWAITING_AGENT"

    takeover_action = next(option.action for option in takeover_decision.available_actions if option.eligible)
    human_commit = adapter.commit_strategy(ai_session.session_id, takeover_action, decision_id=takeover_decision.decision_id)
    assert human_commit.accepted

    reactivated = adapter.advance_to_next_decision(ai_session.session_id, actor="WEBMCP_AGENT")
    assert not isinstance(reactivated, RaceFinishedResponse)
    reactivated_state = adapter.get_race_state(ai_session.session_id)
    assert reactivated_state.current_controller == "WEBMCP_AGENT"
    assert reactivated_state.delegation_status == "ACTIVE"

    relocked = adapter.advance_to_next_decision(ai_session.session_id, actor="HUMAN")
    assert not relocked.accepted


def test_field_hides_policy_until_debug_mode():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847)
    adapter.advance_to_next_decision(session.session_id)

    normal = adapter.get_field_state(session.session_id, debug=False)
    debug = adapter.get_field_state(session.session_id, debug=True)

    assert all(row.strategy_archetype is None for row in normal.running_order)
    assert any(row.strategy_archetype for row in debug.running_order)
    assert normal.field_strategy.autonomous_pit_walls == int(session.config.field_size.value) - 1
    assert normal.field_strategy.split_level in {"LOW", "MEDIUM", "HIGH"}
    assert normal.field_strategy.unrecorded_count >= 0


def test_field_strategy_uses_recorded_opponent_actions_after_call():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847)
    decision = adapter.advance_to_next_decision(session.session_id)
    action = next(option.action for option in decision.available_actions if option.eligible)

    adapter.commit_strategy(session.session_id, action)
    field = adapter.get_field_state(session.session_id)

    assert field.field_strategy.acted_count > 0
    assert sum(entry.count for entry in field.field_strategy.action_counts) == field.field_strategy.acted_count
    assert "recorded opponent strategy" in field.field_strategy.note


def test_auto_play_finishes_through_adapter():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1850)

    while True:
        next_stop = adapter.advance_to_next_decision(session.session_id)
        if isinstance(next_stop, RaceFinishedResponse):
            result = next_stop.result
            break
        commit = adapter.auto_commit_current_decision(session.session_id)
        assert commit.accepted

    fetched = adapter.get_race_result(session.session_id)
    assert fetched == result
    assert result.user_finish_position >= 1
    assert result.user_best_position >= 1
    assert len(result.stage_results) == len(session.config.stage_ends)
    assert result.stage_results[0].winner_car_number
    assert result.stage_results[0].top_10[0].position == 1
    assert result.strategy_decisions
    assert all(entry.actor == "AUTO_POLICY" for entry in result.strategy_decisions)


def test_race_state_exposes_completed_stage_results():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1847)

    while session.simulation.lap <= session.config.stage_ends[0]:
        next_stop = adapter.advance_to_next_decision(session.session_id)
        if isinstance(next_stop, RaceFinishedResponse):
            break
        adapter.auto_commit_current_decision(session.session_id)

    state = adapter.get_race_state(session.session_id)

    assert state.current_stage >= 2
    assert len(state.completed_stages) >= 1
    assert state.completed_stages[0].stage_number == 1
    assert state.completed_stages[0].completion_lap == session.config.stage_ends[0]
    assert state.completed_stages[0].winner_car_number
    assert 1 <= state.completed_stages[0].user_position <= int(session.config.field_size.value)


def test_repeated_advance_commit_progression_gets_multiple_decisions_and_finishes():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1850, track_id="trk_daytona_international_speedway")
    decision_laps = []

    while True:
        next_stop = adapter.advance_to_next_decision(session.session_id)
        if isinstance(next_stop, RaceFinishedResponse):
            result = next_stop.result
            break
        decision_laps.append(next_stop.lap)
        commit = adapter.auto_commit_current_decision(session.session_id)
        assert commit.accepted

    assert len(decision_laps) > 1
    assert decision_laps == sorted(decision_laps)
    assert result.strategy_decisions
    assert result.user_finish_position >= 1


def test_commit_rejects_finished_race():
    adapter = PitWallAdapter()
    session = adapter.create_race(seed=1849)
    while True:
        next_stop = adapter.advance_to_next_decision(session.session_id)
        if isinstance(next_stop, RaceFinishedResponse):
            break
        adapter.auto_commit_current_decision(session.session_id)

    result = adapter.commit_strategy(session.session_id, "NORMAL_PACE")

    assert not result.accepted
    assert "finished" in result.message


def test_same_seed_auto_replay_is_deterministic_apart_from_session_id():
    def run(seed: int):
        adapter = PitWallAdapter()
        session = adapter.create_race(seed=seed)
        while True:
            next_stop = adapter.advance_to_next_decision(session.session_id)
            if isinstance(next_stop, RaceFinishedResponse):
                return next_stop.result
            adapter.auto_commit_current_decision(session.session_id)

    one = run(1880)
    two = run(1880)

    assert one.winner_car_number == two.winner_car_number
    assert one.user_finish_position == two.user_finish_position
    assert one.caution_count == two.caution_count
    assert [d.action for d in one.strategy_decisions] == [d.action for d in two.strategy_decisions]


def test_same_seed_decision_boundaries_are_deterministic():
    def boundaries(track_id: str):
        adapter = PitWallAdapter()
        session = adapter.create_race(seed=1847, control_mode="CO_CREW_CHIEF", track_id=track_id)
        observed = []
        while True:
            next_stop = adapter.advance_to_next_decision(session.session_id, actor="HUMAN")
            if isinstance(next_stop, RaceFinishedResponse):
                return tuple(observed)
            observed.append((next_stop.lap, next_stop.reason, next_stop.fuel_remaining, next_stop.tire_age))
            commit = adapter.commit_strategy(session.session_id, "STAY_OUT", decision_id=next_stop.decision_id, actor="HUMAN")
            assert commit.accepted

    assert boundaries("trk_daytona_international_speedway") == boundaries("trk_daytona_international_speedway")
    assert boundaries("trk_pocono_raceway") == boundaries("trk_pocono_raceway")
