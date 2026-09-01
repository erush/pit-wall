const STRATEGY_ACTIONS = [
  "STAY_OUT",
  "PIT_4_TIRES",
  "PIT_2_TIRES",
  "PIT_FUEL_ONLY",
  "SHORT_PIT",
  "EXTEND_STINT",
  "NORMAL_PACE",
  "SAVE_FUEL"
];

const emptyInput = {
  type: "object",
  properties: {},
  additionalProperties: false
};

export const PIT_WALL_WEBMCP_TOOLS = [
  {
    name: "get_race_state",
    description:
      "Returns high-level observable state for the active Pit Wall race open in this browser tab, including track_id, track_name, track_type, track_length_miles, race_laps, lap, stage/current_stage, completed_stages with stage winners and user stage positions, race status, caution status, leader, user position, active cars, laps remaining, control_mode, current_controller, delegation_status, objective, and next_action_expected. Check the selected track and control metadata before any write: WebMCP writes are rejected in HUMAN mode, allowed alongside the human in CO_CREW_CHIEF mode, and activate exclusive ownership in AI_CREW_CHIEF mode only after your first valid mutating call. Read-only inspection never proves agent presence or locks human controls. In CO_CREW_CHIEF mode, default to one pending decision: inspect, commit_strategy, then stop unless the user explicitly delegated a bounded stint. In AI_CREW_CHIEF mode, once active, continue autonomously: advance_to_next_decision, inspect, commit_strategy, then repeat until race_status is FINISHED or the human takes control. This tool does not advance or modify the race.",
    inputSchema: emptyInput,
    readOnly: true
  },
  {
    name: "get_my_car_state",
    description:
      "Returns observable state for the user's team in the active Pit Wall race, including car number, fictional driver and team, position, start, tire age, estimated fuel laps, recent relative pace, pit stops, and pace mode. Use this to understand the car you are helping crew-chief before choosing a strategy action at the current decision. This tool does not expose hidden simulation coefficients and does not modify race state.",
    inputSchema: emptyInput,
    readOnly: true
  },
  {
    name: "get_field_state",
    description:
      "Returns a strategically useful observable running-order window and field strategy summary for the active Pit Wall race. Use this to compare nearby cars, tire age, fuel estimates, gaps, and recent pit behavior when reasoning about whether to pit, stay out, short pit, extend, or manage pace. It excludes hidden opponent policy archetypes and future race information. This tool does not modify race state.",
    inputSchema: {
      type: "object",
      properties: {
        window: {
          type: "number",
          minimum: 3,
          maximum: 32,
          description: "Optional running-order window size around the user's car. Defaults to 15."
        }
      },
      additionalProperties: false
    },
    readOnly: true
  },
  {
    name: "get_current_decision",
    description:
      "Returns the crew-chief decision currently awaiting action in the active Pit Wall race, including decision ID, lap, reason, race context, fuel and tire state, stage and race laps remaining, recent pace, field strategy summary, valid actions, action descriptions, and next_action_expected. Use this before every commit_strategy call; commit_strategy requires the current pending decision_id from this tool. In CO_CREW_CHIEF mode, the default Work with ChatGPT collaboration is atomic: inspect this one pending decision, commit_strategy once, then stop and return progression to the human unless the user explicitly delegated multiple decisions or a bounded stint. During an active delegated AI Crew Chief run, continue the inspect, reason, commit, advance loop until the race is FINISHED. This tool does not advance or modify the race.",
    inputSchema: emptyInput,
    readOnly: true
  },
  {
    name: "get_recent_events",
    description:
      "Returns a bounded list of recent meaningful observable events for the active Pit Wall race, such as cautions, restarts, pit stops, strategy calls, lead changes, and race finish. Use this for context after advancing or before committing a call, without flooding on every lap. This tool does not expose future events and does not modify race state.",
    inputSchema: {
      type: "object",
      properties: {
        count: {
          type: "number",
          minimum: 1,
          maximum: 80,
          description: "Maximum number of recent meaningful events to return. Defaults to 25."
        }
      },
      additionalProperties: false
    },
    readOnly: true
  },
  {
    name: "get_decision_history",
    description:
      "Returns the user's and WebMCP agent's committed strategy decisions so far in the active Pit Wall race, including decision IDs, laps, actions, actor provenance, and immediate position context. Use this to audit prior calls, preserve continuity after human-agent handoff, and explain the race you are calling. This tool does not modify race state.",
    inputSchema: emptyInput,
    readOnly: true
  },
  {
    name: "commit_strategy",
    description:
      "Commits one valid strategy action for the exact pending crew-chief decision in the active Pit Wall race. Use only after get_race_state confirms WebMCP writes are allowed and get_current_decision returns the current pending decision_id plus one eligible action from available_actions. This changes race state through the same Pit Wall operation used by the human UI, rejects stale decision IDs, invalid actions, missing decisions, finished races, and control-ownership violations, records WEBMCP_AGENT actor provenance in normal history, and returns next_action_expected. In CO_CREW_CHIEF mode, default to exactly one pending strategy call, then stop unless the user explicitly delegated a bounded stint. In AI_CREW_CHIEF READY_FOR_HANDOFF or AWAITING_AGENT state, this first valid mutation activates exclusive AI Crew Chief ownership. To crew-chief an entire AI race, inspect the pending decision, reason from the observable state, commit one strategy, then use advance_to_next_decision and repeat until the race is FINISHED.",
    inputSchema: {
      type: "object",
      properties: {
        decision_id: {
          type: "string",
          description: "The current pending decision ID returned by get_current_decision."
        },
        action: {
          type: "string",
          enum: STRATEGY_ACTIONS,
          description: "One currently eligible action from get_current_decision.available_actions."
        }
      },
      required: ["decision_id", "action"],
      additionalProperties: false
    },
    readOnly: false
  },
  {
    name: "advance_to_next_decision",
    description:
      "Advances the active Pit Wall race through routine green-flag, caution, restart, pit-cycle, and stage-break simulation until strategic intervention is required or the race ends. Use this after get_race_state confirms WebMCP writes are allowed, after a committed decision, or whenever get_current_decision shows no pending decision. This changes race state through the same Pit Wall operation used by the human UI, rejects control-ownership violations, and returns a concise before/after summary plus next_action_expected. In CO_CREW_CHIEF mode, call this across decisions only when the user explicitly delegated multiple decisions or a bounded stint. In AI_CREW_CHIEF READY_FOR_HANDOFF or AWAITING_AGENT state, this first valid mutation activates exclusive AI Crew Chief ownership. In an active delegated AI Crew Chief run, repeatedly run advance_to_next_decision, inspect state with the read tools, commit_strategy at each pending decision, and continue until the returned race status is FINISHED.",
    inputSchema: emptyInput,
    readOnly: false
  }
];

