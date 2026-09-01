from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

from src.simulation.decisions import available_strategy_options, validate_action
from src.simulation.models import (
    CarState,
    PitStop,
    Provenance,
    Quantity,
    RaceConfig,
    RaceEvent,
    RacePhase,
    RaceResult,
    SimulationSnapshot,
    StageResult,
    StrategyAction,
    StrategyDecision,
)
from src.simulation.strategy import choose_strategy_action


class RaceSimulation:
    def __init__(self, config: RaceConfig, field: list[CarState], user_car_id: str | None = None):
        self.config = config
        self.field = field
        self.user_car_id = user_car_id or field[len(field) // 2].car_id
        self.rng = random.Random(config.seed)
        self.lap = 0
        self.phase = RacePhase.PRE_RACE
        self.caution_remaining = 0
        self.pending_restart_laps = 0
        self.events: list[RaceEvent] = []
        self.snapshots: list[SimulationSnapshot] = []
        self.last_leader: str | None = None
        self.caution_count = 0
        self.lead_changes = 0
        self.strategy_split_count = 0
        self.recent_pit_laps: list[int] = []
        self.pending_decision: StrategyDecision | None = None
        self.last_human_decision_lap = -999
        self.stage_break_laps = set(config.stage_ends)
        self.stage_results: list[StageResult] = []

    @property
    def user_car(self) -> CarState:
        return next(c for c in self.field if c.car_id == self.user_car_id)

    def start(self) -> None:
        if self.phase != RacePhase.PRE_RACE:
            return
        self.phase = RacePhase.GREEN
        self.events.append(RaceEvent("RaceStarted", 0, f"{self.config.name} started with {len(self.field)} cars."))
        self._sort_order()

    def advance_to_next_decision(self) -> StrategyDecision | RaceResult:
        self.start()
        if self.pending_decision is not None:
            return self.pending_decision
        while self.phase != RacePhase.FINISHED:
            if self._human_decision_needed():
                decision = self._build_decision()
                self.pending_decision = decision
                self.events.append(RaceEvent("StrategyDecisionRequested", self.lap, decision.reason_for_decision, self.user_car_id))
                return decision
            self._advance_one_lap(None)
        return self.result()

    def commit_user_decision(self, action: StrategyAction, actor: str = "HUMAN") -> None:
        if self.pending_decision is None:
            raise ValueError("No pending user decision")
        options = available_strategy_options(self.user_car, self.config, self.phase, int(self.config.scheduled_laps.value) - self.lap)
        validate_action(action, options)
        self.events.append(RaceEvent("StrategyDecisionCommitted", self.lap, action.value, self.user_car_id, {"actor": actor}))
        self.last_human_decision_lap = self.lap
        self._advance_one_lap(action)
        self.pending_decision = None

    def run_to_finish(self, user_policy_auto: bool = True) -> RaceResult:
        self.start()
        while self.phase != RacePhase.FINISHED:
            if user_policy_auto:
                action = None
                if self._human_decision_needed():
                    action = choose_strategy_action(self.user_car, self.config, self.phase, self.lap, self._recent_pitters(3), self.rng)
                    self.events.append(RaceEvent("StrategyDecisionCommitted", self.lap, f"auto:{action.value}", self.user_car_id))
                    self.last_human_decision_lap = self.lap
                self._advance_one_lap(action)
            else:
                decision_or_result = self.advance_to_next_decision()
                if isinstance(decision_or_result, RaceResult):
                    return decision_or_result
                raise RuntimeError("Simulation paused for user decision")
        return self.result()

    def _advance_one_lap(self, user_action: StrategyAction | None) -> None:
        if self.lap in self.stage_break_laps and self.phase == RacePhase.GREEN:
            stage_result = self._record_stage_result()
            self.phase = RacePhase.STAGE_BREAK
            self.caution_remaining = int(self.config.caution_laps.value)
            self.events.append(
                RaceEvent(
                    "StageEnded",
                    self.lap,
                    (
                        f"Stage {stage_result.stage_number} complete. Winner {stage_result.winner_car_id}. "
                        f"You finished P{stage_result.user_position}."
                    ),
                    stage_result.winner_car_id,
                    {
                        "stage_number": stage_result.stage_number,
                        "user_position": stage_result.user_position,
                    },
                )
            )
            self._bunch_field()

        self._apply_strategy(user_action)
        if self.phase == RacePhase.GREEN:
            self._run_green_lap()
            if self.lap > 3 and self.rng.random() < float(self.config.caution_probability_per_green_lap.value):
                self._start_caution("Simulated incident caution")
        else:
            self._run_caution_lap()

        self.lap += 1
        for car in self.field:
            if car.active:
                car.laps_completed = min(self.lap, int(self.config.scheduled_laps.value))
        self._sort_order()
        self._record_leader()
        self._record_snapshot()
        self.events.append(RaceEvent("LapCompleted", self.lap, f"Lap {self.lap} completed.", data={"leader": self.field[0].car_id}))

        if self.lap >= int(self.config.scheduled_laps.value):
            self.phase = RacePhase.FINISHED
            self.events.append(RaceEvent("RaceFinished", self.lap, f"Race finished. Winner {self.field[0].car_id}."))

    def _apply_strategy(self, user_action: StrategyAction | None) -> None:
        committed: dict[StrategyAction, int] = {}
        recent_pitters = self._recent_pitters(3)
        for car in list(self.field):
            if not car.active:
                continue
            if car.car_id == self.user_car_id:
                action = user_action or StrategyAction.NORMAL_PACE
            else:
                action = choose_strategy_action(car, self.config, self.phase, self.lap, recent_pitters, self.rng)
                if action != StrategyAction.NORMAL_PACE:
                    self.events.append(RaceEvent("CompetitorStrategyCommitted", self.lap, action.value, car.car_id))
            car.current_action = action
            car.fuel.fuel_save_mode = action == StrategyAction.SAVE_FUEL
            if action == StrategyAction.SHORT_PIT:
                action = StrategyAction.PIT_4_TIRES
            if action in {StrategyAction.PIT_4_TIRES, StrategyAction.PIT_2_TIRES, StrategyAction.PIT_FUEL_ONLY}:
                self._pit(car, action)
            committed[action] = committed.get(action, 0) + 1
        active_actions = [a for a, n in committed.items() if n > 0 and a != StrategyAction.NORMAL_PACE]
        if len(active_actions) >= 2:
            self.strategy_split_count += 1

    def _pit(self, car: CarState, action: StrategyAction) -> None:
        base_stationary = {
            StrategyAction.PIT_4_TIRES: 13.5,
            StrategyAction.PIT_2_TIRES: 9.4,
            StrategyAction.PIT_FUEL_ONLY: 6.8,
        }[action]
        pit_rating = float(car.team.pit_crew_rating.value)
        stationary = max(5.5, base_stationary - pit_rating * 0.55 + self.rng.gauss(0, 0.55))
        phase_discount = 0.58 if self.phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK} else 1.0
        total_loss = float(self.config.pit_road_loss_seconds.value) * phase_discount + stationary
        positions_lost = max(1, round(total_loss / 1.25)) if self.phase == RacePhase.GREEN else max(0, round(total_loss / 5.0))
        car.total_time_seconds += total_loss
        car.fuel.remaining_laps = car.fuel.capacity_laps
        if action == StrategyAction.PIT_4_TIRES:
            car.tire.age_laps = 0
            car.tire.last_service = action
            car.tire.grip = Quantity(1.0, Provenance.MODELED, "grip")
        elif action == StrategyAction.PIT_2_TIRES:
            car.tire.age_laps = max(0, car.tire.age_laps // 2)
            car.tire.last_service = action
            car.tire.grip = Quantity(0.72, Provenance.MODELED, "grip")
        pit_stop = PitStop(car.car_id, self.lap, action, stationary, total_loss, positions_lost)
        car.pit_stops.append(pit_stop)
        self.recent_pit_laps.append(self.lap)
        self.events.append(RaceEvent("PitStopCompleted", self.lap, action.value, car.car_id, {"loss_seconds": round(total_loss, 3), "stationary_seconds": round(stationary, 3)}))

    def _run_green_lap(self) -> None:
        for car in self.field:
            if not car.active:
                continue
            fuel_burn = 0.86 if car.fuel.fuel_save_mode else car.fuel.burn_per_lap
            car.fuel.remaining_laps = max(0.0, car.fuel.remaining_laps - fuel_burn)
            car.tire.age_laps += 1
            lap_time = self._lap_time(car)
            if car.fuel.remaining_laps <= 0.0:
                lap_time += 4.0
            car.total_time_seconds += lap_time
            car.recent_lap_times.append(lap_time)
            car.recent_lap_times = car.recent_lap_times[-8:]
            self._maybe_retire(car)

    def _run_caution_lap(self) -> None:
        for car in self.field:
            if not car.active:
                continue
            car.fuel.remaining_laps = max(0.0, car.fuel.remaining_laps - 0.42)
            car.tire.age_laps += 1
            car.total_time_seconds += float(self.config.track.base_lap_time_seconds.value) * 1.75
        self.caution_remaining -= 1
        if self.caution_remaining <= 0:
            old_phase = self.phase
            self.phase = RacePhase.GREEN
            self.pending_restart_laps = int(self.config.restart_shuffle_laps.value)
            self.events.append(RaceEvent("CautionEnded", self.lap, f"{old_phase.value} ended; restart next lap."))
            self.events.append(RaceEvent("RestartOccurred", self.lap, "Field restarted from bunched order."))

    def _lap_time(self, car: CarState) -> float:
        base = float(self.config.track.base_lap_time_seconds.value)
        strength = car.strength_score
        tire_age = car.tire.age_laps
        tire_life = float(self.config.baseline_tire_life_laps.value)
        tire_management = float(car.driver.tire_management_rating.value)
        tire_penalty = max(0.0, (tire_age / tire_life) ** 1.42) * (0.82 - tire_management * 0.045)
        fuel_effect = -0.18 * (1 - car.fuel.remaining_laps / max(car.fuel.capacity_laps, 1))
        traffic = (car.position - 1) / max(1, len(self.field) - 1)
        traffic_penalty = traffic * float(self.config.track.track_position_sensitivity.value) * (0.38 - float(car.driver.traffic_rating.value) * 0.025)
        save_penalty = 0.34 if car.fuel.fuel_save_mode else 0.0
        restart_noise = self.rng.gauss(0, 0.12) if self.pending_restart_laps > 0 else 0.0
        noise = self.rng.gauss(0, max(0.035, 0.13 - float(car.driver.consistency_rating.value) * 0.018))
        return max(20.0, base - strength * 0.32 + tire_penalty + fuel_effect + traffic_penalty + save_penalty + restart_noise + noise)

    def _maybe_retire(self, car: CarState) -> None:
        risk = 0.00010
        risk -= float(car.driver.reliability_rating.value) * 0.000018
        risk -= float(car.team.reliability_rating.value) * 0.000014
        if car.fuel.remaining_laps <= 0.0:
            risk += 0.0015
        if self.rng.random() < max(0.000015, risk):
            car.active = False
            car.retired_reason = "mechanical"
            car.total_time_seconds += 9999
            self.events.append(RaceEvent("DriverRetired", self.lap, "Mechanical retirement.", car.car_id))

    def _start_caution(self, message: str) -> None:
        self.phase = RacePhase.CAUTION
        self.caution_remaining = int(self.config.caution_laps.value)
        self.caution_count += 1
        self._bunch_field()
        self.events.append(RaceEvent("CautionStarted", self.lap, message))

    def _bunch_field(self) -> None:
        self._sort_order()
        leader_time = self.field[0].total_time_seconds
        for idx, car in enumerate(self.field):
            if car.active:
                car.total_time_seconds = leader_time + idx * 0.45

    def _sort_order(self) -> None:
        self.field.sort(key=lambda c: (not c.active, c.total_time_seconds, c.car_id))
        for idx, car in enumerate(self.field, start=1):
            old = car.position
            car.position = idx
            if old != idx and self.lap > 0:
                self.events.append(RaceEvent("PositionChanged", self.lap, f"P{old} to P{idx}", car.car_id))

    def _record_leader(self) -> None:
        leader = self.field[0]
        leader.laps_led += 1
        if self.last_leader is not None and self.last_leader != leader.car_id:
            self.lead_changes += 1
            self.events.append(RaceEvent("LeadChanged", self.lap, f"Leader changed to {leader.car_id}.", leader.car_id))
        self.last_leader = leader.car_id

    def _record_snapshot(self) -> None:
        self.snapshots.append(
            SimulationSnapshot(
                lap=self.lap,
                phase=self.phase,
                leader_car_id=self.field[0].car_id,
                running_order=tuple(c.car_id for c in self.field),
                user_position=self.user_car.position,
                user_fuel_remaining_laps=round(self.user_car.fuel.remaining_laps, 2),
                user_tire_age_laps=self.user_car.tire.age_laps,
            )
        )

    def _record_stage_result(self) -> StageResult:
        existing = next((result for result in self.stage_results if result.completion_lap == self.lap), None)
        if existing is not None:
            return existing
        self._sort_order()
        stage_number = self.config.stage_ends.index(self.lap) + 1
        result = StageResult(
            stage_number=stage_number,
            completion_lap=self.lap,
            winner_car_id=self.field[0].car_id,
            user_position=self.user_car.position,
            top_10=tuple(car.car_id for car in self.field[:10]),
        )
        self.stage_results.append(result)
        return result

    def _recent_pitters(self, laps: int) -> int:
        return sum(1 for pit_lap in self.recent_pit_laps if self.lap - laps <= pit_lap <= self.lap)

    def _human_decision_needed(self) -> bool:
        if self.phase == RacePhase.FINISHED or self.pending_decision is not None:
            return False
        if self.lap - self.last_human_decision_lap < 8:
            return False
        car = self.user_car
        laps_remaining = int(self.config.scheduled_laps.value) - self.lap
        next_stage = min([s for s in self.config.stage_ends if s > self.lap], default=None)
        stage_soon = next_stage is not None and next_stage - self.lap <= 8
        in_fuel_window = car.fuel.remaining_laps <= 11
        tire_delta = car.tire.age_laps >= int(self.config.baseline_tire_life_laps.value) * 0.70
        strategy_split = self._recent_pitters(3) >= 5
        late_caution = self.phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK} and laps_remaining <= 45
        return self.phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK} or in_fuel_window or tire_delta or strategy_split or stage_soon or late_caution

    def _build_decision(self) -> StrategyDecision:
        car = self.user_car
        laps_remaining = int(self.config.scheduled_laps.value) - self.lap
        recent_pitters = self._recent_pitters(3)
        lead_lap_old_tires = sum(1 for c in self.field[: len(self.field)] if c.tire.age_laps >= car.tire.age_laps + 8)
        next_stage = min([s for s in self.config.stage_ends if s > self.lap], default=None)
        stage_text = "no stage remaining" if next_stage is None else f"stage ends in {next_stage - self.lap} laps"
        fuel_window = max(0, round(car.fuel.remaining_laps - 6))
        summary = (
            f"{recent_pitters} cars have pitted in the last 3 laps; "
            f"{lead_lap_old_tires} cars remain on older tires; {stage_text}; "
            f"fuel window opens in approximately {fuel_window} laps."
        )
        if self.phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK}:
            reason = f"{self.phase.value} creates a pit/track-position decision."
        elif recent_pitters >= 5:
            reason = "Competitors have started a strategy split."
        elif car.fuel.remaining_laps <= 11:
            reason = "User car is approaching the modeled fuel window."
        elif car.tire.age_laps >= int(self.config.baseline_tire_life_laps.value) * 0.70:
            reason = "User car tires have reached the modeled wear threshold."
        else:
            reason = "Upcoming stage or late-race context creates a strategy choice."
        recent = sum(car.recent_lap_times[-3:]) / len(car.recent_lap_times[-3:]) if car.recent_lap_times else None
        return StrategyDecision(
            lap=self.lap,
            car_id=car.car_id,
            position=car.position,
            race_phase=self.phase,
            fuel_remaining_laps=round(car.fuel.remaining_laps, 2),
            tire_age_laps=car.tire.age_laps,
            recent_pace_seconds=round(recent, 3) if recent is not None else None,
            field_strategy_summary=summary,
            available_actions=available_strategy_options(car, self.config, self.phase, laps_remaining),
            reason_for_decision=reason,
        )

    def result(self) -> RaceResult:
        self._sort_order()
        user = self.user_car
        return RaceResult(
            seed=self.config.seed,
            scheduled_laps=int(self.config.scheduled_laps.value),
            field_size=len(self.field),
            winner_car_id=self.field[0].car_id,
            final_order=tuple(c.car_id for c in self.field),
            caution_count=self.caution_count,
            lead_changes=self.lead_changes,
            pit_stop_count=sum(len(c.pit_stops) for c in self.field),
            strategy_split_count=self.strategy_split_count,
            dnf_count=sum(1 for c in self.field if not c.active),
            user_car_id=user.car_id,
            user_start_position=user.start_position,
            user_finish_position=user.position,
            stage_results=tuple(self.stage_results),
            event_count=len(self.events),
        )

    def write_artifact(self, path: Path) -> None:
        result = self.result()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "result": asdict(result),
            "field": [
                {
                    "car_id": c.car_id,
                    "car_number": c.car_number,
                    "driver": c.driver.display_name,
                    "team": c.team.display_name,
                    "manufacturer": c.team.manufacturer,
                    "policy": c.policy.archetype.value,
                    "start_position": c.start_position,
                    "finish_position": c.position,
                    "pit_stops": [asdict(p) for p in c.pit_stops],
                    "strength_score": round(c.strength_score, 4),
                }
                for c in self.field
            ],
            "events": [asdict(e) for e in self.events],
            "stage_results": [asdict(stage) for stage in self.stage_results],
            "snapshots": [asdict(s) for s in self.snapshots[:: max(1, len(self.snapshots) // 50)]],
        }
        path.write_text(json.dumps(payload, indent=2, default=lambda value: value.value if hasattr(value, "value") else str(value)))
