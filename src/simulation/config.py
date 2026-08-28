from __future__ import annotations

from src.simulation.models import Provenance, Quantity, RaceConfig, TrackConfig, TrackSimulationProfile


DEFAULT_TRACK_ID = "trk_daytona_international_speedway"


TRACK_SIMULATION_PROFILES: dict[str, TrackSimulationProfile] = {
    "trk_daytona_international_speedway": TrackSimulationProfile(
        track_id="trk_daytona_international_speedway",
        track_name="Daytona International Speedway",
        track_type="Superspeedway",
        track_length_miles=Quantity(
            2.5,
            Provenance.OBSERVED,
            "miles",
            "data/reference/tracks.csv; dim_track.track_length_miles",
        ),
        race_laps=Quantity(200, Provenance.DERIVED, "laps", "dim_race representative scheduled Cup distance"),
        stage_1_end=Quantity(65, Provenance.MODELED, "lap", "Representative modern three-stage gameplay split"),
        stage_2_end=Quantity(130, Provenance.MODELED, "lap", "Representative modern three-stage gameplay split"),
        field_size=Quantity(40, Provenance.DERIVED, "cars", "analytics_track_profile.average_field_size rounded"),
        modeled_fuel_window_laps=Quantity(42, Provenance.MODELED, "laps", "Superspeedway pack racing fuel-window approximation"),
        modeled_tire_wear_factor=Quantity(0.82, Provenance.MODELED, "factor", "Lower tire emphasis than abrasive ovals"),
        modeled_caution_rate=Quantity(0.024, Provenance.MODELED, "probability", "Higher incident volatility game model"),
        modeled_restart_volatility=Quantity(5, Provenance.MODELED, "laps", "Pack restart volatility game model"),
        modeled_traffic_effect=Quantity(0.50, Provenance.MODELED, "rating", "Drafting reduces pure track-position penalty"),
        modeled_pit_road_loss=Quantity(42.0, Provenance.MODELED, "seconds", "Long pit-road/gameplay loss approximation"),
        modeled_strategy_volatility=Quantity(1.22, Provenance.MODELED, "factor", "Encourages pack-style strategy variation"),
        source_notes=(
            "Canonical identity, type, and length resolved from data/reference/tracks.csv and dim_track.",
            "Race length and field size use readily available race/profile history.",
            "Fuel, tire, caution, restart, traffic, pit-road, and strategy behavior are explicit MODELED gameplay inputs.",
        ),
    ),
    "trk_bristol_motor_speedway": TrackSimulationProfile(
        track_id="trk_bristol_motor_speedway",
        track_name="Bristol Motor Speedway",
        track_type="Short Track",
        track_length_miles=Quantity(
            0.533,
            Provenance.OBSERVED,
            "miles",
            "data/reference/tracks.csv; dim_track.track_length_miles",
        ),
        race_laps=Quantity(500, Provenance.DERIVED, "laps", "dim_race representative scheduled distance"),
        stage_1_end=Quantity(125, Provenance.MODELED, "lap", "Representative short-track gameplay split"),
        stage_2_end=Quantity(250, Provenance.MODELED, "lap", "Representative short-track gameplay split"),
        field_size=Quantity(36, Provenance.DERIVED, "cars", "analytics_track_profile.average_field_size rounded"),
        modeled_fuel_window_laps=Quantity(88, Provenance.MODELED, "laps", "Short-lap fuel-window approximation"),
        modeled_tire_wear_factor=Quantity(1.18, Provenance.MODELED, "factor", "Short-track traffic and tire management model"),
        modeled_caution_rate=Quantity(0.020, Provenance.MODELED, "probability", "Compact-track incident gameplay model"),
        modeled_restart_volatility=Quantity(4, Provenance.MODELED, "laps", "Short-track restart compression model"),
        modeled_traffic_effect=Quantity(0.92, Provenance.MODELED, "rating", "Heavy traffic sensitivity game model"),
        modeled_pit_road_loss=Quantity(29.0, Provenance.MODELED, "seconds", "Short-track pit-road/gameplay loss approximation"),
        modeled_strategy_volatility=Quantity(1.08, Provenance.MODELED, "factor", "Traffic can split pit timing"),
        source_notes=(
            "Canonical identity, type, and length resolved from data/reference/tracks.csv and dim_track.",
            "Race length and field size use readily available race/profile history.",
            "Fuel, tire, caution, restart, traffic, pit-road, and strategy behavior are explicit MODELED gameplay inputs.",
        ),
    ),
    "trk_darlington_raceway": TrackSimulationProfile(
        track_id="trk_darlington_raceway",
        track_name="Darlington Raceway",
        track_type="Intermediate",
        track_length_miles=Quantity(
            1.366,
            Provenance.OBSERVED,
            "miles",
            "data/reference/tracks.csv; dim_track.track_length_miles",
        ),
        race_laps=Quantity(367, Provenance.DERIVED, "laps", "dim_race representative scheduled distance"),
        stage_1_end=Quantity(115, Provenance.MODELED, "lap", "Representative long-run gameplay split"),
        stage_2_end=Quantity(230, Provenance.MODELED, "lap", "Representative long-run gameplay split"),
        field_size=Quantity(40, Provenance.DERIVED, "cars", "analytics_track_profile.average_field_size rounded"),
        modeled_fuel_window_laps=Quantity(62, Provenance.MODELED, "laps", "Intermediate fuel-window approximation"),
        modeled_tire_wear_factor=Quantity(1.42, Provenance.MODELED, "factor", "High tire-management game model"),
        modeled_caution_rate=Quantity(0.014, Provenance.MODELED, "probability", "Long-run emphasis game model"),
        modeled_restart_volatility=Quantity(3, Provenance.MODELED, "laps", "Moderate restart volatility"),
        modeled_traffic_effect=Quantity(0.76, Provenance.MODELED, "rating", "Track-position/traffic sensitivity model"),
        modeled_pit_road_loss=Quantity(36.5, Provenance.MODELED, "seconds", "Intermediate pit-road/gameplay loss approximation"),
        modeled_strategy_volatility=Quantity(0.96, Provenance.MODELED, "factor", "Long-run tire delta drives strategy"),
        source_notes=(
            "Canonical identity, type, and length resolved from data/reference/tracks.csv and dim_track.",
            "Race length and field size use readily available race/profile history.",
            "Fuel, tire, caution, restart, traffic, pit-road, and strategy behavior are explicit MODELED gameplay inputs.",
        ),
    ),
    "trk_pocono_raceway": TrackSimulationProfile(
        track_id="trk_pocono_raceway",
        track_name="Pocono Raceway",
        track_type="Intermediate",
        track_length_miles=Quantity(
            2.5,
            Provenance.OBSERVED,
            "miles",
            "data/reference/tracks.csv; dim_track.track_length_miles",
        ),
        race_laps=Quantity(160, Provenance.DERIVED, "laps", "dim_race representative scheduled distance"),
        stage_1_end=Quantity(50, Provenance.MODELED, "lap", "Representative fuel/long-run gameplay split"),
        stage_2_end=Quantity(100, Provenance.MODELED, "lap", "Representative fuel/long-run gameplay split"),
        field_size=Quantity(40, Provenance.DERIVED, "cars", "analytics_track_profile.average_field_size rounded"),
        modeled_fuel_window_laps=Quantity(34, Provenance.MODELED, "laps", "Long-lap fuel-window approximation"),
        modeled_tire_wear_factor=Quantity(1.02, Provenance.MODELED, "factor", "Fuel-window emphasis over tire falloff"),
        modeled_caution_rate=Quantity(0.012, Provenance.MODELED, "probability", "Long-run/fuel strategy gameplay model"),
        modeled_restart_volatility=Quantity(3, Provenance.MODELED, "laps", "Moderate restart volatility"),
        modeled_traffic_effect=Quantity(0.62, Provenance.MODELED, "rating", "Long straightaway passing/traffic model"),
        modeled_pit_road_loss=Quantity(41.0, Provenance.MODELED, "seconds", "Long pit-road/gameplay loss approximation"),
        modeled_strategy_volatility=Quantity(1.16, Provenance.MODELED, "factor", "Fuel windows create split strategy"),
        source_notes=(
            "Canonical identity, type, and length resolved from data/reference/tracks.csv and dim_track.",
            "Race length and field size use readily available race/profile history.",
            "Fuel, tire, caution, restart, traffic, pit-road, and strategy behavior are explicit MODELED gameplay inputs.",
        ),
    ),
    "trk_watkins_glen_international": TrackSimulationProfile(
        track_id="trk_watkins_glen_international",
        track_name="Watkins Glen International",
        track_type="Road Course",
        track_length_miles=Quantity(
            2.45,
            Provenance.OBSERVED,
            "miles",
            "data/reference/tracks.csv; dim_track.track_length_miles",
        ),
        race_laps=Quantity(90, Provenance.DERIVED, "laps", "dim_race representative scheduled distance"),
        stage_1_end=Quantity(20, Provenance.MODELED, "lap", "Representative road-course gameplay split"),
        stage_2_end=Quantity(40, Provenance.MODELED, "lap", "Representative road-course gameplay split"),
        field_size=Quantity(40, Provenance.DERIVED, "cars", "analytics_track_profile.average_field_size rounded"),
        modeled_fuel_window_laps=Quantity(27, Provenance.MODELED, "laps", "Road-course fuel-window approximation"),
        modeled_tire_wear_factor=Quantity(0.94, Provenance.MODELED, "factor", "Road-course tire falloff gameplay model"),
        modeled_caution_rate=Quantity(0.010, Provenance.MODELED, "probability", "Lower full-course caution game model"),
        modeled_restart_volatility=Quantity(2, Provenance.MODELED, "laps", "Lower restart shuffle than ovals"),
        modeled_traffic_effect=Quantity(0.70, Provenance.MODELED, "rating", "Road-course passing/traffic model"),
        modeled_pit_road_loss=Quantity(38.0, Provenance.MODELED, "seconds", "Road-course pit-road/gameplay loss approximation"),
        modeled_strategy_volatility=Quantity(1.28, Provenance.MODELED, "factor", "Stage and fuel strategy can diverge"),
        source_notes=(
            "Canonical identity, type, and length resolved from data/reference/tracks.csv and dim_track.",
            "Race length and field size use readily available race/profile history.",
            "Fuel, tire, caution, restart, traffic, pit-road, and strategy behavior are explicit MODELED gameplay inputs.",
        ),
    ),
}


