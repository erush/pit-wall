from __future__ import annotations

import csv
from pathlib import Path

from src.simulation.config import default_race_config
from src.simulation.engine import RaceSimulation
from src.simulation.field import generate_fictional_field


def run_audit(output_csv: Path, races: int = 100, base_seed: int = 1847) -> dict[str, float | int]:
    rows: list[dict[str, int | float | str]] = []
    winners: set[str] = set()
    total_decisions = 0
    for i in range(races):
        seed = base_seed + i
        config = default_race_config(seed=seed)
        field = generate_fictional_field(config)
        sim = RaceSimulation(config, field)
        result = sim.run_to_finish(user_policy_auto=True)
        winners.add(result.winner_car_id)
        total_decisions += sum(1 for e in sim.events if e.event_type == "StrategyDecisionCommitted" and e.car_id == result.user_car_id)
        strongest = min(field, key=lambda c: c.start_position)
        weakest = max(field, key=lambda c: c.start_position)
        rows.append(
            {
                "seed": seed,
                "winner_car_id": result.winner_car_id,
                "cautions": result.caution_count,
                "lead_changes": result.lead_changes,
                "pit_stops": result.pit_stop_count,
                "strategy_splits": result.strategy_split_count,
                "dnfs": result.dnf_count,
                "user_start": result.user_start_position,
                "user_finish": result.user_finish_position,
                "winner_start": next(c.start_position for c in field if c.car_id == result.winner_car_id),
                "strongest_finish": strongest.position,
                "weakest_finish": weakest.position,
            }
        )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "races": races,
        "unique_winners": len(winners),
        "avg_cautions": round(sum(int(r["cautions"]) for r in rows) / races, 2),
        "avg_lead_changes": round(sum(int(r["lead_changes"]) for r in rows) / races, 2),
        "avg_pit_stops": round(sum(int(r["pit_stops"]) for r in rows) / races, 2),
        "avg_strategy_splits": round(sum(int(r["strategy_splits"]) for r in rows) / races, 2),
        "avg_decisions": round(total_decisions / races, 2),
        "avg_dnfs": round(sum(int(r["dnfs"]) for r in rows) / races, 2),
        "avg_winner_start": round(sum(int(r["winner_start"]) for r in rows) / races, 2),
        "avg_strongest_finish": round(sum(int(r["strongest_finish"]) for r in rows) / races, 2),
        "avg_weakest_finish": round(sum(int(r["weakest_finish"]) for r in rows) / races, 2),
    }
