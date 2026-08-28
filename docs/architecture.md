# Pit Wall Architecture

Pit Wall is a standalone stock-car race strategy application built around a shared race session that can be operated by a human or an external AI agent through WebMCP.

## Runtime Architecture

```text
React Pit Wall UI
        │
        ├── Human Player
        │
        └── ChatGPT
              │
              ▼
        WebMCP Site Tools
              │
              ▼
           FastAPI
              │
              ▼
       Pit Wall Adapter
              │
              ▼
      Race Simulation Engine
          │           │
          │           └── Autonomous Rival Pit Walls
          │
          └── User Car / Strategy Decisions
```

## Frontend

The React frontend provides:

- track selection
- Human, Co-Crew Chief, and AI Crew Chief experiences
- race progression
- strategy decisions
- running order
- fuel and tire state
- field-strategy summaries
- race timeline
- Human/AI decision provenance
- post-race recap

The frontend also registers Pit Wall's WebMCP Site Tools.

## API

FastAPI provides the transport layer between the browser and the Pit Wall domain.

The standalone API supports:

- race creation
- race state
- user-car state
- field state
- current strategy decision
- recent race events
- decision history
- strategy mutations
- race progression
- control state
- race results
- application health

The standalone API has no NASCAR warehouse dependency.

## Pit Wall Adapter

`src/pitwall/` provides the application boundary around the simulation engine.

Responsibilities include:

- race-session lifecycle
- stable request/response contracts
- Human and WebMCP actor provenance
- control-mode state
- decision history
- presentation-safe state
- hidden-information boundaries

## Simulation Engine

`src/simulation/` contains the deterministic headless race simulation.

The engine models:

- fictional driver and car performance
- race progression
- tires
- fuel
- pit service
- stages
- cautions
- restarts
- traffic
- autonomous crew-chief strategies
- user strategy decisions
- finishing results

The same engine is used regardless of whether the race is controlled by a human or WebMCP agent.

## Shared Session Model

Human and agent actions mutate the same canonical race session.

WebMCP does not operate a parallel simulation or separate AI-specific game state.

This shared state is the core of Pit Wall's human-agent collaboration model.

## Determinism

Race simulation supports deterministic replay from the same configuration, seed, and strategy decisions.

This supports testing, debugging, and reproducible evaluation.

## Information Boundary

The human player and WebMCP agent receive observable race information.

Hidden simulation information is not exposed through the normal Pit Wall contract, including:

- future stochastic events
- future cautions
- private opponent strategy policies
- hidden simulation coefficients

## Standalone Runtime

This repository does not require:

- the original NASCAR Decision Engine repository
- DuckDB
- a NASCAR warehouse
- raw NASCAR data
- DFS data
- generated analytics outputs

The standalone runtime consists of:

- React and Vite
- FastAPI
- Pit Wall adapter
- race simulation engine
- WebMCP integration