def available_track_profiles() -> tuple[TrackSimulationProfile, ...]:
    return tuple(TRACK_SIMULATION_PROFILES.values())


def get_track_profile(track_id: str = DEFAULT_TRACK_ID) -> TrackSimulationProfile:
    normalized = track_id or DEFAULT_TRACK_ID
    try:
        return TRACK_SIMULATION_PROFILES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown Pit Wall track: {track_id}") from exc


def race_config_for_profile(profile: TrackSimulationProfile, seed: int) -> RaceConfig:
    tire_life = round(float(profile.modeled_fuel_window_laps.value) * float(profile.modeled_tire_wear_factor.value))
    track = TrackConfig(
        track_id=profile.track_id,
        name=profile.track_name,
        track_type=profile.track_type,
        length_miles=profile.track_length_miles,
        track_position_sensitivity=profile.modeled_traffic_effect,
        base_lap_time_seconds=_modeled_base_lap_time(profile),
    )
    return RaceConfig(
        race_id=f"pitwall_{profile.track_id}_{int(profile.race_laps.value)}",
        name=f"{profile.track_name} {int(profile.race_laps.value)}",
        scheduled_laps=profile.race_laps,
        field_size=profile.field_size,
        stage_ends=(int(profile.stage_1_end.value), int(profile.stage_2_end.value)),
        nominal_fuel_window_laps=profile.modeled_fuel_window_laps,
        baseline_tire_life_laps=Quantity(max(12, tire_life), Provenance.MODELED, "laps", profile.modeled_tire_wear_factor.source),
        pit_road_loss_seconds=profile.modeled_pit_road_loss,
        caution_probability_per_green_lap=profile.modeled_caution_rate,
        caution_laps=Quantity(_modeled_caution_laps(profile), Provenance.MODELED, "laps", "Track profile gameplay model"),
        restart_shuffle_laps=profile.modeled_restart_volatility,
        strategy_volatility=profile.modeled_strategy_volatility,
        track=track,
        track_profile=profile,
        seed=seed,
    )


