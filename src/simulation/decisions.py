from __future__ import annotations

from src.simulation.models import CarState, RaceConfig, RacePhase, StrategyAction, StrategyOption


def available_strategy_options(car: CarState, config: RaceConfig, phase: RacePhase, laps_remaining: int) -> tuple[StrategyOption, ...]:
    can_pit = phase in {RacePhase.GREEN, RacePhase.CAUTION, RacePhase.STAGE_BREAK}
    fuel_tight = car.fuel.remaining_laps <= laps_remaining + 2
    tire_worn = car.tire.age_laps >= int(config.baseline_tire_life_laps.value) * 0.65
    return (
        StrategyOption(StrategyAction.STAY_OUT, "Stay out", True, "Always available while racing."),
        StrategyOption(StrategyAction.PIT_4_TIRES, "Pit: 4 tires + fuel", can_pit, "Available during green, caution, and stage break." if can_pit else "Race is not in a pit-eligible phase."),
        StrategyOption(StrategyAction.PIT_2_TIRES, "Pit: 2 tires + fuel", can_pit and car.tire.age_laps >= 4, "Modeled track-position tire call." if can_pit and car.tire.age_laps >= 4 else "Requires at least lightly used tires and a pit-eligible phase."),
        StrategyOption(StrategyAction.PIT_FUEL_ONLY, "Pit: fuel only", can_pit and not tire_worn, "Modeled fuel-only call when tires are still usable." if can_pit and not tire_worn else "Fuel-only is invalid on heavily worn tires."),
        StrategyOption(StrategyAction.SHORT_PIT, "Short pit", can_pit and phase == RacePhase.GREEN and car.fuel.remaining_laps > 6, "Available before the fuel cliff under green." if can_pit and phase == RacePhase.GREEN and car.fuel.remaining_laps > 6 else "Short-pit requires green-flag margin."),
        StrategyOption(StrategyAction.EXTEND_STINT, "Extend stint", fuel_tight or tire_worn, "Valid as a strategic extension near a pit window."),
        StrategyOption(StrategyAction.NORMAL_PACE, "Normal pace", True, "Default pace mode."),
        StrategyOption(StrategyAction.SAVE_FUEL, "Save fuel", car.fuel.remaining_laps < laps_remaining, "Available when fuel range matters." if car.fuel.remaining_laps < laps_remaining else "Fuel saving is not needed yet."),
    )


def validate_action(action: StrategyAction, options: tuple[StrategyOption, ...]) -> None:
    for option in options:
        if option.action == action:
            if option.eligible:
                return
            raise ValueError(f"{action.value} is not eligible: {option.reason}")
    raise ValueError(f"{action.value} is not available in this decision context")
