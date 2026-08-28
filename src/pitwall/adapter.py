from __future__ import annotations

from dataclasses import dataclass, field

from src.pitwall.presenters import (
    car_state_response,
    decision_response,
    event_response,
    field_state_response,
    race_result_response,
    race_state_response,
)
from src.pitwall.schemas import (
    ActionResult,
    CarStateResponse,
    ControlActionResult,
    DecisionHistoryEntry,
    DecisionResponse,
    EventResponse,
    FieldStateResponse,
    RaceFinishedResponse,
    RaceResultResponse,
    RaceStateResponse,
)
from src.simulation.config import DEFAULT_TRACK_ID, default_race_config
from src.simulation.engine import RaceSimulation
from src.simulation.field import generate_fictional_field
from src.simulation.models import RaceConfig, RaceEvent, RaceResult, StrategyAction, StrategyDecision


CONTROL_HUMAN = "HUMAN"
CONTROL_CO_CREW_CHIEF = "CO_CREW_CHIEF"
CONTROL_AI_CREW_CHIEF = "AI_CREW_CHIEF"
CONTROLLER_HUMAN = "HUMAN"
CONTROLLER_SHARED = "SHARED"
CONTROLLER_WEBMCP = "WEBMCP_AGENT"
CONTROLLER_NONE = "NONE"
DELEGATION_NOT_DELEGATED = "NOT_DELEGATED"
DELEGATION_SHARED = "SHARED"
DELEGATION_AWAITING_AGENT = "AWAITING_AGENT"
DELEGATION_ACTIVE = "ACTIVE"
DELEGATION_PAUSED = "PAUSED"
OBJECTIVE_MAX_FINISH = "MAXIMIZE_FINISH_POSITION"
VALID_CONTROL_MODES = {CONTROL_HUMAN, CONTROL_CO_CREW_CHIEF, CONTROL_AI_CREW_CHIEF}
MUTATING_ACTORS = {CONTROLLER_HUMAN, CONTROLLER_WEBMCP, "AUTO_POLICY"}

MEANINGFUL_EVENT_TYPES = {
    "CautionStarted",
    "CautionEnded",
    "RestartOccurred",
    "StageEnded",
    "PitStopCompleted",
    "CompetitorStrategyCommitted",
    "StrategyDecisionRequested",
    "StrategyDecisionCommitted",
    "LeadChanged",
    "PositionChanged",
    "DriverRetired",
    "RaceStarted",
    "RaceFinished",
    "ControlTransferred",
}
from src.simulation.strategy import choose_strategy_action


@dataclass
class RaceSession:
    session_id: str
    seed: int
    config: RaceConfig
    simulation: RaceSimulation
    human_car_id: str
    control_mode: str = CONTROL_HUMAN
    current_controller: str = CONTROLLER_HUMAN
    delegation_status: str = DELEGATION_NOT_DELEGATED
    objective: str = OBJECTIVE_MAX_FINISH
    decision_history: list[DecisionHistoryEntry] = field(default_factory=list)
    event_cursor: int = 0
    finished: bool = False
    current_decision_id: str = ""
    _decision_sequence: int = 0
    _last_result: RaceResult | None = None