def default_race_config(seed: int = 1847, field_size: int | None = None, track_id: str = DEFAULT_TRACK_ID) -> RaceConfig:
    profile = get_track_profile(track_id)
    if field_size is not None:
        profile = _with_field_size(profile, field_size)
    return race_config_for_profile(profile, seed)


def pine_ridge_test_config(seed: int = 1847, field_size: int = 32) -> RaceConfig:
    """Return the legacy fictional oval as an internal test fixture."""
    track = TrackConfig(
        track_id="fictional_short_oval_v0",
        name="Pine Ridge Speedway",
        track_type="short_oval",
        length_miles=Quantity(0.75, Provenance.MODELED, "miles"),
        track_position_sensitivity=Quantity(0.68, Provenance.MODELED, "rating"),
        base_lap_time_seconds=Quantity(24.2, Provenance.MODELED, "seconds"),
    )
    return RaceConfig(
        race_id="race_sim_v0_pine_ridge_200",
        name="Pine Ridge 200",
        scheduled_laps=Quantity(200, Provenance.MODELED, "laps"),
        field_size=Quantity(field_size, Provenance.MODELED, "cars"),
        stage_ends=(60, 130),
        nominal_fuel_window_laps=Quantity(52, Provenance.MODELED, "laps"),
        baseline_tire_life_laps=Quantity(42, Provenance.MODELED, "laps"),
        pit_road_loss_seconds=Quantity(33.0, Provenance.MODELED, "seconds"),
        caution_probability_per_green_lap=Quantity(0.018, Provenance.MODELED, "probability"),
        caution_laps=Quantity(4, Provenance.MODELED, "laps"),
        restart_shuffle_laps=Quantity(3, Provenance.MODELED, "laps"),
        strategy_volatility=Quantity(1.0, Provenance.MODELED, "factor"),
        track=track,
        seed=seed,
    )


