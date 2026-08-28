"""Headless NASCAR-style race simulation V0."""

from src.simulation.config import default_race_config
from src.simulation.engine import RaceSimulation
from src.simulation.field import generate_fictional_field

__all__ = ["RaceSimulation", "default_race_config", "generate_fictional_field"]
