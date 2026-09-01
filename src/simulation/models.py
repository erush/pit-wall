from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Provenance(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    MODELED = "MODELED"
    SIMULATED = "SIMULATED"


@dataclass(frozen=True)
class Quantity:
    value: float | int | str | bool
    provenance: Provenance
    units: str | None = None
    source: str | None = None


class RacePhase(str, Enum):
    PRE_RACE = "PRE_RACE"
    GREEN = "GREEN"
    CAUTION = "CAUTION"
    STAGE_BREAK = "STAGE_BREAK"
    FINISHED = "FINISHED"


class StrategyAction(str, Enum):
    STAY_OUT = "STAY_OUT"
    PIT_4_TIRES = "PIT_4_TIRES"
    PIT_2_TIRES = "PIT_2_TIRES"
    PIT_FUEL_ONLY = "PIT_FUEL_ONLY"
    SHORT_PIT = "SHORT_PIT"
    EXTEND_STINT = "EXTEND_STINT"
    NORMAL_PACE = "NORMAL_PACE"
    SAVE_FUEL = "SAVE_FUEL"


class PolicyArchetype(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    AGGRESSIVE = "AGGRESSIVE"
    STAGE_OPTIMIZER = "STAGE_OPTIMIZER"
    LONG_RUN_OPTIMIZER = "LONG_RUN_OPTIMIZER"
    TRACK_POSITION_DEFENDER = "TRACK_POSITION_DEFENDER"


class RaceObjective(str, Enum):
    EXPECTED_FINISH = "EXPECTED_FINISH"
    WIN_PROBABILITY = "WIN_PROBABILITY"
    STAGE_POINTS = "STAGE_POINTS"
    MINIMIZE_DNF_RISK = "MINIMIZE_DNF_RISK"


@dataclass(frozen=True)
class TrackConfig:
    track_id: str
    name: str
    track_type: str
    length_miles: Quantity
    track_position_sensitivity: Quantity
    base_lap_time_seconds: Quantity


@dataclass(frozen=True)
class TrackSimulationProfile:
    track_id: str
    track_name: str
    track_type: str
    track_length_miles: Quantity
    race_laps: Quantity
    stage_1_end: Quantity
    stage_2_end: Quantity
    field_size: Quantity
    modeled_fuel_window_laps: Quantity
    modeled_tire_wear_factor: Quantity
    modeled_caution_rate: Quantity
    modeled_restart_volatility: Quantity
    modeled_traffic_effect: Quantity
    modeled_pit_road_loss: Quantity
    modeled_strategy_volatility: Quantity
    source_notes: tuple[str, ...]


@dataclass(frozen=True)
class RaceConfig:
    race_id: str
    name: str
    scheduled_laps: Quantity
    field_size: Quantity
    stage_ends: tuple[int, ...]
    nominal_fuel_window_laps: Quantity
    baseline_tire_life_laps: Quantity
    pit_road_loss_seconds: Quantity
    caution_probability_per_green_lap: Quantity
    caution_laps: Quantity
    restart_shuffle_laps: Quantity
    strategy_volatility: Quantity
    track: TrackConfig
    track_profile: TrackSimulationProfile | None = None
    seed: int = 1847


@dataclass(frozen=True)
class DriverPerformanceProfile:
    driver_id: str
    display_name: str
    baseline_pace_rating: Quantity
    qualifying_rating: Quantity
    long_run_rating: Quantity
    consistency_rating: Quantity
    track_fit_rating: Quantity
    tire_management_rating: Quantity
    traffic_rating: Quantity
    reliability_rating: Quantity


@dataclass(frozen=True)
class TeamPerformanceProfile:
    team_id: str
    display_name: str
    equipment_rating: Quantity
    pit_crew_rating: Quantity
    reliability_rating: Quantity
    manufacturer: str


@dataclass(frozen=True)
class CrewChiefPolicy:
    policy_id: str
    archetype: PolicyArchetype
    finish_weight: float
    win_weight: float
    stage_weight: float
    risk_aversion: float


@dataclass
class TireState:
    age_laps: int
    last_service: StrategyAction
    grip: Quantity


@dataclass
class FuelState:
    capacity_laps: float
    remaining_laps: float
    burn_per_lap: float
    fuel_save_mode: bool = False


@dataclass
class PitStop:
    car_id: str
    lap: int
    action: StrategyAction
    stationary_seconds: float
    total_loss_seconds: float
    positions_lost: int
    provenance: Provenance = Provenance.SIMULATED


@dataclass
class CarState:
    car_id: str
    car_number: str
    driver: DriverPerformanceProfile
    team: TeamPerformanceProfile
    policy: CrewChiefPolicy
    objective: RaceObjective
    position: int
    start_position: int
    laps_completed: int = 0
    total_time_seconds: float = 0.0
    tire: TireState = field(default_factory=lambda: TireState(0, StrategyAction.PIT_4_TIRES, Quantity(1.0, Provenance.MODELED)))
    fuel: FuelState = field(default_factory=lambda: FuelState(52.0, 52.0, 1.0))
    active: bool = True
    retired_reason: str | None = None
    pit_stops: list[PitStop] = field(default_factory=list)
    recent_lap_times: list[float] = field(default_factory=list)
    current_action: StrategyAction = StrategyAction.NORMAL_PACE
    laps_led: int = 0
    strength_score: float = 0.0


@dataclass(frozen=True)
class StrategyOption:
    action: StrategyAction
    label: str
    eligible: bool
    reason: str
    provenance: Provenance = Provenance.MODELED


@dataclass(frozen=True)
class StrategyDecision:
    lap: int
    car_id: str
    position: int
    race_phase: RacePhase
    fuel_remaining_laps: float
    tire_age_laps: int
    recent_pace_seconds: float | None
    field_strategy_summary: str
    available_actions: tuple[StrategyOption, ...]
    reason_for_decision: str
    provenance: Provenance = Provenance.SIMULATED


@dataclass(frozen=True)
class RaceEvent:
    event_type: str
    lap: int
    message: str
    car_id: str | None = None
    data: dict[str, float | int | str | bool] = field(default_factory=dict)
    provenance: Provenance = Provenance.SIMULATED


@dataclass(frozen=True)
class StageResult:
    stage_number: int
    completion_lap: int
    winner_car_id: str
    user_position: int
    top_10: tuple[str, ...]
    provenance: Provenance = Provenance.SIMULATED


@dataclass(frozen=True)
class SimulationSnapshot:
    lap: int
    phase: RacePhase
    leader_car_id: str
    running_order: tuple[str, ...]
    user_position: int
    user_fuel_remaining_laps: float
    user_tire_age_laps: int
    provenance: Provenance = Provenance.SIMULATED


@dataclass(frozen=True)
class RaceResult:
    seed: int
    scheduled_laps: int
    field_size: int
    winner_car_id: str
    final_order: tuple[str, ...]
    caution_count: int
    lead_changes: int
    pit_stop_count: int
    strategy_split_count: int
    dnf_count: int
    user_car_id: str
    user_start_position: int
    user_finish_position: int
    stage_results: tuple[StageResult, ...]
    event_count: int
    provenance: Provenance = Provenance.SIMULATED