class PitWallAdapter:
    """Application-facing race service for UI, CLI, and future WebMCP callers."""

    def __init__(self) -> None:
        self._sessions: dict[str, RaceSession] = {}
        self._session_sequence = 0

    def create_race(self, seed: int = 1847, control_mode: str = CONTROL_HUMAN, track_id: str = DEFAULT_TRACK_ID) -> RaceSession:
        self._session_sequence += 1
        control_mode = self._coerce_control_mode(control_mode)
        session_id = f"pitwall-{seed}-{self._session_sequence:04d}"
        config = default_race_config(seed=seed, track_id=track_id)
        field = generate_fictional_field(config)
        sim = RaceSimulation(config, field)
        current_controller, delegation_status = self._initial_control_state(control_mode)
        session = RaceSession(
            session_id=session_id,
            seed=seed,
            config=config,
            simulation=sim,
            human_car_id=sim.user_car_id,
            control_mode=control_mode,
            current_controller=current_controller,
            delegation_status=delegation_status,
        )
        self._sessions[session_id] = session
        return session

    def get_race_state(self, session_id: str) -> RaceStateResponse:
        return race_state_response(self._session(session_id))

    def get_my_car_state(self, session_id: str) -> CarStateResponse:
        return car_state_response(self._session(session_id))

    def get_field_state(self, session_id: str, window: int = 9, debug: bool = False) -> FieldStateResponse:
        return field_state_response(self._session(session_id), window=window, debug=debug)

    def get_current_decision(self, session_id: str) -> DecisionResponse | None:
        session = self._session(session_id)
        if session.simulation.pending_decision is None:
            return None
        return decision_response(session, session.simulation.pending_decision)

    def get_recent_events(self, session_id: str, since_cursor: int | None = None, limit: int = 25) -> tuple[EventResponse, ...]:
        session = self._session(session_id)
        start = session.event_cursor if since_cursor is None else since_cursor
        matched = []
        for cursor, event in enumerate(session.simulation.events[start:], start=start):
            if event.event_type not in MEANINGFUL_EVENT_TYPES:
                continue
            matched.append((cursor, event))
        events = matched[-limit:] if since_cursor == 0 else matched[:limit]
        last_cursor = start
        if matched:
            last_cursor = matched[-1][0] + 1 if since_cursor == 0 else events[-1][0] + 1
        if since_cursor is None:
            session.event_cursor = last_cursor
        return tuple(event_response(cursor, event, session) for cursor, event in events)

    def get_decision_history(self, session_id: str) -> tuple[DecisionHistoryEntry, ...]:
        return tuple(self._session(session_id).decision_history)

    def commit_strategy(
        self,
        session_id: str,
        action: str | StrategyAction,
        decision_id: str | None = None,
        actor: str = "HUMAN",
    ) -> ActionResult:
        session = self._session(session_id)
        ownership = self._mutation_denial(session, actor)
        if ownership is not None:
            return ActionResult(False, ownership, control=self._control_payload(session))
        if session.finished or session.simulation.phase.value == "FINISHED":
            return ActionResult(False, "Cannot commit strategy after the race is finished.", control=self._control_payload(session))
        if session.simulation.pending_decision is None:
            return ActionResult(False, "No pending strategy decision.", control=self._control_payload(session))
        if decision_id is not None and decision_id != session.current_decision_id:
            return ActionResult(
                False,
                f"Stale decision ID: {decision_id}. Current decision is {session.current_decision_id}.",
                control=self._control_payload(session),
            )
        try:
            strategy_action = self._coerce_action(action)
        except ValueError as exc:
            return ActionResult(False, str(exc), control=self._control_payload(session))
        decision = session.simulation.pending_decision
        try:
            session.simulation.commit_user_decision(strategy_action, actor=actor)
        except ValueError as exc:
            return ActionResult(False, str(exc), control=self._control_payload(session))
        self._mark_mutation(session, actor)
        history = DecisionHistoryEntry(
            decision_id=session.current_decision_id,
            lap=decision.lap,
            action=strategy_action.value,
            label=self._action_label(decision, strategy_action),
            reason=decision.reason_for_decision,
            actor=actor,
            position_before=decision.position,
            position_after_commit=session.simulation.user_car.position,
            tire_age_before=decision.tire_age_laps,
            fuel_laps_before=decision.fuel_remaining_laps,
        )
        session.decision_history.append(history)
        if session.simulation.phase.value == "FINISHED":
            session.finished = True
            session._last_result = session.simulation.result()
        return ActionResult(True, f"Committed {strategy_action.value}.", history, control=self._control_payload(session))

    def advance_to_next_decision(self, session_id: str, actor: str = "HUMAN") -> DecisionResponse | RaceFinishedResponse | ControlActionResult:
        session = self._session(session_id)
        ownership = self._mutation_denial(session, actor)
        if ownership is not None:
            return self._control_result(session, False, ownership)
        pending_before = session.simulation.pending_decision
        result_or_decision = session.simulation.advance_to_next_decision()
        self._mark_mutation(session, actor)
        if isinstance(result_or_decision, RaceResult):
            session.finished = True
            session._last_result = result_or_decision
            return RaceFinishedResponse(session.session_id, "FINISHED", race_result_response(session, result_or_decision))
        if pending_before is not result_or_decision or not session.current_decision_id:
            session.current_decision_id = self._next_decision_id(session, result_or_decision)
        return decision_response(session, result_or_decision)

    def handoff_to_ai(self, session_id: str) -> ControlActionResult:
        session = self._session(session_id)
        if session.control_mode != CONTROL_AI_CREW_CHIEF:
            return self._control_result(session, False, "AI handoff is available only in AI Crew Chief mode.")
        session.current_controller = CONTROLLER_HUMAN
        session.delegation_status = DELEGATION_AWAITING_AGENT
        self._record_control_event(session, "AI Crew Chief ready for handoff.", CONTROLLER_HUMAN)
        return self._control_result(session, True, "AI Crew Chief ready for handoff. Use Work with ChatGPT to activate the agent.")

    def take_control(self, session_id: str) -> ControlActionResult:
        session = self._session(session_id)
        if session.control_mode != CONTROL_AI_CREW_CHIEF:
            return self._control_result(session, False, "Take control is available only in AI Crew Chief mode.")
        session.current_controller = CONTROLLER_HUMAN
        session.delegation_status = DELEGATION_PAUSED
        self._record_control_event(session, "Human crew chief took the pit box.", CONTROLLER_HUMAN)
        return self._control_result(session, True, "Human control restored.")

    def return_to_ai(self, session_id: str) -> ControlActionResult:
        session = self._session(session_id)
        if session.control_mode != CONTROL_AI_CREW_CHIEF:
            return self._control_result(session, False, "Return to AI is available only in AI Crew Chief mode.")
        session.current_controller = CONTROLLER_HUMAN
        session.delegation_status = DELEGATION_AWAITING_AGENT
        self._record_control_event(session, "AI Crew Chief ready for handoff.", CONTROLLER_HUMAN)
        return self._control_result(session, True, "AI Crew Chief ready for handoff. Human controls remain available until ChatGPT acts.")

    def auto_commit_current_decision(self, session_id: str) -> ActionResult:
        session = self._session(session_id)
        if session.simulation.pending_decision is None:
            return ActionResult(False, "No pending strategy decision.")
        action = choose_strategy_action(
            session.simulation.user_car,
            session.config,
            session.simulation.phase,
            session.simulation.lap,
            self._recent_pitters(session, 3),
            session.simulation.rng,
        )
        return self.commit_strategy(session_id, action, actor="AUTO_POLICY")

    def get_race_result(self, session_id: str) -> RaceResultResponse | None:
        session = self._session(session_id)
        if not session.finished and session.simulation.phase.value != "FINISHED":
            return None
        if session._last_result is None:
            session._last_result = session.simulation.result()
        return race_result_response(session, session._last_result)

    def _session(self, session_id: str) -> RaceSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown race session: {session_id}") from exc

    def _coerce_control_mode(self, control_mode: str) -> str:
        normalized = str(control_mode or CONTROL_HUMAN).upper()
        if normalized not in VALID_CONTROL_MODES:
            raise ValueError(f"Unknown control mode: {control_mode}")
        return normalized

    def _initial_control_state(self, control_mode: str) -> tuple[str, str]:
        if control_mode == CONTROL_CO_CREW_CHIEF:
            return CONTROLLER_SHARED, DELEGATION_SHARED
        if control_mode == CONTROL_AI_CREW_CHIEF:
            return CONTROLLER_NONE, DELEGATION_AWAITING_AGENT
        return CONTROLLER_HUMAN, DELEGATION_NOT_DELEGATED

    def _mutation_denial(self, session: RaceSession, actor: str) -> str | None:
        actor = actor or CONTROLLER_HUMAN
        if actor not in MUTATING_ACTORS:
            return f"Unknown mutation actor: {actor}."
        if actor == "AUTO_POLICY":
            return None
        if session.control_mode == CONTROL_HUMAN and actor != CONTROLLER_HUMAN:
            return "This race is in Human mode. WebMCP writes are disabled; the agent may inspect state only."
        if session.control_mode == CONTROL_CO_CREW_CHIEF:
            return None
        if session.control_mode == CONTROL_AI_CREW_CHIEF:
            if actor == CONTROLLER_HUMAN:
                if session.current_controller == CONTROLLER_WEBMCP and session.delegation_status == DELEGATION_ACTIVE:
                    return "The AI Crew Chief currently owns the pit box. Take control before making human race calls."
                return None
            if actor == CONTROLLER_WEBMCP:
                if session.delegation_status == DELEGATION_AWAITING_AGENT:
                    return None
                if session.current_controller == CONTROLLER_WEBMCP and session.delegation_status == DELEGATION_ACTIVE:
                    return None
                return "Human control is active. Return the pit box to AI before WebMCP race calls."
        return None

    def _mark_mutation(self, session: RaceSession, actor: str) -> None:
        if session.control_mode == CONTROL_AI_CREW_CHIEF and actor == CONTROLLER_WEBMCP:
            was_active = session.current_controller == CONTROLLER_WEBMCP and session.delegation_status == DELEGATION_ACTIVE
            session.current_controller = CONTROLLER_WEBMCP
            session.delegation_status = DELEGATION_ACTIVE
            if not was_active:
                self._record_control_event(session, "AI Crew Chief assumed the pit box.", CONTROLLER_WEBMCP)

    def _control_payload(self, session: RaceSession) -> dict[str, str]:
        return {
            "control_mode": session.control_mode,
            "current_controller": session.current_controller,
            "delegation_status": session.delegation_status,
            "objective": session.objective,
        }

    def _control_result(self, session: RaceSession, accepted: bool, message: str) -> ControlActionResult:
        return ControlActionResult(accepted=accepted, message=message, **self._control_payload(session))

    def _record_control_event(self, session: RaceSession, message: str, actor: str) -> None:
        session.simulation.events.append(
            RaceEvent(
                lap=session.simulation.lap,
                event_type="ControlTransferred",
                message=message,
                car_id=session.human_car_id,
                data={
                    "actor": actor,
                    "control_mode": session.control_mode,
                    "current_controller": session.current_controller,
                    "delegation_status": session.delegation_status,
                },
            )
        )

    def _coerce_action(self, action: str | StrategyAction) -> StrategyAction:
        if isinstance(action, StrategyAction):
            return action
        try:
            return StrategyAction[action]
        except KeyError as exc:
            try:
                return StrategyAction(action)
            except ValueError as value_exc:
                raise ValueError(f"Unknown strategy action: {action}") from value_exc

    def _recent_pitters(self, session: RaceSession, laps: int) -> int:
        current_lap = session.simulation.lap
        return sum(
            1
            for event in session.simulation.events
            if event.event_type == "PitStopCompleted" and current_lap - laps <= event.lap <= current_lap
        )

    def _next_decision_id(self, session: RaceSession, decision: StrategyDecision) -> str:
        session._decision_sequence += 1
        return f"{session.session_id}-d{session._decision_sequence:03d}-lap{decision.lap}"

    def _action_label(self, decision: StrategyDecision, action: StrategyAction) -> str:
        for option in decision.available_actions:
            if option.action == action:
                return option.label
        return action.value
