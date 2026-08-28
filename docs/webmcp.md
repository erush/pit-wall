# WebMCP Integration

Pit Wall uses WebMCP to expose race-strategy capabilities directly to external AI agents.

The browser application registers structured tools using:

```javascript
document.modelContext.registerTool({
  name,
  description,
  inputSchema,
  execute
});
```

These tools operate on the same live race session used by the human-facing interface.

## Site Tools

Pit Wall registers eight WebMCP tools.

| Tool | Type | Purpose |
|---|---|---|
| `get_race_state` | Read | Current track, lap, phase, race status, and control context |
| `get_my_car_state` | Read | Position, tires, fuel, pace, and user-car state |
| `get_field_state` | Read | Observable field and competitor context |
| `get_current_decision` | Read | Current actionable strategy decision |
| `get_recent_events` | Read | Recent meaningful race events |
| `get_decision_history` | Read | Human and AI strategy-call history |
| `commit_strategy` | Mutation | Execute a valid pending strategy decision |
| `advance_to_next_decision` | Mutation | Advance routine racing to the next meaningful strategy call |

## Atomic Delegation

The human can delegate exactly one decision:

> Take this strategy call for me.

ChatGPT can:

1. inspect the current race
2. inspect the pending decision
3. reason about strategy
4. execute one valid call
5. stop

The human then resumes race progression.

## Bounded Delegation

The human can delegate a defined portion of the race:

> Call strategy through the end of this stage, then stop.

The agent can repeatedly use the same eight tools until the requested boundary is reached.

No separate "stage agent" or additional WebMCP tool is required.

## Full-Race Delegation

The human can delegate the entire race:

> Take the pit box and call this race through the checkered flag. Maximize our finishing position.

The agent can repeatedly:

```text
advance
   ↓
inspect
   ↓
reason
   ↓
commit
   ↓
advance
   ↓
repeat
```

until the race reaches the checkered flag.

## Native ChatGPT Interaction

Pit Wall does not embed a fake or separate ChatGPT client.

The external agent is invoked through ChatGPT's native **Work with ChatGPT** experience while the user views the WebMCP-enabled page.

Pit Wall provides structured application capabilities.

ChatGPT provides reasoning and tool selection.

Both operate on the same live race.

## Actor Provenance

Strategy mutations preserve actor provenance:

- `HUMAN`
- `WEBMCP_AGENT`
- `AUTO_POLICY`

Player-facing user-team decisions are presented as:

- Human
- AI Crew Chief

This makes human-agent participation auditable throughout the race and in the final recap.

## Control Semantics

### Human

The human owns race strategy.

WebMCP can inspect the race but cannot silently steal control.

### Co-Crew Chief

Human and ChatGPT share the pit box.

The default collaborative interaction is one strategy decision at a time, while bounded delegation is also supported.

### AI Crew Chief

The player intends to delegate race strategy to ChatGPT.

Actual agent ownership begins only after a valid `WEBMCP_AGENT` mutation establishes external-agent participation.

## Decision Integrity

Pit Wall rejects:

- stale decision IDs
- invalid strategy actions
- duplicate or invalid mutations
- actions after race completion
- unauthorized mutations based on control state

A pending decision is a hard stop boundary. `advance_to_next_decision` cannot silently advance beyond it.

## Hidden Information

The WebMCP agent does not receive:

- future cautions
- future race events
- hidden opponent policies
- future outcomes

The agent must make strategy decisions from the observable race state available at that moment.

## Why WebMCP

Without WebMCP, an AI agent would need to infer Pit Wall's semantics from visual controls.

With WebMCP, Pit Wall exposes the actual semantic operations of a crew chief.

This enables a shared application where the human and agent can collaborate at different levels of autonomy without maintaining separate game state.