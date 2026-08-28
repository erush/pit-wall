from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from src.pitwall import ControlActionResult, PitWallAdapter, RaceFinishedResponse


router = APIRouter()
adapter = PitWallAdapter()


class CreateRaceRequest(BaseModel):
    seed: int | None = None
    control_mode: str | None = None
    track_id: str | None = None


class StrategyRequest(BaseModel):
    action: str
    decision_id: str | None = None
    actor: str | None = None


class AdvanceRequest(BaseModel):
    actor: str | None = None


class ControlRequest(BaseModel):
    action: str


def _json(payload: Any) -> Any:
    if is_dataclass(payload):
        payload = asdict(payload)
    elif isinstance(payload, tuple):
        payload = [asdict(item) if is_dataclass(item) else item for item in payload]
    return jsonable_encoder(payload)


def _guard(operation):
    try:
        return operation()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pit-wall/races")
def create_race(request: CreateRaceRequest | None = None):
    seed = request.seed if request and request.seed is not None else 1847
    control_mode = request.control_mode if request and request.control_mode is not None else "HUMAN"
    track_id = request.track_id if request and request.track_id is not None else None
    kwargs = {"seed": seed, "control_mode": control_mode}
    if track_id is not None:
        kwargs["track_id"] = track_id
    session = _guard(lambda: adapter.create_race(**kwargs))
    return _json(
        {
            "session_id": session.session_id,
            "seed": session.seed,
            "race": adapter.get_race_state(session.session_id),
            "my_car": adapter.get_my_car_state(session.session_id),
        }
    )


@router.get("/pit-wall/races/{session_id}/state")
def race_state(session_id: str):
    return _json(_guard(lambda: adapter.get_race_state(session_id)))


@router.get("/pit-wall/races/{session_id}/my-car")
def my_car(session_id: str):
    return _json(_guard(lambda: adapter.get_my_car_state(session_id)))


@router.get("/pit-wall/races/{session_id}/field")
def field(session_id: str, window: int = Query(13, ge=3, le=32), debug: bool = False):
    return _json(_guard(lambda: adapter.get_field_state(session_id, window=window, debug=debug)))


@router.get("/pit-wall/races/{session_id}/decision")
def current_decision(session_id: str):
    return _json(_guard(lambda: adapter.get_current_decision(session_id)))


@router.get("/pit-wall/races/{session_id}/events")
def recent_events(session_id: str, since_cursor: int | None = None, limit: int = Query(40, ge=1, le=200)):
    return _json(_guard(lambda: adapter.get_recent_events(session_id, since_cursor=since_cursor, limit=limit)))


@router.get("/pit-wall/races/{session_id}/decision-history")
def decision_history(session_id: str):
    return _json(_guard(lambda: adapter.get_decision_history(session_id)))


@router.post("/pit-wall/races/{session_id}/strategy")
def commit_strategy(session_id: str, request: StrategyRequest):
    actor = request.actor or "HUMAN"
    return _json(_guard(lambda: adapter.commit_strategy(session_id, request.action, request.decision_id, actor=actor)))


@router.post("/pit-wall/races/{session_id}/advance")
def advance(session_id: str, request: AdvanceRequest | None = None):
    actor = request.actor if request and request.actor else "HUMAN"
    result = _guard(lambda: adapter.advance_to_next_decision(session_id, actor=actor))
    if isinstance(result, ControlActionResult):
        return _json(result)
    if isinstance(result, RaceFinishedResponse):
        return _json({"status": "FINISHED", "result": result.result})
    return _json({"status": "DECISION", "decision": result})


@router.post("/pit-wall/races/{session_id}/control")
def control(session_id: str, request: ControlRequest):
    action = request.action.upper()
    if action == "HANDOFF_TO_AI":
        result = _guard(lambda: adapter.handoff_to_ai(session_id))
    elif action == "TAKE_CONTROL":
        result = _guard(lambda: adapter.take_control(session_id))
    elif action == "RETURN_TO_AI":
        result = _guard(lambda: adapter.return_to_ai(session_id))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown control action: {request.action}")
    return _json(result)


@router.post("/pit-wall/races/{session_id}/auto-strategy")
def auto_strategy(session_id: str):
    return _json(_guard(lambda: adapter.auto_commit_current_decision(session_id)))


@router.get("/pit-wall/races/{session_id}/result")
def race_result(session_id: str):
    return _json(_guard(lambda: adapter.get_race_result(session_id)))