def _with_field_size(profile: TrackSimulationProfile, field_size: int) -> TrackSimulationProfile:
    return TrackSimulationProfile(
        track_id=profile.track_id,
        track_name=profile.track_name,
        track_type=profile.track_type,
        track_length_miles=profile.track_length_miles,
        race_laps=profile.race_laps,
        stage_1_end=profile.stage_1_end,
        stage_2_end=profile.stage_2_end,
        field_size=Quantity(field_size, Provenance.MODELED, "cars", "Caller override"),
        modeled_fuel_window_laps=profile.modeled_fuel_window_laps,
        modeled_tire_wear_factor=profile.modeled_tire_wear_factor,
        modeled_caution_rate=profile.modeled_caution_rate,
        modeled_restart_volatility=profile.modeled_restart_volatility,
        modeled_traffic_effect=profile.modeled_traffic_effect,
        modeled_pit_road_loss=profile.modeled_pit_road_loss,
        modeled_strategy_volatility=profile.modeled_strategy_volatility,
        source_notes=profile.source_notes,
    )


def _modeled_base_lap_time(profile: TrackSimulationProfile) -> Quantity:
    seconds = {
        "trk_daytona_international_speedway": 47.8,
        "trk_bristol_motor_speedway": 15.6,
        "trk_darlington_raceway": 29.4,
        "trk_pocono_raceway": 53.2,
        "trk_watkins_glen_international": 72.5,
    }[profile.track_id]
    return Quantity(seconds, Provenance.MODELED, "seconds", "Track profile baseline lap-time gameplay model")


def _modeled_caution_laps(profile: TrackSimulationProfile) -> int:
    if profile.track_id == "trk_bristol_motor_speedway":
        return 6
    if profile.track_id == "trk_watkins_glen_international":
        return 3
    return 4
