# Pit Wall

**A WebMCP-powered stock-car race strategy game where humans and AI agents share the crew-chief role.**

Pit Wall puts you on the pit box against a field of autonomous rival crew chiefs. Manage tires, fuel, cautions, pit timing, and track position yourself, collaborate with ChatGPT one decision or stage at a time, or delegate an entire race to an AI Crew Chief through WebMCP Site Tools.

**Live app:** https://nascar-pit-wall.onrender.com/

## Why WebMCP?

Traditional browser agents have to interpret interfaces visually and infer what buttons, controls, and application state mean.

Pit Wall exposes the semantic operations of a race strategist directly through WebMCP.

The human and ChatGPT operate the **same live race session**.

A player can:

- make every strategy decision manually;
- ask ChatGPT to handle a single strategy call;
- delegate a bounded stint or stage;
- hand ChatGPT the entire race;
- inspect the consequences of AI decisions;
- take control again without restarting the race.

WebMCP turns ChatGPT from an external adviser into an actual participant in the game.

## Human + Agent Gameplay

### Human

You control race progression and make every strategy call.

### Co-Crew Chief

You and ChatGPT share the pit box.

At any strategic decision, use ChatGPT's **Work with ChatGPT** interaction and ask:

> Take this strategy call for me.

ChatGPT can inspect the live race through WebMCP, execute exactly that decision, and return the race to you.

You can also delegate a bounded portion of the race:

> Call strategy through the end of this stage, then stop.

### AI Crew Chief

Delegate the entire pit box:

> Take the pit box and call this race through the checkered flag. Maximize our finishing position.

ChatGPT can repeatedly inspect race state, reason about strategy, execute decisions, and advance to the next meaningful decision through WebMCP.

## WebMCP Site Tools

Pit Wall registers eight structured tools with `document.modelContext.registerTool(...)`.

| Tool | Type | Purpose |
|---|---|---|
| `get_race_state` | Read | Current race, track, phase, lap, and control context |
| `get_my_car_state` | Read | Position, tires, fuel, pace, and user-car state |
| `get_field_state` | Read | Observable field and competitor context |
| `get_current_decision` | Read | Current actionable strategy decision |
| `get_recent_events` | Read | Recent meaningful race events |
| `get_decision_history` | Read | Human and AI strategy-call history |
| `commit_strategy` | Mutation | Execute a valid strategy decision |
| `advance_to_next_decision` | Mutation | Advance routine racing to the next meaningful call |

The same tool surface supports atomic, bounded, and full-race delegation.

## Strategy

Depending on race state, Pit Wall supports calls including:

- Stay Out
- 4 Tires + Fuel
- 2 Tires + Fuel
- Fuel Only
- Short Pit
- Extend Stint
- Normal Pace
- Save Fuel

Every strategy call records its actor provenance so the race history can distinguish **Human** and **AI Crew Chief** decisions.

## Tracks

Pit Wall currently includes five differentiated race environments:

- Daytona International Speedway
- Bristol Motor Speedway
- Darlington Raceway
- Pocono Raceway
- Watkins Glen International

Track selection changes race configuration and strategic conditions while preserving the same human-agent interaction model.

## Autonomous Competition

The player races against autonomous rival pit walls.

Opponent strategy policies independently respond to race conditions, producing strategy splits around cautions, pit windows, fuel state, and race progression.

The UI exposes aggregate field strategy without exposing hidden opponent policies to the player or agent.

## Architecture

```text
React Pit Wall UI
        │
        ├──────── Human
        │
        └──────── ChatGPT / WebMCP
                       │
                       ▼
               WebMCP Site Tools
                       │
                       ▼
                  FastAPI API
                       │
                       ▼
                Pit Wall Adapter
                       │
                       ▼
             Race Simulation Engine
                       │
              ┌────────┴────────┐
              │                 │
          User Car       Autonomous Field
```

Human UI actions and WebMCP actions operate on the same canonical race session.

## Data and Simulation Boundary

Pit Wall grew from prior NASCAR data and analytics research, but the standalone application does **not** require the original NASCAR warehouse or DuckDB database at runtime.

The current game deliberately distinguishes between real-world grounding and simulation.

**Data-backed / derived**

- track identities;
- track types;
- track lengths;
- prior NASCAR research used during development and calibration.

**Modeled**

- tire behavior;
- fuel behavior;
- pit-service effects;
- caution generation;
- traffic effects;
- autonomous strategy policies.

**Simulated**

- fictional drivers;
- race events;
- strategy outcomes;
- finishing order.

Pit Wall does not claim to reproduce historical NASCAR races or official NASCAR strategy systems.

## WebMCP Challenge

Pit Wall was developed for the WebMCP Challenge using an existing NASCAR data and analytics project as its research foundation.

The challenge work transformed that foundation into a new:

- stateful race simulation;
- autonomous multi-agent competition;
- Pit Wall browser game;
- human-agent control model;
- WebMCP Site Tools interface;
- deployed interactive product.

The standalone repository contains everything required to run Pit Wall without the original data warehouse.

## Local Development

### Requirements

- Python 3.11+
- Node.js / npm

### Backend

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the API:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

### Frontend

Install dependencies:

```bash
npm install
```

Run Vite:

```bash
npm run dev
```

Build production assets:

```bash
npm run build
```

## Tests

Run the standalone Pit Wall suite:

```bash
python -m pytest tests/test_race_simulation_v0.py tests/test_pitwall_adapter_v1.py tests/test_pitwall_api_v1.py tests/test_pitwall_webmcp_v1.py
```

Current standalone extraction baseline:

```text
37 passed
```

## Production

Pit Wall supports a single-origin Docker deployment.

The included:

- `Dockerfile`
- `render.yaml`
- `.dockerignore`
- `.env.example`

provide the production deployment configuration.

The React frontend is built into `dist/` and served by FastAPI alongside the Pit Wall API.

## WebMCP Testing

Open the deployed application in ChatGPT's WebMCP-capable built-in browser.

When Site Tools are available, use **Work with ChatGPT** to delegate race strategy.

For Co-Crew Chief:

> Take this strategy call for me.

For bounded delegation:

> Call strategy through the end of this stage, then stop.

For full AI Crew Chief:

> Take the pit box and call this race through the checkered flag. Maximize our finishing position.

## License

Pit Wall is released under the MIT License. See `LICENSE`.