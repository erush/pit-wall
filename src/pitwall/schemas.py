from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AvailableActionResponse:
    action: str
    label: str
    short_description: str
    eligible: bool
    reason: str


@dataclass(frozen=True)
class RecentRunAnalysisResponse:
    last_5_lap_relative_pace: float | None
    last_10_lap_relative_pace: float | None
    positions_gained_recently: int
    positions_lost_recently: int
    simulated_tire_falloff_signal: str


@dataclass(frozen=True)
class StageRunningOrderEntryResponse:
    position: int
    car_number: str
    driver_name: str


@dataclass(frozen=True)
class StageResultResponse:
    stage_number: int
    completion_lap: int
    winner_car_number: str
    winner_driver_name: str
    user_position: int
    top_10: tuple[StageRunningOrderEntryResponse, ...]


@dataclass(frozen=True)
class TireContextResponse:
    user_tire_age: int
    field_median_tire_age: float
    user_tire_age_delta_to_median: float
    relative_classification: str
    approximate_percentile: int
    recent_relative_pace_seconds: float | None


@dataclass(frozen=True)
class FuelContextResponse:
    fuel_laps_remaining: float
    laps_to_next_boundary: int
    fuel_margin_to_boundary: float
    can_reach_next_boundary: bool
    next_boundary_type: str
    next_boundary_lap: int


@dataclass(frozen=True)
class FieldStrategyContextResponse:
    stay_out_count: int
    four_tire_count: int
    two_tire_count: int
    fuel_only_count: int
    extend_stint_count: int
    save_fuel_count: int
    not_yet_recorded_count: int
    strategy_split_classification: str
    recent_window_laps: int
    leading_recorded_action: str | None


@dataclass(frozen=True)
class PositionContextResponse:
    current_position: int
    starting_position: int
    net_positions_gained: int
    net_positions_lost: int
    recent_position_trend: str
    track_position_classification: str


@dataclass(frozen=True)
class StageContextResponse:
    current_stage: int
    laps_remaining_in_current_stage: int | None
    laps_to_next_boundary: int
    next_boundary_type: str
    completed_stage_results: tuple[StageResultResponse, ...]
    latest_completed_stage: StageResultResponse | None
    user_latest_stage_position: int | None
    latest_stage_winner: str | None


@dataclass(frozen=True)
class RecentStrategyConsequenceResponse:
    lap: int
    actor: str
    action: str
    position_before: int
    position_after_commit: int
    current_position: int
    immediate_position_delta: int
    current_net_position_delta: int


@dataclass(frozen=True)
class RaceIntelligenceContextResponse:
    tire_context: TireContextResponse
    fuel_context: FuelContextResponse
    field_strategy_context: FieldStrategyContextResponse
    position_context: PositionContextResponse
    stage_context: StageContextResponse
    recent_strategy_consequence: RecentStrategyConsequenceResponse | None
    strategic_factors: tuple[str, ...]


@dataclass(frozen=True)
class RaceStateResponse:
    session_id: str
    track_id: str
    track_name: str
    track_type: str
    track_length_miles: float
    race_laps: int
    lap: int
    total_laps: int
    stage: int
    race_status: str
    caution_status: str
    leader: str
    user_position: int
    cars_active: int
    laps_remaining: int
    control_mode: str
    current_controller: str
    delegation_status: str
    objective: str
    current_stage: int
    completed_stages: tuple[StageResultResponse, ...] = field(default_factory=tuple)
    race_intelligence: RaceIntelligenceContextResponse | None = None


@dataclass(frozen=True)
class CarStateResponse:
    car_number: str
    driver_name: str
    team_name: str
    position: int
    starting_position: int
    fuel_remaining: float
    estimated_fuel_laps: float
    tire_age: int
    pace_mode: str
    recent_pace: float | None
    gap_to_leader: float
    pit_stops: int
    provenance: dict[str, str]
    recent_run: RecentRunAnalysisResponse


@dataclass(frozen=True)
class FieldCarResponse:
    position: int
    car_number: str
    driver_name: str
    team_name: str
    laps_down: int
    tire_age: int
    estimated_fuel_laps: float
    last_pit_lap: int | None
    gap_to_leader: float
    strategy_archetype: str | None = None


@dataclass(frozen=True)
class StrategyActionCountResponse:
    action: str
    label: str
    count: int


@dataclass(frozen=True)
class FieldStrategyResponse:
    lap: int
    window_laps: int
    autonomous_pit_walls: int
    acted_count: int
    unrecorded_count: int
    split_level: str
    split_rule: str
    action_counts: tuple[StrategyActionCountResponse, ...]
    note: str


@dataclass(frozen=True)
class FieldStateResponse:
    session_id: str
    lap: int
    running_order: tuple[FieldCarResponse, ...]
    field_strategy_summary: tuple[str, ...]
    field_strategy: FieldStrategyResponse


@dataclass(frozen=True)
class DecisionResponse:
    session_id: str
    decision_id: str
    lap: int
    position: int
    reason: str
    race_context: str
    fuel_remaining: float
    estimated_fuel_laps: float
    tire_age: int
    laps_to_stage_end: int | None
    laps_to_race_end: int
    recent_pace: float | None
    recent_run: RecentRunAnalysisResponse
    field_strategy_summary: tuple[str, ...]
    available_actions: tuple[AvailableActionResponse, ...]


@dataclass(frozen=True)
class DecisionHistoryEntry:
    decision_id: str
    lap: int
    action: str
    label: str
    reason: str
    actor: str
    position_before: int
    position_after_commit: int
    tire_age_before: int
    fuel_laps_before: float


@dataclass(frozen=True)
class EventResponse:
    cursor: int
    event_type: str
    lap: int
    message: str
    actor: str | None = None
    car_number: str | None = None
    driver_name: str | None = None


@dataclass(frozen=True)
class ActionResult:
    accepted: bool
    message: str
    decision: DecisionHistoryEntry | None = None
    control: dict[str, str] | None = None


@dataclass(frozen=True)
class ControlActionResult:
    accepted: bool
    message: str
    control_mode: str
    current_controller: str
    delegation_status: str
    objective: str


@dataclass(frozen=True)
class RaceResultResponse:
    session_id: str
    seed: int
    track_id: str
    track_name: str
    track_type: str
    track_length_miles: float
    control_mode: str
    current_controller: str
    delegation_status: str
    objective: str
    winner_car_number: str
    winner_driver_name: str
    user_car_number: str
    user_driver_name: str
    user_start_position: int
    user_finish_position: int
    positions_changed: int
    user_best_position: int | None
    stage_points: int | None
    pit_stops: int
    lead_laps: int
    cautions_survived: int
    strategy_decisions: tuple[DecisionHistoryEntry, ...]
    stage_results: tuple[StageResultResponse, ...]
    caution_count: int
    lead_changes: int
    dnf_count: int
    final_order: tuple[FieldCarResponse, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RaceFinishedResponse:
    session_id: str
    status: str
    result: RaceResultResponse
