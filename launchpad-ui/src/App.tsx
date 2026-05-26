import { useCallback, useEffect, useState } from "react";
import {
  generateArchitecture,
  getSession,
  isSessionNotFoundError,
  SESSION_ID_STORAGE_KEY,
  startSession,
  submitTurn,
} from "./api";
import { ArchitectureWorkspace } from "./components/ArchitectureWorkspace";
import { ChatPanel } from "./components/ChatPanel";
import { SpecificationPanel } from "./components/SpecificationPanel";
import { WorkflowSteps } from "./components/WorkflowSteps";
import type { ArchitecturePlan, InterviewSession } from "./types";
import "./App.css";

type RightTab = "spec" | "architecture";

export default function App() {
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<RightTab>("spec");
  const [plan, setPlan] = useState<ArchitecturePlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [sessionLost, setSessionLost] = useState(false);
  const [restoringSession, setRestoringSession] = useState(true);

  const resetInterview = useCallback(() => {
    localStorage.removeItem(SESSION_ID_STORAGE_KEY);
    setSession(null);
    setPlan(null);
    setPlanError(null);
    setError(null);
    setSessionLost(false);
    setRightTab("spec");
  }, []);

  const clearStaleSession = useCallback(() => {
    resetInterview();
    setSessionLost(true);
  }, [resetInterview]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("fresh") || params.has("new")) {
      localStorage.removeItem(SESSION_ID_STORAGE_KEY);
      params.delete("fresh");
      params.delete("new");
      const qs = params.toString();
      const next = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`;
      window.history.replaceState(null, "", next);
      setRestoringSession(false);
      return;
    }

    const storedId = localStorage.getItem(SESSION_ID_STORAGE_KEY);
    if (!storedId) {
      setRestoringSession(false);
      return;
    }
    getSession(storedId)
      .then(({ session: s }) => {
        setSession(s);
        if (s.architecture_plan) setPlan(s.architecture_plan);
        setSessionLost(false);
      })
      .catch((e) => {
        if (isSessionNotFoundError(e)) {
          localStorage.removeItem(SESSION_ID_STORAGE_KEY);
          setSessionLost(true);
        }
      })
      .finally(() => setRestoringSession(false));
  }, []);

  useEffect(() => {
    if (session?.id) {
      localStorage.setItem(SESSION_ID_STORAGE_KEY, session.id);
      setSessionLost(false);
    }
  }, [session?.id]);

  const canPlan =
    session?.spec.status === "sufficient" ||
    session?.spec.status === "ready";

  const isArchitectureView = session && rightTab === "architecture";

  useEffect(() => {
    if (session?.architecture_plan) {
      setPlan(session.architecture_plan);
    }
  }, [session?.architecture_plan]);

  useEffect(() => {
    if (session?.spec.status === "ready") {
      setRightTab("architecture");
    }
  }, [session?.spec.status]);

  const handleStart = useCallback(async (problemStatement: string) => {
    resetInterview();
    setLoading(true);
    try {
      const { session: s } = await startSession(problemStatement);
      setSession(s);
      setRightTab("spec");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }, [resetInterview]);

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!session) return;
      setLoading(true);
      setError(null);
      try {
        const { session: s } = await submitTurn(session.id, answer);
        setSession(s);
        if (s.architecture_plan) setPlan(s.architecture_plan);
      } catch (e) {
        if (isSessionNotFoundError(e)) {
          clearStaleSession();
          setError(
            "Session expired (API restarted). Start a new interview below.",
          );
        } else {
          setError(e instanceof Error ? e.message : "Failed to submit answer");
        }
      } finally {
        setLoading(false);
      }
    },
    [session, clearStaleSession],
  );

  const handleGenerateArchitecture = useCallback(
    async (force = false) => {
      if (!session) return;
      setPlanLoading(true);
      setPlanError(null);
      try {
        const { plan: p, session_id } = await generateArchitecture(
          session.id,
          force,
        );
        setPlan(p);
        setSession((prev) =>
          prev && prev.id === session_id
            ? { ...prev, architecture_plan: p }
            : prev,
        );
        setRightTab("architecture");
      } catch (e) {
        if (isSessionNotFoundError(e)) {
          clearStaleSession();
          setPlanError(
            "Session not found on server. Start a new interview, or restore a saved session under data/sessions/ if you have the id.",
          );
        } else {
          setPlanError(
            e instanceof Error ? e.message : "Failed to generate architecture",
          );
        }
      } finally {
        setPlanLoading(false);
      }
    },
    [session, clearStaleSession],
  );

  const workflowStep = !session
    ? "interview"
    : rightTab === "architecture"
      ? "architecture"
      : session.spec.status === "ready" || session.spec.status === "sufficient"
        ? "spec"
        : "interview";

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__row">
          <div className="app-header__brand">
            <span className="app-header__logo" aria-hidden>
              ◆
            </span>
            <div>
              <h1>Affine Agent Launchpad</h1>
              <p>Interview → spec → architecture</p>
            </div>
          </div>
          <div className="app-header__actions">
            {session ? (
              <WorkflowSteps
                current={workflowStep}
                canArchitecture={!!canPlan}
                onGoSpec={() => setRightTab("spec")}
                onGoArchitecture={() => setRightTab("architecture")}
              />
            ) : null}
            {session ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={loading}
                onClick={() => {
                  if (
                    window.confirm(
                      "Start a new interview? Your current session stays saved on the server but will no longer load automatically in this browser.",
                    )
                  ) {
                    resetInterview();
                  }
                }}
              >
                New interview
              </button>
            ) : null}
          </div>
        </div>
      </header>

      {sessionLost && !session ? (
        <p className="app-session-lost" role="status">
          Previous session is no longer on the server. Start a new interview in
          the chat panel. To skip auto-restore on refresh, open{" "}
          <a href="?fresh=1">?fresh=1</a> or clear site data for localhost:5173.
        </p>
      ) : null}
      {restoringSession ? (
        <p className="app-session-lost" role="status">
          Restoring session…
        </p>
      ) : null}

      <main
        className={`app-main ${isArchitectureView ? "app-main--architecture" : ""}`}
      >
        <ChatPanel
          session={session}
          loading={loading}
          error={error}
          onStart={handleStart}
          onAnswer={handleAnswer}
          compact={!!isArchitectureView}
        />

        {session && isArchitectureView ? (
          <ArchitectureWorkspace
            sessionId={session.id}
            plan={plan}
            loading={planLoading}
            error={planError}
            canGenerate={!!canPlan}
            onGenerate={handleGenerateArchitecture}
            onPlanUpdated={(p) => {
              setPlan(p);
              setSession((prev) =>
                prev ? { ...prev, architecture_plan: p } : prev,
              );
            }}
            onBackToSpec={() => setRightTab("spec")}
          />
        ) : session ? (
          <aside className="right-panel">
            <nav className="right-panel__tabs" aria-label="Side panel">
              <button
                type="button"
                className={`right-panel__tab ${rightTab === "spec" ? "right-panel__tab--active" : ""}`}
                onClick={() => setRightTab("spec")}
              >
                Specification
              </button>
              <button
                type="button"
                className={`right-panel__tab ${rightTab === "architecture" ? "right-panel__tab--active" : ""}`}
                onClick={() => setRightTab("architecture")}
                disabled={!canPlan}
              >
                Architecture
                {canPlan ? (
                  <span className="right-panel__tab-dot" aria-hidden />
                ) : null}
              </button>
            </nav>
            {rightTab === "spec" ? (
              <SpecificationPanel spec={session.spec} />
            ) : null}
          </aside>
        ) : (
          <aside className="spec-panel spec-panel--placeholder">
            <h2>Specification</h2>
            <p>
              Start the interview, confirm requirements, then open Architecture
              for a full-width flow diagram.
            </p>
          </aside>
        )}
      </main>
    </div>
  );
}
