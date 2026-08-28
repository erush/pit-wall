import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bug,
  ChevronDown,
  ChevronRight,
  Flag,
  Fuel,
  Gauge,
  History,
  ListOrdered,
  Play,
  Radio,
  RotateCcw,
  Sparkles,
  Timer,
  Trophy,
  Users,
  Wrench
} from "lucide-react";
import "./styles.css";
import { registerPitWallWebMCP } from "./webmcpTools.js";

const API_ROOT = import.meta.env.VITE_PITWALL_API_ROOT ?? "/api/v1/nascar/pit-wall";
const EVENT_KEEPERS = new Set([
  "CautionStarted",
  "CautionEnded",
  "RestartOccurred",
  "StageEnded",
  "PitStopCompleted",
  "CompetitorStrategyCommitted",
  "StrategyDecisionRequested",
  "StrategyDecisionCommitted",
  "LeadChanged",
  "PositionChanged",
  "ControlTransferred",
  "DriverRetired",
  "RaceStarted",
  "RaceFinished"
]);

const TRACK_OPTIONS = [
  { id: "trk_daytona_international_speedway", label: "Daytona", name: "Daytona International Speedway", type: "Superspeedway" },
  { id: "trk_bristol_motor_speedway", label: "Bristol", name: "Bristol Motor Speedway", type: "Short Track" },
  { id: "trk_darlington_raceway", label: "Darlington", name: "Darlington Raceway", type: "Intermediate" },
  { id: "trk_pocono_raceway", label: "Pocono", name: "Pocono Raceway", type: "Intermediate" },
  { id: "trk_watkins_glen_international", label: "Watkins Glen", name: "Watkins Glen International", type: "Road Course" }
];

