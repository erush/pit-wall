from fastapi.testclient import TestClient

from api.main import app


def test_pitwall_session_creation_and_pre_race_state():
    client = TestClient(app)

    response = client.post(
        "/api/v1/nascar/pit-wall/races",
        json={"seed": 1847, "track_id": "trk_darlington_raceway"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"].startswith("pitwall-1847-")
    assert payload["race"]["lap"] == 0
    assert payload["race"]["track_id"] == "trk_darlington_raceway"
    assert payload["race"]["track_name"] == "Darlington Raceway"
    assert payload["race"]["track_type"] == "Intermediate"
    assert payload["race"]["race_laps"] == 367
    assert payload["race"]["total_laps"] == 367
    assert payload["race"]["control_mode"] == "HUMAN"
    assert payload["my_car"]["car_number"]
    assert payload["my_car"]["starting_position"] >= 1


def test_pitwall_advance_commit_state_and_hidden_boundary():
    client = TestClient(app)
    session_id = client.post(
        "/api/v1/nascar/pit-wall/races",
        json={"seed": 1847, "control_mode": "CO_CREW_CHIEF", "track_id": "trk_watkins_glen_international"},
    ).json()["session_id"]

    advanced = client.post(f"/api/v1/nascar/pit-wall/races/{session_id}/advance")
    assert advanced.status_code == 200
    decision = advanced.json()["decision"]
    action = next(option["action"] for option in decision["available_actions"] if option["eligible"])

    normal_field = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/field").json()
    debug_field = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/field?debug=true").json()
    assert all(row["strategy_archetype"] is None for row in normal_field["running_order"])
    assert any(row["strategy_archetype"] for row in debug_field["running_order"])

    stale = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/strategy",
        json={"action": action, "decision_id": f"{decision['decision_id']}-old", "actor": "WEBMCP_AGENT"},
    )
    assert stale.status_code == 200
    assert stale.json()["accepted"] is False

    committed = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/strategy",
        json={"action": action, "decision_id": decision["decision_id"], "actor": "WEBMCP_AGENT"},
    )
    assert committed.status_code == 200
    assert committed.json()["accepted"] is True

    history = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/decision-history").json()
    assert history[0]["action"] == action
    assert history[0]["actor"] == "WEBMCP_AGENT"
    assert history[0]["position_before"] >= 1
    assert history[0]["position_after_commit"] >= 1

    events = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/events?since_cursor=0&limit=200").json()
    assert any(event["event_type"] == "StrategyDecisionCommitted" and event["actor"] == "WEBMCP_AGENT" for event in events)


def test_pitwall_ai_control_handoff_api_contract():
    client = TestClient(app)
    payload = client.post(
        "/api/v1/nascar/pit-wall/races",
        json={"seed": 1851, "control_mode": "AI_CREW_CHIEF", "track_id": "trk_watkins_glen_international"},
    ).json()
    session_id = payload["session_id"]

    assert payload["race"]["current_controller"] == "NONE"
    assert payload["race"]["delegation_status"] == "AWAITING_AGENT"

    human_advanced = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/advance",
        json={"actor": "HUMAN"},
    )
    assert human_advanced.status_code == 200
    decision = human_advanced.json()["decision"]
    waiting_state = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/state").json()
    assert waiting_state["current_controller"] == "NONE"
    assert waiting_state["delegation_status"] == "AWAITING_AGENT"

    action = next(option["action"] for option in decision["available_actions"] if option["eligible"])
    activated = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/strategy",
        json={"action": action, "decision_id": decision["decision_id"], "actor": "WEBMCP_AGENT"},
    )
    assert activated.status_code == 200
    assert activated.json()["accepted"] is True

    state = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/state").json()
    assert state["track_id"] == "trk_watkins_glen_international"
    assert state["track_name"] == "Watkins Glen International"
    assert state["race_laps"] == 90
    assert state["current_controller"] == "WEBMCP_AGENT"
    assert state["delegation_status"] == "ACTIVE"

    human_locked = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/advance",
        json={"actor": "HUMAN"},
    )
    assert human_locked.status_code == 200
    assert human_locked.json()["accepted"] is False

    paused = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/control",
        json={"action": "TAKE_CONTROL"},
    )
    assert paused.status_code == 200
    assert paused.json()["accepted"] is True
    assert paused.json()["current_controller"] == "HUMAN"
    assert paused.json()["delegation_status"] == "PAUSED"

    takeover_advanced = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/advance",
        json={"actor": "HUMAN"},
    )
    assert takeover_advanced.status_code == 200
    takeover_decision = takeover_advanced.json()["decision"]

    returned = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/control",
        json={"action": "RETURN_TO_AI"},
    )
    assert returned.status_code == 200
    assert returned.json()["accepted"] is True
    assert returned.json()["current_controller"] == "HUMAN"
    assert returned.json()["delegation_status"] == "AWAITING_AGENT"

    takeover_action = next(option["action"] for option in takeover_decision["available_actions"] if option["eligible"])
    human_commit = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/strategy",
        json={"action": takeover_action, "decision_id": takeover_decision["decision_id"], "actor": "HUMAN"},
    )
    assert human_commit.status_code == 200
    assert human_commit.json()["accepted"] is True

    reactivated = client.post(
        f"/api/v1/nascar/pit-wall/races/{session_id}/advance",
        json={"actor": "WEBMCP_AGENT"},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "DECISION"
    reactivated_state = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/state").json()
    assert reactivated_state["current_controller"] == "WEBMCP_AGENT"
    assert reactivated_state["delegation_status"] == "ACTIVE"


def test_pitwall_race_completion_through_api():
    client = TestClient(app)
    session_id = client.post("/api/v1/nascar/pit-wall/races", json={"seed": 1849}).json()["session_id"]

    for _ in range(50):
        advanced = client.post(f"/api/v1/nascar/pit-wall/races/{session_id}/advance").json()
        if advanced["status"] == "FINISHED":
            break
        committed = client.post(f"/api/v1/nascar/pit-wall/races/{session_id}/auto-strategy").json()
        assert committed["accepted"] is True
    else:
        raise AssertionError("Race did not finish through API")

    result = client.get(f"/api/v1/nascar/pit-wall/races/{session_id}/result").json()
    assert result["user_finish_position"] >= 1
    assert result["winner_driver_name"]
    assert result["strategy_decisions"]


def test_pitwall_unknown_session_returns_404():
    client = TestClient(app)

    response = client.get("/api/v1/nascar/pit-wall/races/not-real/state")

    assert response.status_code == 404
