from __future__ import annotations

import random

from src.simulation.models import (
    CarState,
    CrewChiefPolicy,
    DriverPerformanceProfile,
    FuelState,
    PolicyArchetype,
    Provenance,
    Quantity,
    RaceConfig,
    RaceObjective,
    StrategyAction,
    TeamPerformanceProfile,
    TireState,
)

FIRST_NAMES = (
    "Cal", "Mason", "Riley", "Tate", "Drew", "Hayes", "Logan", "Avery",
    "Parker", "Blake", "Jesse", "Rowan", "Colby", "Nolan", "Reese", "Wyatt",
)
LAST_NAMES = (
    "Mercer", "Vance", "Keller", "Rourke", "Sawyer", "Bishop", "Dalton", "Pierce",
    "Hale", "Grady", "Sutton", "Maddox", "Keene", "Lowell", "Archer", "Baird",
)
TEAM_NAMES = (
    "Summit Ridge Racing", "Ironwood Motorsports", "Cobalt Lane Racing", "Keystone Autosport",
    "Northstar Competition", "Redline Union", "Harbor Point Racing", "Atlas Stock Car",
    "Turn Four Motorsports", "Blacktop Alliance", "Crescent Valley Racing", "Metroplex Speed",
)
MANUFACTURERS = ("Apex", "Comet", "Vanguard")


def _rating(rng: random.Random, mean: float = 0.0, spread: float = 1.0) -> float:
    return max(-2.2, min(2.2, rng.gauss(mean, spread)))


def _policy(index: int, rng: random.Random) -> CrewChiefPolicy:
    archetype = list(PolicyArchetype)[index % len(PolicyArchetype)]
    if archetype == PolicyArchetype.CONSERVATIVE:
        weights = (0.78, 0.12, 0.10, 0.78)
    elif archetype == PolicyArchetype.AGGRESSIVE:
        weights = (0.45, 0.40, 0.15, 0.25)
    elif archetype == PolicyArchetype.STAGE_OPTIMIZER:
        weights = (0.45, 0.15, 0.40, 0.45)
    elif archetype == PolicyArchetype.LONG_RUN_OPTIMIZER:
        weights = (0.70, 0.18, 0.12, 0.42)
    else:
        weights = (0.65, 0.25, 0.10, 0.36)
    jitter = [rng.uniform(-0.04, 0.04) for _ in range(4)]
    return CrewChiefPolicy(
        policy_id=f"policy_{archetype.value.lower()}_{index + 1}",
        archetype=archetype,
        finish_weight=max(0.0, weights[0] + jitter[0]),
        win_weight=max(0.0, weights[1] + jitter[1]),
        stage_weight=max(0.0, weights[2] + jitter[2]),
        risk_aversion=max(0.0, weights[3] + jitter[3]),
    )


def generate_fictional_field(config: RaceConfig, seed: int | None = None) -> list[CarState]:
    """Generate fictional teams from distribution-shaped, non-identity historical proxies.

    The ratings are derived in form from the readiness-approved analytics categories:
    pace percentile, qualifying strength, long-run strength, consistency, traffic, and
    reliability. V0 samples the distributions directly because no individual real driver
    identity should be cloned into the playable universe.
    """
    rng = random.Random(config.seed if seed is None else seed)
    field_size = int(config.field_size.value)
    numbers = rng.sample([str(n) for n in range(1, 100)], field_size)
    cars: list[CarState] = []
    latent_strengths = sorted([rng.gauss(0.0, 0.95) for _ in range(field_size)], reverse=True)

    for i in range(field_size):
        latent = latent_strengths[i]
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 5 + rng.randrange(len(LAST_NAMES))) % len(LAST_NAMES)]
        team_name = TEAM_NAMES[i % len(TEAM_NAMES)]
        driver = DriverPerformanceProfile(
            driver_id=f"fictional_driver_{i + 1:02d}",
            display_name=f"{first} {last}",
            baseline_pace_rating=Quantity(_rating(rng, latent, 0.38), Provenance.DERIVED, "z_score", "analytics_driver_race_lap distribution proxy"),
            qualifying_rating=Quantity(_rating(rng, latent * 0.72, 0.55), Provenance.DERIVED, "z_score", "start/qualifying distribution proxy"),
            long_run_rating=Quantity(_rating(rng, latent * 0.80, 0.48), Provenance.DERIVED, "z_score", "long-run analytics distribution proxy"),
            consistency_rating=Quantity(_rating(rng, latent * 0.35, 0.62), Provenance.DERIVED, "z_score", "lap variability distribution proxy"),
            track_fit_rating=Quantity(_rating(rng, latent * 0.50, 0.58), Provenance.DERIVED, "z_score", "track-type analytics distribution proxy"),
            tire_management_rating=Quantity(_rating(rng, latent * 0.45, 0.58), Provenance.MODELED, "z_score", "modeled tire management proxy"),
            traffic_rating=Quantity(_rating(rng, latent * 0.30, 0.65), Provenance.DERIVED, "z_score", "running-position/pass distribution proxy"),
            reliability_rating=Quantity(_rating(rng, latent * 0.25, 0.70), Provenance.DERIVED, "z_score", "DNF distribution proxy"),
        )
        equipment = _rating(rng, latent * 0.82, 0.42)
        team = TeamPerformanceProfile(
            team_id=f"fictional_team_{i % len(TEAM_NAMES) + 1:02d}",
            display_name=team_name,
            equipment_rating=Quantity(equipment, Provenance.DERIVED, "z_score", "team/equipment distribution proxy"),
            pit_crew_rating=Quantity(_rating(rng, equipment * 0.50, 0.62), Provenance.MODELED, "z_score", "modeled pit crew proxy"),
            reliability_rating=Quantity(_rating(rng, equipment * 0.30, 0.65), Provenance.DERIVED, "z_score", "team DNF proxy"),
            manufacturer=MANUFACTURERS[i % len(MANUFACTURERS)],
        )
        strength = (
            float(driver.baseline_pace_rating.value) * 0.36
            + float(driver.long_run_rating.value) * 0.18
            + float(driver.track_fit_rating.value) * 0.15
            + float(team.equipment_rating.value) * 0.31
        )
        cars.append(
            CarState(
                car_id=f"car_{i + 1:02d}",
                car_number=numbers[i],
                driver=driver,
                team=team,
                policy=_policy(i, rng),
                objective=RaceObjective.EXPECTED_FINISH,
                position=i + 1,
                start_position=i + 1,
                tire=TireState(0, StrategyAction.PIT_4_TIRES, Quantity(1.0, Provenance.MODELED, "grip")),
                fuel=FuelState(
                    capacity_laps=float(config.nominal_fuel_window_laps.value),
                    remaining_laps=float(config.nominal_fuel_window_laps.value),
                    burn_per_lap=1.0,
                ),
                strength_score=strength,
            )
        )

    cars.sort(key=lambda c: (-float(c.driver.qualifying_rating.value) - float(c.team.equipment_rating.value) * 0.55, c.car_id))
    for pos, car in enumerate(cars, start=1):
        car.position = pos
        car.start_position = pos
        car.total_time_seconds = pos * 0.12
    return cars