function App() {
  const [session, setSession] = useState(null);
  const [race, setRace] = useState(null);
  const [car, setCar] = useState(null);
  const [field, setField] = useState(null);
  const [decision, setDecision] = useState(null);
  const [events, setEvents] = useState([]);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [seed, setSeed] = useState("1847");
  const [trackId, setTrackId] = useState(TRACK_OPTIONS[0].id);
  const [controlMode, setControlMode] = useState("HUMAN");
  const [debug, setDebug] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [webmcp, setWebmcp] = useState({ ready: false, message: "WebMCP not registered.", tools: [], lastAction: null });

  async function request(path, options = {}) {
    const response = await fetch(`${API_ROOT}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  async function refresh(sessionId = session?.session_id) {
    if (!sessionId) return;
    const [raceState, myCar, fieldState, currentDecision, recentEvents, decisions, raceResult] = await Promise.all([
      request(`/races/${sessionId}/state`),
      request(`/races/${sessionId}/my-car`),
      request(`/races/${sessionId}/field?window=15&debug=${debug}`),
      request(`/races/${sessionId}/decision`),
      request(`/races/${sessionId}/events?since_cursor=0&limit=160`),
      request(`/races/${sessionId}/decision-history`),
      request(`/races/${sessionId}/result`)
    ]);
    setRace(raceState);
    setCar(myCar);
    setField(fieldState);
    setDecision(currentDecision);
    setEvents(recentEvents.filter((event) => eventRelevant(event, myCar)).slice(-70).reverse());
    setHistory(decisions);
    setResult(raceResult);
  }

  useEffect(() => {
    if (session) refresh();
  }, [debug]);

  useEffect(() => {
    let cleanup = () => {};
    let cancelled = false;
    registerPitWallWebMCP({
      getSessionId: () => session?.session_id,
      request,
      refresh,
      notify: (status) => setWebmcp((current) => ({ ...current, ...status }))
    })
      .then((removeTools) => {
        if (cancelled) {
          removeTools();
        } else {
          cleanup = removeTools;
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setWebmcp((current) => ({ ...current, ready: false, message: err.message }));
        }
      });
    const onAgentAction = (event) => {
      setWebmcp((current) => ({
        ...current,
        lastAction: event.detail?.payload?.decision?.label || event.detail?.payload?.status || "Tool action"
      }));
    };
    document.addEventListener("pitwall:webmcp-action", onAgentAction);
    return () => {
      cancelled = true;
      cleanup();
      document.removeEventListener("pitwall:webmcp-action", onAgentAction);
    };
  }, [session?.session_id, debug]);

  async function createRace(randomize = false) {
    setBusy(true);
    setError("");
    try {
      const selectedSeed = randomize ? Math.floor(1000 + Math.random() * 9000) : Number(seed || 1847);
      const payload = await request("/races", {
        method: "POST",
        body: JSON.stringify({ seed: selectedSeed, control_mode: controlMode, track_id: trackId })
      });
      setSession({ session_id: payload.session_id, seed: payload.seed });
      setSeed(String(payload.seed));
      setRace(payload.race);
      setCar(payload.my_car);
      setField(null);
      setDecision(null);
      setEvents([]);
      setHistory([]);
      setResult(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const payload = await request(`/races/${session.session_id}/advance`, {
        method: "POST",
        body: JSON.stringify({ actor: "HUMAN" })
      });
      if (payload.accepted === false) {
        throw new Error(payload.message);
      }
      if (payload.status === "FINISHED") {
        setResult(payload.result);
        setDecision(null);
      } else {
        setDecision(payload.decision);
      }
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function commit(action) {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const payload = await request(`/races/${session.session_id}/strategy`, {
        method: "POST",
        body: JSON.stringify({ action, actor: "HUMAN" })
      });
      if (!payload.accepted) {
        throw new Error(payload.message);
      }
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function control(action) {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const payload = await request(`/races/${session.session_id}/control`, {
        method: "POST",
        body: JSON.stringify({ action })
      });
      if (!payload.accepted) {
        throw new Error(payload.message);
      }
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!session) {
    return (
      <PreRace
        seed={seed}
        setSeed={setSeed}
        trackId={trackId}
        setTrackId={setTrackId}
        controlMode={controlMode}
        setControlMode={setControlMode}
        busy={busy}
        error={error}
        createRace={createRace}
      />
    );
  }

  if (result) {
    return (
      <PostRace
        result={result}
        events={events}
        history={history}
        restart={() => {
          setSession(null);
          setResult(null);
        }}
      />
    );
  }

  return (
    <RaceScreen
      session={session}
      race={race}
      car={car}
      field={field}
      decision={decision}
      events={events}
      history={history}
      busy={busy}
      error={error}
      debug={debug}
      webmcp={webmcp}
      setDebug={setDebug}
      advance={advance}
      commit={commit}
      control={control}
    />
  );
}

function PreRace({ seed, setSeed, trackId, setTrackId, controlMode, setControlMode, busy, error, createRace }) {
  const selectedTrack = TRACK_OPTIONS.find((track) => track.id === trackId) ?? TRACK_OPTIONS[0];
  return (
    <main className="preRace">
      <section className="prePanel">
        <div className="preMeta">
          <span>Stock-Car Strategy</span>
          <span>{selectedTrack.type}</span>
          <span>{selectedTrack.name}</span>
        </div>
        <div className="preHero">
          <p>Pit Wall</p>
          <h1>You Are The Crew Chief</h1>
          <strong>Race against 31 autonomous pit walls.</strong>
          <span>
            Manage tires, fuel, pit timing, and track position from green flag to checkered flag.
            Call the race yourself, share the pit box with an AI agent, or delegate through Work with ChatGPT.
          </span>
        </div>
        <div className="selectorBlock">
          <p className="label">Choose Your Track</p>
          <div className="trackSelector" aria-label="Track selection">
            {TRACK_OPTIONS.map((track) => (
              <button
                key={track.id}
                className={track.id === trackId ? "selected" : ""}
                onClick={() => setTrackId(track.id)}
                type="button"
              >
                <Flag size={17} />
                <span>{track.label}</span>
                <small>{track.type}</small>
              </button>
            ))}
          </div>
        </div>
        <div className="selectorBlock">
          <p className="label">Who Calls The Race?</p>
        <div className="controlStyles" aria-label="Control styles">
          <ControlStyle
            icon={Radio}
            title="Human"
            text="You make every strategy call."
            selected={controlMode === "HUMAN"}
            onClick={() => setControlMode("HUMAN")}
          />
          <ControlStyle
            icon={Users}
            title="Co-Crew Chief"
            text="Human and WebMCP agent alternate or collaborate."
            selected={controlMode === "CO_CREW_CHIEF"}
            onClick={() => setControlMode("CO_CREW_CHIEF")}
          />
          <ControlStyle
            icon={Sparkles}
            title="AI Crew Chief"
            text="Use Work with ChatGPT to delegate once the race opens."
            selected={controlMode === "AI_CREW_CHIEF"}
            onClick={() => setControlMode("AI_CREW_CHIEF")}
          />
        </div>
        </div>
        <ol className="howToPlay" aria-label="How to play">
          <li>Advance to the next strategic decision.</li>
          <li>Make the call yourself or bring ChatGPT onto the pit box through Work with ChatGPT.</li>
          <li>Beat the autonomous pit walls to the checkered flag.</li>
        </ol>
        <div className="preGrid">
          <div>
            <p className="label">Your Team</p>
            <p className="bigLine">#47</p>
            <p>Riley Vale</p>
            <p>Summit Hollow Racing</p>
          </div>
          <div>
            <p className="label">Starting Position</p>
            <p className="bigLine">Midfield</p>
            <p>Generated from the selected race seed after session creation.</p>
          </div>
          <div>
            <p className="label">Debug Seed</p>
            <input value={seed} onChange={(event) => setSeed(event.target.value)} inputMode="numeric" />
            <button className="secondary" onClick={() => createRace(true)} disabled={busy}>
              <RotateCcw size={16} /> Random
            </button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="primary start" onClick={() => createRace(false)} disabled={busy}>
          <Play size={18} /> START RACE
        </button>
      </section>
    </main>
  );
}

function ControlStyle({ icon: Icon, title, text, selected, onClick }) {
  return (
    <button className={`controlStyle ${selected ? "selected" : ""}`} onClick={onClick} type="button">
      <Icon size={18} />
      <strong>{title}</strong>
      <p>{text}</p>
    </button>
  );
}

function RaceScreen({ session, race, car, field, decision, events, history, busy, error, debug, webmcp, setDebug, advance, commit, control }) {
  const delta = car ? car.starting_position - car.position : 0;
  const pace = formatPace(car?.recent_run?.last_5_lap_relative_pace);
  const racePhase = dominantRacePhase(race);
  const humanCanAct = canHumanMutate(race);

  return (
    <main className="raceShell">
      <header className="raceHeader">
        <div>
          <p className="label">Pit Wall</p>
          <h1>{race?.track_name ?? "Pit Wall"}</h1>
          <p className="trackSubhead">
            {race?.track_type ?? "Track"} | {race?.track_length_miles ?? "-"} mi | {race?.total_laps ?? 0} laps
          </p>
        </div>
        <div className="headerStrip">
          <WebMCPStatus status={webmcp} history={history} race={race} />
          <Stat icon={Flag} label="Lap" value={`${race?.lap ?? 0}/${race?.total_laps ?? 200}`} />
          <Stat icon={Timer} label="Stage" value={race?.stage ?? 1} />
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="raceCommand">
        <div className={`positionScore ${delta > 0 ? "positive" : delta < 0 ? "negative" : ""}`}>
          <span>Current Position</span>
          <strong>P{car?.position ?? "-"}</strong>
          <p>{movementText(delta)} FROM START</p>
        </div>
        <div className={`phaseScore ${racePhase.tone}`}>
          <span>Race Status</span>
          <strong>{racePhase.label}</strong>
          <p>{racePhase.detail}</p>
        </div>
      </section>

      <ControlStatePanel race={race} decision={decision} busy={busy} control={control} />

      <section className="workstation">
        <section className="carPanel">
          <div className="panelTitle"><Gauge size={17} /> Your Car</div>
          <div className="carHero">
            <span>#{car?.car_number}</span>
            <div>
              <h2>{car?.driver_name}</h2>
              <p>{car?.team_name}</p>
            </div>
          </div>
          <div className="metricGrid">
            <Metric label="Start" value={`P${car?.starting_position ?? "-"}`} />
            <Metric label="Change" value={movementText(delta)} tone={delta > 0 ? "positive" : delta < 0 ? "negative" : ""} />
            <Metric label="Tire Age" value={`${car?.tire_age ?? 0} laps`} />
            <Metric label="Fuel" value={`${fmt(car?.estimated_fuel_laps)} laps`} />
            <Metric label="Pit Stops" value={car?.pit_stops ?? 0} />
            <Metric label="Recent Pace" value={pace} wide />
            <Metric label="Mode" value={cleanAction(car?.pace_mode ?? "NORMAL_PACE")} wide />
          </div>
          <LastCall history={history} car={car} events={events} />
          <DecisionHistory history={history} />
        </section>

        <section className="orderPanel">
          <div className="panelTitle"><ListOrdered size={17} /> Running Order</div>
          <div className="runningOrder">
            {(field?.running_order ?? []).map((row) => (
              <div className={orderRowClass(row, car)} key={row.car_number}>
                <span className="pos">P{row.position}</span>
                <span className="num">#{row.car_number}</span>
                <span className="driver">{row.driver_name}</span>
                <span>{row.laps_down ? `${row.laps_down}L` : `+${row.gap_to_leader.toFixed(1)}`}</span>
                <span>{row.last_pit_lap ? `Pit L${row.last_pit_lap}` : "No stop"}</span>
                <span>{row.tire_age} lap tires</span>
                {debug && <span className="debugTag">{row.strategy_archetype}</span>}
              </div>
            ))}
          </div>
        </section>

        <section className="strategyPanel">
          <div className="panelTitle"><Wrench size={17} /> Strategy</div>
          <FieldStrategy fieldStrategy={field?.field_strategy} />
          {decision ? (
            <>
              <div className="decisionHead">
                <p className="label">Decision Lap {decision.lap}</p>
                <h2>{decision.reason}</h2>
                <p>{decision.race_context} | P{decision.position} | {decision.laps_to_race_end} laps remaining</p>
              </div>
              <div className="contextGrid">
                <Metric label="Fuel" value={`${fmt(decision.estimated_fuel_laps)} laps`} />
                <Metric label="Tires" value={`${decision.tire_age} laps`} />
                <Metric label="Stage Left" value={decision.laps_to_stage_end ?? "Final"} />
                <Metric label="Pace" value={formatPace(decision.recent_run?.last_5_lap_relative_pace)} />
              </div>
              <div className="summaryLines">
                {decision.field_strategy_summary.map((line) => <p key={line}>{line}</p>)}
              </div>
              {humanCanAct ? (
                <div className="actions">
                  {decision.available_actions.filter((action) => action.eligible).map((action) => (
                    <button key={action.action} onClick={() => commit(action.action)} disabled={busy}>
                      <ChevronRight size={17} />
                      <span>{action.label}</span>
                      <small>{action.short_description}</small>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="handoffNotice">
                  <Sparkles size={18} />
                  <strong>{controlLockTitle(race)}</strong>
                  <p>{controlLockDetail(race)}</p>
                </div>
              )}
            </>
          ) : (
            <div className="standby">
              <p className="label">Race Control</p>
              <h2>Awaiting next meaningful call</h2>
              <p>Advance through routine laps until fuel, tires, stage, caution, or strategy split creates a crew-chief decision.</p>
            </div>
          )}
          <div className="advanceBar">
            <button className="primary" onClick={advance} disabled={busy || Boolean(decision) || !humanCanAct}>
              <Play size={17} /> Next Decision
            </button>
            <button className="secondary" onClick={advance} disabled={busy || Boolean(decision) || !humanCanAct}>5x</button>
            <button className="secondary" onClick={advance} disabled={busy || Boolean(decision) || !humanCanAct}>20x</button>
            <label className="debugSwitch">
              <input type="checkbox" checked={debug} onChange={(event) => setDebug(event.target.checked)} />
              <Bug size={15} /> Debug
            </label>
          </div>
        </section>

        <section className="timelinePanel">
          <div className="panelTitle"><History size={17} /> Race Timeline</div>
          <StrategicTimeline events={events} history={history} />
          <div className="eventFeed">
            {events.map((event) => (
              <div className="eventRow" key={`${event.cursor}-${event.event_type}`}>
                <span>L{event.lap}</span>
                <p>{eventText(event)}</p>
              </div>
            ))}
          </div>
        </section>
      </section>

      <footer className="sessionBar">
        <span>Session {session.session_id}</span>
        <span>{race?.track_name}</span>
        {debug && <span>Seed {session.seed}</span>}
      </footer>
    </main>
  );
}

function PostRace({ result, events, history, restart }) {
  const [showAllCalls, setShowAllCalls] = useState(false);
  const recap = useMemo(() => strategyRecap(history, result, events), [history, result, events]);
  const humanCount = result.strategy_decisions.filter((entry) => actorLabel(entry.actor) === "HUMAN").length;
  const aiCount = result.strategy_decisions.filter((entry) => actorLabel(entry.actor) === "AI CREW CHIEF").length;
  const finishMovement = finishMovementLabel(result.positions_changed);
  const allCalls = [...result.strategy_decisions].sort((a, b) => a.lap - b.lap || a.decision_id.localeCompare(b.decision_id));
  const major = majorEvents(result, events, allCalls);
  return (
    <main className="postRace">
      <section className="finishHeader">
        <div>
          <p className="label">Race Complete</p>
          <h1>CHECKERED FLAG</h1>
          <div className="finishLine">
            <span>START <strong>P{result.user_start_position}</strong></span>
            <span>FINISH <strong>P{result.user_finish_position}</strong></span>
            <span>{finishMovement.label} <strong>{finishMovement.value}</strong></span>
          </div>
        </div>
        <Trophy size={52} />
      </section>
      <section className="finishGrid">
        <Metric label="Winner" value={`#${result.winner_car_number} ${result.winner_driver_name}`} wide />
        <Metric label="Track" value={result.track_name} wide />
        <Metric label="Race Mode" value={controlModeLabel(result.control_mode)} wide />
        <Metric label="Best Position" value={result.user_best_position ? `P${result.user_best_position}` : "n/a"} />
        <Metric label="Pit Stops" value={result.pit_stops} />
        <Metric label="Total Calls" value={result.strategy_decisions.length} />
        <Metric label="Strategy Calls" value={`Human ${humanCount} / AI Crew Chief ${aiCount}`} wide />
        <Metric label="Lead Changes" value={result.lead_changes} />
        <Metric label="Cautions" value={result.caution_count} />
      </section>
      <section className="recap">
        <h2>Strategy Story</h2>
        <div className="storyGrid">
          <StoryBlock title="Biggest Gain" entry={recap.biggestGain} />
          <StoryBlock title="Toughest Sequence" entry={recap.toughestSequence} />
        </div>
        <h2>Final Calls</h2>
        <div className="decisionList">
          {recap.finalCalls.map((entry) => (
            <div key={entry.decision_id}>
              <span>L{entry.lap}</span>
              <strong>{actorLabel(entry.actor)}</strong>
              <p>{actionName(entry)}</p>
              <small>P{entry.position_before} to P{entry.position_after_commit}</small>
            </div>
          ))}
        </div>
        {allCalls.length > 5 && (
          <button className="inlineExpand" type="button" onClick={() => setShowAllCalls((current) => !current)}>
            {showAllCalls ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            {showAllCalls ? "Hide Full Call History" : `View All ${allCalls.length} Calls`}
          </button>
        )}
        {showAllCalls && (
          <div className="decisionList allCalls" aria-label="Full strategy call history">
            {allCalls.map((entry) => (
              <div key={entry.decision_id}>
                <span>L{entry.lap}</span>
                <strong>{actorLabel(entry.actor)}</strong>
                <p>{actionName(entry)}</p>
                <small>P{entry.position_before} to P{entry.position_after_commit}</small>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="recap">
        <h2>Major Events</h2>
        <div className="eventFeed">
          {major.map((event) => (
            <div className="eventRow" key={`${event.cursor}-${event.event_type}`}>
              <span>L{event.lap}</span>
              <p>{eventText(event)}</p>
            </div>
          ))}
        </div>
      </section>
      <button className="primary start" onClick={restart}><RotateCcw size={17} /> New Race</button>
    </main>
  );
}

function ControlStatePanel({ race, decision, busy, control }) {
  if (!race) return null;
  const isAiMode = race.control_mode === "AI_CREW_CHIEF";
  const isCoCrewMode = race.control_mode === "CO_CREW_CHIEF";
  const label = controlModeLabel(race.control_mode);
  const status = delegationLabel(race.delegation_status, race.current_controller);
  return (
    <section className={`controlStatePanel ${isAiMode ? "aiMode" : ""}`}>
      <div>
        <p className="label">{isCoCrewMode ? "Co-Crew Chief" : isAiMode ? "AI Crew Chief" : "Pit Box Control"}</p>
        <h2>{label}</h2>
        <p>{controlStateText(race)}</p>
      </div>
      <div className="controlStateActions">
        <span>{status}</span>
        {isAiMode && race.current_controller === "WEBMCP_AGENT" && race.delegation_status === "ACTIVE" && (
          <button className="secondary" onClick={() => control("TAKE_CONTROL")} disabled={busy}>
            <Users size={17} /> Take Control
          </button>
        )}
        {isAiMode && race.current_controller === "HUMAN" && race.delegation_status === "PAUSED" && (
          <button className="primary" onClick={() => control("RETURN_TO_AI")} disabled={busy}>
            <Sparkles size={17} /> Return To AI
          </button>
        )}
      </div>
      {isCoCrewMode && decision && (
        <div className="handoffPrompt">
          <span>Shared Pit Wall</span>
          <strong>Make this call yourself, or use Work with ChatGPT: "Take this strategy call for me."</strong>
        </div>
      )}
      {isAiMode && race.delegation_status !== "ACTIVE" && (
        <div className="handoffPrompt">
          <span>Use Work with ChatGPT</span>
          <strong>"Take the pit box and call this race through the checkered flag."</strong>
        </div>
      )}
    </section>
  );
}

function WebMCPStatus({ status, history = [], race }) {
  const active = Boolean(
    race?.delegation_status === "ACTIVE" ||
    status.lastAction ||
    history.some((entry) => entry.actor === "WEBMCP_AGENT")
  );
  const label = active ? "ACTIVE" : status.ready ? "READY" : "SITE TOOLS UNAVAILABLE";
  return (
    <div className={`webmcpStatus ${status.ready ? "ready" : ""} ${active ? "active" : ""}`} title={status.message}>
      <Sparkles size={16} />
      <span>AI Crew Chief</span>
      <strong>{label}</strong>
      {status.lastAction && <small>AI call: {status.lastAction}</small>}
    </div>
  );
}

function LastCall({ history, car, events }) {
  const last = history.at(-1);
  if (!last || !car) return null;
  const net = last.position_before - car.position;
  const immediate = last.position_before - last.position_after_commit;
  const tireDelta = car.tire_age - last.tire_age_before;
  const cautionFollowed = events.some((event) => event.event_type === "CautionStarted" && event.lap > last.lap);
  return (
    <div className="consequence">
      <p className="label">{actorLabel(last.actor)} Call - Lap {last.lap}</p>
      <strong>{actionName(last)}</strong>
      <div className="evidenceGrid">
        <span>Before call <strong>P{last.position_before}</strong></span>
        <span>Initial result <strong>P{last.position_after_commit}</strong></span>
        <span>Position change <strong>{signed(immediate)}</strong></span>
        <span>Tire delta <strong>{signed(tireDelta)} laps</strong></span>
      </div>
      <p>{cautionFollowed ? "CAUTION FOLLOWED" : `Current net ${signed(net)} positions`}</p>
    </div>
  );
}

function DecisionHistory({ history }) {
  if (!history.length) return null;
  return (
    <div className="decisionHistoryMini">
      <p className="label">User-Team Call History</p>
      {history.slice(-5).reverse().map((entry) => (
        <div key={entry.decision_id}>
          <span>L{entry.lap}</span>
          <strong>{actorLabel(entry.actor)}</strong>
          <p>{actionName(entry)}</p>
        </div>
      ))}
    </div>
  );
}

function FieldStrategy({ fieldStrategy }) {
  if (!fieldStrategy) return null;
  return (
    <section className="fieldStrategy">
      <div>
        <p className="label">Field Strategy</p>
        <strong>{fieldStrategy.autonomous_pit_walls} Autonomous Pit Walls</strong>
      </div>
      <div className={`splitPill ${fieldStrategy.split_level.toLowerCase()}`} title={fieldStrategy.split_rule}>
        Strategy Split {fieldStrategy.split_level}
      </div>
      <div className="strategyCounts">
        {fieldStrategy.action_counts.length ? (
          fieldStrategy.action_counts.map((entry) => (
            <div key={entry.action}>
              <span>{entry.label}</span>
              <strong>{entry.count}</strong>
            </div>
          ))
        ) : (
          <p>No recorded opponent calls in this window.</p>
        )}
        {fieldStrategy.unrecorded_count > 0 && (
          <div>
            <span>Not Yet Recorded</span>
            <strong>{fieldStrategy.unrecorded_count}</strong>
          </div>
        )}
      </div>
      <small>{fieldStrategy.note}</small>
    </section>
  );
}

function StrategicTimeline({ events, history }) {
  const markers = timelineMarkers(events, history);
  if (!markers.length) return <p className="timelineEmpty">No strategic markers yet.</p>;
  return (
    <div className="strategicTimeline" aria-label="Strategic race timeline">
      {markers.map((marker) => (
        <div className={`timelineMarker ${marker.type}`} key={marker.key} title={marker.label}>
          <span>L{marker.lap}</span>
          <strong>{marker.short}</strong>
        </div>
      ))}
    </div>
  );
}

function StoryBlock({ title, entry }) {
  return (
    <div className="storyBlock">
      <p className="label">{title}</p>
      {entry ? (
        <>
          <strong>{actorLabel(entry.actor)}</strong>
          <span>Lap {entry.lap} | {actionName(entry)}</span>
          <span>P{entry.position_before} to P{entry.position_after_commit}</span>
          {entry.cautionFollowed && <span>CAUTION FOLLOWED</span>}
        </>
      ) : (
        <span>No user-team calls recorded.</span>
      )}
    </div>
  );
}

function Stat({ icon: Icon, label, value, urgent = false }) {
  return (
    <div className={`stat ${urgent ? "urgent" : ""}`}>
      <Icon size={16} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value, wide = false, tone = "" }) {
  return (
    <div className={`metric ${wide ? "wide" : ""} ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function eventText(event) {
  const car = event.car_number ? `#${event.car_number} ` : "";
  if (event.event_type === "StrategyHistoryCall") {
    return `${actorLabel(event.actor)} chose ${cleanAction(event.message)}`;
  }
  if (event.event_type === "ControlTransferred") return event.message;
  if (event.event_type === "PitStopCompleted") return `${car}pits: ${cleanAction(event.message)}`;
  if (event.event_type === "StrategyDecisionCommitted") {
    return `${actorLabel(event.actor)} chose ${cleanAction(event.message)}`;
  }
  if (event.event_type === "PositionChanged") return `Your car moved ${event.message}`;
  if (event.event_type === "StrategyDecisionRequested") return `Crew-chief call requested: ${event.message}`;
  if (event.event_type === "LeadChanged") return `Lead change: ${car}${event.driver_name ?? ""}`;
  return `${car}${event.message}`;
}

function strategyRecap(history, result, events) {
  if (!history.length) {
    return { biggestGain: null, toughestSequence: null, finalCalls: [] };
  }
  const withEvidence = history.map((entry, index) => ({
    ...entry,
    cautionFollowed: cautionBetweenCalls(entry, history[index + 1], events)
  }));
  const biggestGain = [...withEvidence].sort((a, b) => immediateDelta(b) - immediateDelta(a))[0];
  const toughestSequence = [...withEvidence].sort((a, b) => immediateDelta(a) - immediateDelta(b))[0];
  return {
    biggestGain,
    toughestSequence,
    finalCalls: withEvidence.slice(-5).reverse()
  };
}

function majorEvents(result, events, calls) {
  const byKey = new Map();
  const add = (event) => byKey.set(`${event.event_type}-${event.lap}-${event.message}-${event.actor ?? ""}`, event);
  if (!events.some((event) => event.event_type === "RaceStarted")) {
    add({
      cursor: "synthetic-start",
      event_type: "RaceStarted",
      lap: 0,
      message: `${result.track_name} started.`
    });
  }
  events.filter((event) => event.event_type !== "StrategyDecisionCommitted").forEach(add);
  calls.forEach((entry) => {
    add({
      cursor: `call-${entry.decision_id}`,
      event_type: "StrategyHistoryCall",
      lap: entry.lap,
      message: entry.action,
      actor: entry.actor
    });
  });
  if (!events.some((event) => event.event_type === "RaceFinished")) {
    const finalLap = Math.max(0, ...events.map((event) => event.lap), ...calls.map((entry) => entry.lap));
    add({
      cursor: "synthetic-finish",
      event_type: "RaceFinished",
      lap: finalLap,
      message: `Race finished. Winner #${result.winner_car_number} ${result.winner_driver_name}.`
    });
  }
  const sorted = [...byKey.values()]
    .filter((event) => majorEventType(event.event_type))
    .sort((a, b) => a.lap - b.lap || majorEventPriority(a.event_type) - majorEventPriority(b.event_type));
  if (sorted.length <= 24) return sorted;
  const start = sorted.find((event) => event.event_type === "RaceStarted");
  const tail = sorted.filter((event) => event !== start).slice(-23);
  return start ? [start, ...tail] : tail;
}

function majorEventType(type) {
  return [
    "RaceStarted",
    "CautionStarted",
    "CautionEnded",
    "RestartOccurred",
    "StageEnded",
    "PitStopCompleted",
    "StrategyDecisionCommitted",
    "StrategyHistoryCall",
    "LeadChanged",
    "PositionChanged",
    "ControlTransferred",
    "DriverRetired",
    "RaceFinished"
  ].includes(type);
}

function majorEventPriority(type) {
  const priority = {
    RaceStarted: 0,
    CautionStarted: 1,
    StageEnded: 2,
    CautionEnded: 3,
    RestartOccurred: 4,
    PitStopCompleted: 5,
    StrategyDecisionCommitted: 6,
    StrategyHistoryCall: 6,
    LeadChanged: 7,
    PositionChanged: 8,
    ControlTransferred: 9,
    DriverRetired: 10,
    RaceFinished: 11
  };
  return priority[type] ?? 99;
}

function immediateDelta(entry) {
  return entry.position_before - entry.position_after_commit;
}

function fmt(value) {
  return typeof value === "number" ? value.toFixed(1) : "-";
}

function signed(value) {
  if (typeof value !== "number") return value;
  return value > 0 ? `+${value}` : String(value);
}

function finishMovementLabel(value) {
  if (value > 0) return { label: "GAINED", value: signed(value) };
  if (value < 0) return { label: "LOST", value: String(Math.abs(value)) };
  return { label: "CHANGE", value: "EVEN" };
}

function movementText(value) {
  if (typeof value !== "number") return value;
  if (value > 0) return `↑${value}`;
  if (value < 0) return `↓${Math.abs(value)}`;
  return "EVEN";
}

function cleanAction(value) {
  return String(value).replace("auto:", "").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function actorLabel(actor) {
  if (actor === "AUTO_POLICY") return "AUTO POLICY";
  if (actor === "WEBMCP_AGENT") return "AI CREW CHIEF";
  return "HUMAN";
}

function actionName(entry) {
  return cleanAction(entry?.action ?? entry?.label).toUpperCase();
}

function cautionBetweenCalls(entry, nextEntry, events) {
  const endLap = nextEntry?.lap ?? Number.POSITIVE_INFINITY;
  return events.some((event) => event.event_type === "CautionStarted" && event.lap > entry.lap && event.lap < endLap);
}

function eventRelevant(event, car) {
  if (!EVENT_KEEPERS.has(event.event_type)) return false;
  if (event.event_type === "CompetitorStrategyCommitted") return false;
  if (event.event_type === "StrategyDecisionRequested") return false;
  if (event.event_type === "PitStopCompleted") return event.car_number === car?.car_number;
  if (event.event_type === "PositionChanged") return event.car_number === car?.car_number && majorPositionChange(event);
  if (event.event_type === "LeadChanged") return event.lap % 10 === 0 || event.car_number === car?.car_number;
  return true;
}

function majorPositionChange(event) {
  const match = String(event.message).match(/P(\d+)\s+to\s+P(\d+)/i);
  if (!match) return false;
  const from = Number(match[1]);
  const to = Number(match[2]);
  return from === 1 || to === 1 || Math.abs(from - to) >= 3;
}

function canHumanMutate(race) {
  if (!race) return false;
  if (race.control_mode === "HUMAN" || race.control_mode === "CO_CREW_CHIEF") return true;
  return !(race.current_controller === "WEBMCP_AGENT" && race.delegation_status === "ACTIVE");
}

function controlModeLabel(mode) {
  if (mode === "AI_CREW_CHIEF") return "AI Crew Chief";
  if (mode === "CO_CREW_CHIEF") return "Co-Crew Chief";
  return "Human";
}

function delegationLabel(status, controller) {
  if (status === "ACTIVE") return "AI ACTIVE";
  if (status === "AWAITING_AGENT") return "READY FOR HANDOFF";
  if (status === "PAUSED") return "HUMAN TAKEOVER";
  if (status === "SHARED") return "SHARED PIT WALL";
  if (controller === "WEBMCP_AGENT") return "AI CREW CHIEF";
  return "HUMAN CONTROL";
}

function controlStateText(race) {
  if (race.control_mode === "CO_CREW_CHIEF") {
    return "Shared pit wall. Make the call yourself, or use Work with ChatGPT for one pending decision.";
  }
  if (race.control_mode === "AI_CREW_CHIEF" && race.delegation_status === "AWAITING_AGENT") {
    return "Ready for handoff. Human controls remain available until the first WebMCP agent mutation.";
  }
  if (race.control_mode === "AI_CREW_CHIEF" && race.current_controller === "WEBMCP_AGENT" && race.delegation_status === "ACTIVE") {
    return "ChatGPT is calling the race through Site Tools.";
  }
  if (race.control_mode === "AI_CREW_CHIEF") {
    return "Human control is temporarily active. Return the pit box when you want the AI Crew Chief to continue.";
  }
  return "You own all race calls. WebMCP tools can inspect the race but cannot mutate it.";
}

function controlLockTitle(race) {
  if (race?.current_controller === "WEBMCP_AGENT" && race?.delegation_status === "ACTIVE") return "AI Crew Chief owns this call";
  return "Ready for handoff";
}

function controlLockDetail(race) {
  if (race?.current_controller === "WEBMCP_AGENT" && race?.delegation_status === "ACTIVE") {
    return "Take control before making manual strategy or advance calls.";
  }
  return "Use Work with ChatGPT when you want ChatGPT to take the pit box.";
}

function orderRowClass(row, car) {
  const classes = ["orderRow"];
  if (row.position === 1) classes.push("leader");
  if (row.car_number === car?.car_number) classes.push("you");
  if (car && Math.abs(row.position - car.position) === 1) classes.push("nearby");
  return classes.join(" ");
}

function timelineMarkers(events, history) {
  const eventMarkers = events
    .filter((event) => ["CautionStarted", "StageEnded", "PitStopCompleted", "RaceFinished"].includes(event.event_type))
    .map((event) => ({
      key: `${event.cursor}-${event.event_type}`,
      lap: event.lap,
      type: markerType(event),
      short: markerShort(event),
      label: eventText(event)
    }));
  const callMarkers = history.map((entry) => ({
    key: entry.decision_id,
    lap: entry.lap,
    type: entry.actor === "WEBMCP_AGENT" ? "ai" : "human",
    short: entry.actor === "WEBMCP_AGENT" ? "AI" : "HUMAN",
    label: `${actorLabel(entry.actor)} ${actionName(entry)}`
  }));
  return [...eventMarkers, ...callMarkers].sort((a, b) => a.lap - b.lap || a.short.localeCompare(b.short)).slice(-24);
}

function markerType(event) {
  if (event.event_type === "CautionStarted") return "caution";
  if (event.event_type === "StageEnded") return "stage";
  if (event.event_type === "PitStopCompleted") return "pit";
  if (event.event_type === "RaceFinished") return "finish";
  return "event";
}

function markerShort(event) {
  if (event.event_type === "CautionStarted") return "CAUTION";
  if (event.event_type === "StageEnded") return "STAGE";
  if (event.event_type === "PitStopCompleted") return "PIT";
  if (event.event_type === "RaceFinished") return "CHECKER";
  return "EVENT";
}

function dominantRacePhase(race) {
  const status = race?.race_status ?? "PRE_RACE";
  const caution = race?.caution_status ?? "NONE";
  if ((race?.lap ?? 0) === 0 && status === "PRE_RACE") {
    return { label: "PRE-RACE", detail: "Ready to race", tone: "" };
  }
  if (status === "FINISHED" || status === "CHECKERED") {
    return { label: "CHECKERED", detail: "Race complete", tone: "checkered" };
  }
  if (status === "STAGE_BREAK" || caution === "STAGE_BREAK") {
    return { label: "STAGE BREAK", detail: `Stage ${race?.stage ?? "-"} reset window`, tone: "stage" };
  }
  if (caution !== "NONE" || status === "CAUTION") {
    return { label: "CAUTION", detail: "Field controlled under yellow", tone: "caution" };
  }
  if (status === "GREEN") {
    return { label: "GREEN", detail: "Race is live", tone: "green" };
  }
  return { label: cleanAction(status), detail: "Awaiting race control", tone: "" };
}

function formatPace(value) {
  if (value === null || value === undefined) return "n/a";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)} sec`;
}

createRoot(document.getElementById("root")).render(<App />);
