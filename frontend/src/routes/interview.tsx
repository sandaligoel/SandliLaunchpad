import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { ChatPanel } from "@/components/launchpad/ChatPanel";
import {
  checkAffineHealth,
  getSession,
  isSessionNotFoundError,
  listSessions,
  startSession,
  submitTurn,
  type SessionSummary,
} from "@/api/affine/client";
import {
  preserveSessionBeforeNewInterviewAsync,
  registerLaunchpadWorkflowPlaceholder,
} from "@/api/affine/builderStorage";
import {
  consumeFreshUrlFlag,
  getInterviewSessionIdFromUrl,
  syncInterviewSessionToUrl,
} from "@/api/affine/sessionStorage";
import type { InterviewSession } from "@/api/affine/types";
import { AFFINE_DEV_UI_URL, AFFINE_START_CMD } from "@/config/affineDev";

type InterviewSearch = {
  fresh?: string;
  sessionId?: string;
  view?: "chat";
};

export const Route = createFileRoute("/interview")({
  validateSearch: (search: Record<string, unknown>): InterviewSearch => ({
    fresh: typeof search.fresh === "string" ? search.fresh : undefined,
    sessionId:
      typeof search.sessionId === "string" ? search.sessionId : undefined,
    view: search.view === "chat" ? "chat" : undefined,
  }),
  head: () => ({
    meta: [{ title: "Launchpad Chat — AgentForge | Affine" }],
  }),
  component: InterviewPage,
});

