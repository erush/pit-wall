from pathlib import Path


WEBMCP_SOURCE = Path("frontend/src/webmcpTools.js")


def test_webmcp_registers_current_imperative_api_tools():
    source = WEBMCP_SOURCE.read_text()

    assert "documentRef.modelContext.registerTool" in source
    assert "inputSchema" in source
    assert "execute: async" in source
    assert "annotations: { readOnlyHint" in source


def test_webmcp_tool_surface_and_narrow_mutation_schema():
    source = WEBMCP_SOURCE.read_text()
    expected_tools = [
        "get_race_state",
        "get_my_car_state",
        "get_field_state",
        "get_current_decision",
        "get_recent_events",
        "get_decision_history",
        "commit_strategy",
        "advance_to_next_decision",
    ]

    for tool_name in expected_tools:
        assert f'name: "{tool_name}"' in source
    assert source.count('name: "') == len(expected_tools)

    assert 'required: ["decision_id", "action"]' in source
    assert "enum: STRATEGY_ACTIONS" in source
    assert 'actor: "WEBMCP_AGENT"' in source
    assert "control_mode" in source
    assert "current_controller" in source
    assert "track_id" in source
    assert "track_name" in source
    assert "race_laps" in source
    assert "race_intelligence" in source
    assert "fuel-to-boundary" in source
    assert "control-ownership" in source
    assert "next_action_expected" in source
    assert "first valid mutation activates exclusive AI Crew Chief ownership" in source
    assert "default to exactly one pending strategy call" in source
    assert "Human controls remain available until your first valid WebMCP mutation" in source
    assert "continue until the returned race status is FINISHED" in source
    assert "You still own the pit box" in source
    assert "debug=false" in source


def test_webmcp_uses_active_browser_session_and_refresh_event():
    source = WEBMCP_SOURCE.read_text()

    assert "getSessionId()" in source
    assert "No active Pit Wall race session" in source
    assert "await refresh(activeSessionId())" in source
    assert 'new CustomEvent("pitwall:webmcp-action"' in source
