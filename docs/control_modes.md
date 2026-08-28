# Control Modes

Pit Wall supports three player-facing control experiences.

All three use the same race engine and canonical race session.

## Human

The player controls race progression and makes every strategy decision.

Typical loop:

```text
Next Decision
      ↓
Inspect Race
      ↓
Choose Strategy
      ↓
Observe Consequence
      ↓
Repeat
```

WebMCP Site Tools may inspect the race, but external-agent mutations cannot silently take ownership from a Human-mode race.

## Co-Crew Chief

Human and ChatGPT share the pit box.

This is Pit Wall's primary collaborative WebMCP experience.

At any pending strategy decision, the player can make the call manually or delegate it through **Work with ChatGPT**.

### One Decision

Example:

> Take this strategy call for me.

ChatGPT inspects the live race, executes one strategy decision, and stops.

The human then resumes progression.

### Bounded Stint

Example:

> Call strategy through the end of this stage, then stop.

ChatGPT can operate multiple decision cycles before returning control at the requested boundary.

This supports meaningful collaboration without requiring full-race delegation.

## AI Crew Chief

The player intends to delegate the race to ChatGPT.

Selecting AI Crew Chief does not pretend that the webpage itself launches an external agent.

The player invokes ChatGPT through **Work with ChatGPT**.

Example:

> Take the pit box and call this race through the checkered flag. Maximize our finishing position.

The agent can then repeatedly inspect, reason, execute strategy, and advance the race.

## Agent-Activated Ownership

Pit Wall distinguishes between:

1. intent to use an AI agent
2. actual external-agent participation

Human controls are not locked merely because AI Crew Chief was selected.

Exclusive agent ownership begins only after an actual `WEBMCP_AGENT` mutation proves that the external agent is active.

This prevents the race from deadlocking while waiting for an agent that has not started.

## Take Control

During active AI Crew Chief operation, the human can take control without restarting the race.

The same session is preserved, including:

- field
- lap
- strategy history
- fuel
- tires
- race state

## Return to AI

The human can return the pit box to AI-ready state.

Human controls remain available until a new WebMCP mutation establishes that the agent has resumed participation.

## Provenance

Every user-team strategy call records its actor.

The post-race recap therefore distinguishes:

**Race Mode**

- Human
- Co-Crew Chief
- AI Crew Chief

from:

**Strategy Calls**

- Human
- AI Crew Chief

A Co-Crew Chief race may legitimately contain only Human calls, only AI calls, or a mixture of both.

## Delegation Model

The same WebMCP interface supports three useful scopes:

```text
ONE CALL
Human → AI → Human

BOUNDED STINT
Human → AI for defined period → Human

FULL RACE
Human → AI through checkered
```

No separate simulation or agent implementation is required for each scope.