function InterviewPage() {
  const navigate = useNavigate();
  const { sessionId: urlSessionId, view } = Route.useSearch();
  const showChatHistory = view === "chat";
  const openBuilderAfterReady = useRef(false);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [storageHint, setStorageHint] = useState<string | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);
  const [problem, setProblem] = useState("");

  const applyHealth = useCallback((health: Awaited<ReturnType<typeof checkAffineHealth>>) => {
    setApiOk(true);
    const st = health.storage;
    if (st?.backend === "azure_blob" && st.reachable) {
      const n = st.session_blob_count ?? 0;
      setStorageHint(
        `Connected to Azure storage (${st.account}/${st.container}) — ${n} saved chat(s).`,
      );
    } else if (st?.backend === "azure_blob") {
      setStorageHint(
        "Azure Blob is configured but not reachable — check backend/.env credentials.",
      );
    } else {
      setStorageHint(
        "Using local disk only. Add AZURE_STORAGE_* to backend/.env for Azure persistence.",
      );
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const probe = () => {
      checkAffineHealth()
        .then((health) => {
          if (!cancelled) applyHealth(health);
        })
        .catch(() => {
          if (!cancelled) setApiOk(false);
        });
    };
    probe();
    const interval = window.setInterval(probe, 20_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [applyHealth]);

  useEffect(() => {
    if (apiOk !== true || session) return;
    listSessions()
      .then(setRecentSessions)
      .catch(() => setRecentSessions([]));
  }, [apiOk, session]);

  const resumeSession = useCallback((sessionId: string) => {
    setRestoring(true);
    setError(null);
    syncInterviewSessionToUrl(sessionId);
    getSession(sessionId)
      .then(({ session: s }) => {
        setApiOk(true);
        setSession(s);
      })
      .catch((e) => {
        if (isSessionNotFoundError(e)) syncInterviewSessionToUrl(null);
        setError(e instanceof Error ? e.message : "Could not load session");
      })
      .finally(() => setRestoring(false));
  }, []);

  useEffect(() => {
    if (consumeFreshUrlFlag()) {
      setRestoring(false);
      return;
    }
    const storedId = urlSessionId ?? getInterviewSessionIdFromUrl();
    if (!storedId) {
      setRestoring(false);
      return;
    }
    syncInterviewSessionToUrl(storedId);
    getSession(storedId)
      .then(({ session: s }) => {
        setApiOk(true);
        setSession(s);
      })
      .catch((e) => {
        if (isSessionNotFoundError(e)) {
          syncInterviewSessionToUrl(null);
        } else {
          setError(
            e instanceof Error
              ? `Could not restore previous session: ${e.message}`
              : "Could not restore previous session",
          );
        }
      })
      .finally(() => setRestoring(false));
  }, [urlSessionId]);

  useEffect(() => {
    if (session?.id) syncInterviewSessionToUrl(session.id);
  }, [session?.id]);

  useEffect(() => {
    if (showChatHistory) return;
    if (!openBuilderAfterReady.current) return;
    if (session?.spec.status === "ready" && session.id) {
      openBuilderAfterReady.current = false;
      registerLaunchpadWorkflowPlaceholder(
        session.id,
        session.spec.problem_statement,
      );
      navigate({
        to: "/builder",
        search: { sessionId: session.id },
      });
    }
  }, [session?.spec.status, session?.id, navigate, showChatHistory]);

  const handleStart = useCallback(
    async (text: string) => {
      await preserveSessionBeforeNewInterviewAsync(
        session?.id ?? getInterviewSessionIdFromUrl(),
        session?.spec.problem_statement,
      );
      syncInterviewSessionToUrl(null);
      setLoading(true);
      setError(null);
      try {
        const { session: s } = await startSession(text);
        setApiOk(true);
        if (s.spec.status === "ready") openBuilderAfterReady.current = true;
        setSession(s);
        syncInterviewSessionToUrl(s.id);
        setProblem("");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to start session");
      } finally {
        setLoading(false);
      }
    },
    [session?.id, session?.spec.problem_statement],
  );

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!session) return;
      setLoading(true);
      setError(null);
      try {
        const { session: s } = await submitTurn(session.id, answer);
        setApiOk(true);
        if (s.spec.status === "ready") openBuilderAfterReady.current = true;
        setSession(s);
      } catch (e) {
        if (isSessionNotFoundError(e)) {
          syncInterviewSessionToUrl(null);
          setSession(null);
          setError("Session expired. Start a new chat.");
        } else {
          setError(e instanceof Error ? e.message : "Failed to submit answer");
        }
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  const canPlan = session?.spec.status === "ready";

  return (
    <AppShell>
      <Topbar
        title="Agent Launchpad"
        subtitle="Structured chat"
        actions={
          session ? (
            <div className="flex items-center gap-2">
              {canPlan ? (
                <Button variant="outline" size="sm" asChild>
                  <Link to="/builder" search={{ sessionId: session.id }}>
                    Workflow builder
                  </Link>
                </Button>
              ) : null}
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  if (!window.confirm("Start a new chat?")) return;
                  setLoading(true);
                  setError(null);
                  try {
                    await preserveSessionBeforeNewInterviewAsync(
                      session.id,
                      session.spec.problem_statement,
                    );
                  } catch (e) {
                    // Best-effort preserve only; user should still be able to start fresh.
                    setError(
                      e instanceof Error
                        ? `Previous chat could not be preserved: ${e.message}`
                        : "Previous chat could not be preserved",
                    );
                  } finally {
                    syncInterviewSessionToUrl(null);
                    setSession(null);
                    setProblem("");
                    setLoading(false);
                  }
                }}
              >
                New chat
              </Button>
            </div>
          ) : null
        }
      />

      <div className="launchpad-interview-page flex-1 min-h-0 flex flex-col">
        {apiOk === false && !session ? (
          <p className="text-sm text-destructive m-4 rounded-md border border-destructive/30 bg-destructive/5 p-3">
            Cannot reach AFFINE API. Run{" "}
            <code className="text-xs">{AFFINE_START_CMD}</code>, then{" "}
            <code className="text-xs">./scripts/sync-dev-env.sh</code> and restart{" "}
            <code className="text-xs">npm run dev</code>.{" "}
            <Link to="/interview" search={{ fresh: "1" }} className="underline">
              {AFFINE_DEV_UI_URL}/interview?fresh=1
            </Link>
          </p>
        ) : null}

        {restoring ? (
          <p className="text-sm text-muted-foreground p-4">Restoring session…</p>
        ) : null}

        {!session && !restoring ? (
          <div className="p-6 max-w-3xl mx-auto w-full space-y-4">
            <Card className="p-5 space-y-4">
              <div>
                <h2 className="text-lg font-semibold">What do you want to build?</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Describe your workflow in plain language. We will ask dynamic,
                  catalog-backed setup questions and track chat readiness
                  with explicit coverage/risk signals.
                </p>
                {storageHint ? (
                  <p className="text-xs text-muted-foreground mt-2">{storageHint}</p>
                ) : null}
              </div>
              {recentSessions.length > 0 ? (
                <div className="space-y-2 rounded-md border border-border p-3 bg-muted/30">
                  <p className="text-sm font-medium">Continue a previous chat</p>
                  <ul className="space-y-1.5">
                    {recentSessions.slice(0, 6).map((row) => {
                      const label =
                        row.problem_statement.trim().slice(0, 96) +
                        (row.problem_statement.length > 96 ? "…" : "");
                      return (
                        <li key={row.id}>
                          <button
                            type="button"
                            className="w-full text-left text-sm px-3 py-2 rounded-md border border-border bg-background hover:bg-muted transition-colors"
                            onClick={() => resumeSession(row.id)}
                          >
                            <span className="line-clamp-2">{label || row.id}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : null}
              <Textarea
                rows={8}
                placeholder="e.g. Pre-screen loan applications using document extraction and policy checks, with analyst review on exceptions…"
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
                disabled={loading}
              />
              {error ? <p className="text-sm text-destructive">{error}</p> : null}
              <Button
                disabled={loading || problem.trim().length < 10}
                onClick={() => void handleStart(problem.trim())}
              >
                {loading
                  ? "Starting interview (30–90s first time)…"
                  : "Get started"}
              </Button>
            </Card>
          </div>
        ) : null}

        {session ? (
          <div className="app-main app-main--solo flex-1 min-h-0">
            <ChatPanel
              session={session}
              loading={loading}
              error={error}
              onStart={handleStart}
              onAnswer={handleAnswer}
            />
          </div>
        ) : null}

        {session?.spec.status === "ready" && showChatHistory ? (
          <div className="p-4 border-t border-border">
            <Button variant="default" size="sm" asChild>
              <Link to="/builder" search={{ sessionId: session.id }}>
                Open workflow builder
              </Link>
            </Button>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