export function supportsWebMCP(doc = document) {
  return Boolean(doc?.modelContext?.registerTool);
}

export async function registerPitWallWebMCP({ documentRef = document, getSessionId, request, refresh, notify }) {
  if (!supportsWebMCP(documentRef)) {
    notify?.({ ready: false, message: "WebMCP unavailable in this browser." });
    return () => {};
  }

  const controller = new AbortController();
  const registered = [];

  const activeSessionId = () => {
    const sessionId = getSessionId();
    if (!sessionId) {
      throw new Error("No active Pit Wall race session is open in this browser tab.");
    }
    return sessionId;
  };

  const read = async (path) => request(`/races/${activeSessionId()}${path}`);
  const mutate = async (path, options = {}) => {
    const before = await read("/state");
    const payload = await request(`/races/${activeSessionId()}${path}`, options);
    await refresh(activeSessionId());
    documentRef.dispatchEvent(new CustomEvent("pitwall:webmcp-action", { detail: { path, payload } }));
    const after = await read("/state");
    return { before, payload, after, next_action_expected: nextActionExpected({ payload, after, path }) };
  };

  const executors = {
    get_race_state: async () => {
      const state = await read("/state");
      const decision = await read("/decision");
      return { ...state, next_action_expected: nextActionExpected({ payload: decision, after: state }) };
    },
    get_my_car_state: () => read("/my-car"),
    get_field_state: ({ window = 15 } = {}) => read(`/field?window=${clamp(Number(window) || 15, 3, 32)}&debug=false`),
    get_current_decision: async () => {
      const [state, decision] = await Promise.all([read("/state"), read("/decision")]);
      if (decision) {
        return {
          ...decision,
          control: controlSnapshot(state),
          next_action_expected: nextActionExpected({ payload: decision, after: state })
        };
      }
      return {
        decision,
        control: controlSnapshot(state),
        next_action_expected: nextActionExpected({ payload: decision, after: state })
      };
    },
    get_recent_events: async ({ count = 25 } = {}) => {
      const events = await read(`/events?since_cursor=0&limit=160`);
      return {
        events: events.filter(isMeaningfulEvent).slice(-clamp(Number(count) || 25, 1, 80))
      };
    },
    get_decision_history: () => read("/decision-history"),
    commit_strategy: async ({ decision_id, action }) => {
      if (!decision_id || !action) {
        throw new Error("commit_strategy requires decision_id and action.");
      }
      const result = await mutate("/strategy", {
        method: "POST",
        body: JSON.stringify({ decision_id, action, actor: "WEBMCP_AGENT" })
      });
      if (!result.payload.accepted) {
        throw new Error(result.payload.message);
      }
      return result;
    },
    advance_to_next_decision: async () => {
      const result = await mutate("/advance", {
        method: "POST",
        body: JSON.stringify({ actor: "WEBMCP_AGENT" })
      });
      if (result.payload.accepted === false) {
        throw new Error(result.payload.message);
      }
      return result;
    }
  };

  await Promise.all(
    PIT_WALL_WEBMCP_TOOLS.map(async (tool) => {
      await documentRef.modelContext.registerTool(
        {
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          annotations: { readOnlyHint: tool.readOnly },
          execute: async (args = {}) => executors[tool.name](args)
        },
        { signal: controller.signal }
      );
      registered.push(tool.name);
    })
  );

  notify?.({ ready: true, message: `${registered.length} Pit Wall WebMCP tools registered.`, tools: registered });
  return () => controller.abort();
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function isMeaningfulEvent(event) {
  return [
    "CautionStarted",
    "CautionEnded",
    "RestartOccurred",
    "StageEnded",
    "PitStopCompleted",
    "StrategyDecisionRequested",
    "StrategyDecisionCommitted",
    "LeadChanged",
    "DriverRetired",
    "RaceStarted",
    "RaceFinished"
  ].includes(event.event_type);
}

function controlSnapshot(state = {}) {
  return {
    control_mode: state.control_mode,
    current_controller: state.current_controller,
    delegation_status: state.delegation_status,
    objective: state.objective
  };
}

function nextActionExpected({ payload, after = {}, path = "" } = {}) {
  const control = payload?.control ?? controlSnapshot(after);
  const controller = control.current_controller ?? after.current_controller;
  const delegationStatus = control.delegation_status ?? after.delegation_status;
  const raceStatus = after.race_status ?? payload?.status ?? payload?.result?.race_status;
  const hasPendingDecision = Boolean(payload?.decision || payload?.decision_id);

  if (raceStatus === "FINISHED" || payload?.status === "FINISHED") {
    return "Race is FINISHED. Stop autonomous tool execution and summarize the completed race.";
  }
  if (payload?.accepted === false) {
    return `Action was rejected: ${payload.message} Inspect state and resolve ownership or decision context before trying another mutation.`;
  }
  if (control.control_mode === "CO_CREW_CHIEF") {
    if (hasPendingDecision || path === "/advance") {
      return "Co-Crew Chief shared control: inspect this pending decision, commit_strategy once if the user asked you to make this call, then stop unless the user explicitly delegated a bounded stint.";
    }
    return "Co-Crew Chief shared control: return progression to the human by default. Call advance_to_next_decision only when the user explicitly delegated multiple decisions or a bounded stint.";
  }
  if (control.control_mode === "AI_CREW_CHIEF" && delegationStatus === "AWAITING_AGENT") {
    return "AI Crew Chief is READY FOR HANDOFF. Human controls remain available until your first valid WebMCP mutation; if the user asked you to take the pit box, call advance_to_next_decision or commit_strategy as appropriate.";
  }
  if (controller === "WEBMCP_AGENT") {
    if (hasPendingDecision || path === "/advance") {
      return "A strategic decision is pending and you still own the pit box. Inspect get_my_car_state, get_field_state, get_current_decision, and get_recent_events as needed, then commit_strategy with the current decision_id.";
    }
    return "You still own the pit box. Continue autonomously by calling advance_to_next_decision until the next pending decision or FINISHED.";
  }
  if (controller === "NONE") {
    return "AI Crew Chief is READY FOR HANDOFF. Inspect freely; a first valid WebMCP mutation is what activates AI ownership.";
  }
  return "Human control is active. Inspect only unless the user changes control mode or returns the pit box to AI.";
}
