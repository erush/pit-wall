from __future__ import annotations

import random

from src.simulation.decisions import available_strategy_options
from src.simulation.models import CarState, PolicyArchetype, RaceConfig, RacePhase, StrategyAction


def choose_strategy_action(
    car: CarState,
    config: RaceConfig,
    phase: RacePhase,
    lap: int,
    recent_pitters: int,
    rng: random.Random,
) -> StrategyAction:
    laps_remaining = int(config.scheduled_laps.value) - lap
    options = {o.action: o for o in available_strategy_options(car, config, phase, laps_remaining)}
    fuel_window = float(config.nominal_fuel_window_laps.value)
    tire_life = float(config.baseline_tire_life_laps.value)
    strategy_volatility = float(config.strategy_volatility.value)
    recent_pitter_trigger = max(3, round(6 / max(strategy_volatility, 0.25)))
    split_probability = min(0.82, max(0.28, 0.55 * strategy_volatility))
    stage_soon = any(0 < stage - lap <= 8 for stage in config.stage_ends)
    late = laps_remaining <= 35
    low_fuel = car.fuel.remaining_laps <= 5
    in_window = car.fuel.remaining_laps <= 12 or (car.tire.age_laps >= tire_life * 0.84 and car.fuel.remaining_laps <= 20)
    pitted_recently = bool(car.pit_stops and lap - car.pit_stops[-1].lap <= 8)

    if pitted_recently and not low_fuel:
        return StrategyAction.STAY_OUT if phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK} else StrategyAction.NORMAL_PACE

    if low_fuel and options[StrategyAction.PIT_4_TIRES].eligible:
        return StrategyAction.PIT_4_TIRES

    archetype = car.policy.archetype
    if phase in {RacePhase.CAUTION, RacePhase.STAGE_BREAK}:
        if car.fuel.remaining_laps > 35 and car.tire.age_laps < 18:
            return StrategyAction.STAY_OUT
        if late and car.position <= 6 and archetype == PolicyArchetype.TRACK_POSITION_DEFENDER:
            return StrategyAction.STAY_OUT if rng.random() < 0.58 else StrategyAction.PIT_2_TIRES
        if car.tire.age_laps < 10 and car.fuel.remaining_laps > laps_remaining:
            return StrategyAction.STAY_OUT
        if archetype == PolicyArchetype.AGGRESSIVE and late and options[StrategyAction.PIT_2_TIRES].eligible:
            return StrategyAction.PIT_2_TIRES
        if archetype == PolicyArchetype.STAGE_OPTIMIZER and stage_soon and car.position <= 12:
            return StrategyAction.STAY_OUT
        return StrategyAction.PIT_4_TIRES if options[StrategyAction.PIT_4_TIRES].eligible else StrategyAction.STAY_OUT

    if archetype == PolicyArchetype.AGGRESSIVE and in_window and options[StrategyAction.SHORT_PIT].eligible:
        return StrategyAction.PIT_2_TIRES if late and rng.random() < 0.35 else StrategyAction.SHORT_PIT
    if archetype == PolicyArchetype.LONG_RUN_OPTIMIZER and car.tire.age_laps >= tire_life * 0.80 and car.fuel.remaining_laps <= 18 and options[StrategyAction.PIT_4_TIRES].eligible:
        return StrategyAction.PIT_4_TIRES
    if archetype == PolicyArchetype.STAGE_OPTIMIZER and stage_soon and car.position <= 14:
        return StrategyAction.EXTEND_STINT
    if archetype == PolicyArchetype.TRACK_POSITION_DEFENDER and recent_pitters > 4 and car.fuel.remaining_laps > 4:
        return StrategyAction.EXTEND_STINT
    if archetype == PolicyArchetype.CONSERVATIVE and car.fuel.remaining_laps <= fuel_window * 0.16:
        return StrategyAction.PIT_4_TIRES
    if recent_pitters >= recent_pitter_trigger and in_window and options[StrategyAction.PIT_4_TIRES].eligible:
        return StrategyAction.PIT_4_TIRES if rng.random() < split_probability else StrategyAction.EXTEND_STINT
    if car.fuel.remaining_laps < laps_remaining and car.fuel.remaining_laps < 8:
        return StrategyAction.SAVE_FUEL
    return StrategyAction.NORMAL_PACE
