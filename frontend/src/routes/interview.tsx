import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import {
  checkAffineHealth,
  getSession,
  isSessionNotFoundError,
  listSessions,
  startSession,
  submitTurn,
  type SessionSummary,
} from "@/api/affine/client";
import { isCustomDescribeChip } from "@/api/affine/chipUtils";
import {
  preserveSessionBeforeNewInterviewAsync,
  registerLaunchpadWorkflowPlaceholder,
  setActiveBuilderSessionId,
} from "@/api/affine/builderStorage";
import {
  clearStoredSessionId,
  consumeFreshUrlFlag,
  getStoredSessionId,
  setStoredSessionId,
} from "@/api/affine/sessionStorage";
import type { InterviewSession } from "@/api/affine/types";
import { USER_INTERVIEW_FIELD_KEYS } from "@/api/affine/types";
import { AFFINE_DEV_UI_URL, AFFINE_START_CMD } from "@/config/affineDev";

type InterviewSearch = {
  fresh?: string;
  sessionId?: string;
  /** When set, show chat history without auto-opening Workflow Builder. */
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
    meta: [{ title: "Launchpad Interview — AgentForge | Affine" }],
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
  const [draft, setDraft] = useState("");
  const [customDescribeMode, setCustomDescribeMode] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkAffineHealth()
      .then((health) => {
        setApiOk(true);
        const st = health.storage;
        if (st?.backend === "azure_blob" && st.reachable) {
          const n = st.session_blob_count ?? 0;
          setStorageHint(
            `Connected to Azure storage (${st.account}/${st.container}) — ${n} saved interview(s).`,
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
      })
      .catch(() => setApiOk(false));
  }, []);

  useEffect(() => {
    if (apiOk !== true || session) return;
    listSessions()
      .then(setRecentSessions)
      .catch(() => setRecentSessions([]));
  }, [apiOk, session]);

  const resumeSession = useCallback((sessionId: string) => {
    setRestoring(true);
    setError(null);
    setStoredSessionId(sessionId);
    getSession(sessionId)
      .then(({ session: s }) => setSession(s))
      .catch((e) => {
        if (isSessionNotFoundError(e)) clearStoredSessionId();
        setError(e instanceof Error ? e.message : "Could not load session");
      })
      .finally(() => setRestoring(false));
  }, []);

  useEffect(() => {
    if (consumeFreshUrlFlag()) {
      setRestoring(false);
      return;
    }
    const storedId = urlSessionId ?? getStoredSessionId();
    if (!storedId) {
      setRestoring(false);
      return;
    }
    if (urlSessionId) setStoredSessionId(urlSessionId);
    getSession(storedId)
      .then(({ session: s }) => setSession(s))
      .catch((e) => {
        if (isSessionNotFoundError(e)) clearStoredSessionId();
      })
      .finally(() => setRestoring(false));
  }, [urlSessionId]);

  useEffect(() => {
    if (session?.id) setStoredSessionId(session.id);
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
      setActiveBuilderSessionId(session.id);
      navigate({
        to: "/builder",
        search: { sessionId: session.id },
      });
    }
  }, [session?.spec.status, session?.id, navigate, showChatHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, loading]);

  const handleStart = useCallback(async () => {
    const text = problem.trim();
    if (text.length < 10) return;
    await preserveSessionBeforeNewInterviewAsync(
      getStoredSessionId(),
      session?.spec.problem_statement,
    );
    clearStoredSessionId();
    setLoading(true);
    setError(null);
    try {
      const { session: s } = await startSession(text);
      if (s.spec.status === "ready") openBuilderAfterReady.current = true;
      setSession(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }, [problem]);

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!session) return;
      setLoading(true);
      setError(null);
      try {
        const { session: s } = await submitTurn(session.id, answer);
        if (s.spec.status === "ready") openBuilderAfterReady.current = true;
        setSession(s);
      } catch (e) {
        if (isSessionNotFoundError(e)) {
          clearStoredSessionId();
          setSession(null);
          setError("Session expired. Start a new interview.");
        } else {
          setError(e instanceof Error ? e.message : "Failed to submit answer");
        }
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  const ready = session?.spec.status === "ready";
  const canPlan = session?.spec.status === "ready";
  const pq = session?.pending_question;
  const chips = pq?.chips ?? [];
  const presetChips = chips.filter((c) => !isCustomDescribeChip(c));
  const customChip = chips.find(isCustomDescribeChip);
  const canReply = session && !ready && pq && !loading;

  const topicsCovered = session
    ? USER_INTERVIEW_FIELD_KEYS.filter((k) => {
        const f = session.spec.fields[k];
        return f?.status === "known" && f.value?.trim();
      }).length
    : 0;
  const userReplies = session
    ? session.messages.filter(
        (m) => m.role === "user" && m.field_key && m.content.trim(),
      ).length
    : 0;

  return (
    <AppShell>
      <Topbar
        title="Agent Launchpad"
        subtitle="Focused questions until we have enough detail — plain language only"
        actions={
          session ? (
            <div className="flex items-center gap-2">
              {canPlan && session ? (
                <Button variant="outline" size="sm" asChild>
                  <Link
                    to="/builder"
                    search={{ sessionId: session.id }}
                  >
                    Workflow builder
                  </Link>
                </Button>
              ) : null}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (!window.confirm("Start a new interview?")) return;
                  void preserveSessionBeforeNewInterviewAsync(
                    session?.id ?? getStoredSessionId(),
                    session?.spec.problem_statement,
                  ).then(() => {
                    clearStoredSessionId();
                    setSession(null);
                    setProblem("");
                  });
                }}
              >
                New interview
              </Button>
            </div>
          ) : null
        }
      />
      <main className="p-6 max-w-4xl mx-auto space-y-4 overflow-auto">
        {apiOk === false ? (
          <p className="text-sm text-destructive rounded-md border border-destructive/30 bg-destructive/5 p-3">
            Cannot reach AFFINE API (expected at{" "}
            <code className="text-xs">config/dev-ports.json</code>). In another
            terminal run <code className="text-xs">{AFFINE_START_CMD}</code>, then
            reload this page. If you changed ports, run{" "}
            <code className="text-xs">./scripts/sync-dev-env.sh</code> and restart{" "}
            <code className="text-xs">npm run dev</code>. Fresh session:{" "}
            <Link to="/interview" search={{ fresh: "1" }} className="underline">
              {AFFINE_DEV_UI_URL}/interview?fresh=1
            </Link>
            .
          </p>
        ) : null}

        {restoring ? (
          <p className="text-sm text-muted-foreground">Restoring session…</p>
        ) : null}

        {!session && !restoring ? (
          <Card className="p-5 space-y-4">
            <div>
              <h2 className="text-lg font-semibold">What do you want to build?</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Describe it in everyday language. We will ask focused
                questions until we have enough detail — pick what fits or type
                your own answer.
              </p>
              {storageHint ? (
                <p className="text-xs text-muted-foreground mt-2">{storageHint}</p>
              ) : null}
            </div>
            {recentSessions.length > 0 ? (
              <div className="space-y-2 rounded-md border border-border p-3 bg-muted/30">
                <p className="text-sm font-medium">Continue a previous interview</p>
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
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide mt-1 block">
                            {row.status ?? "draft"}
                            {row.has_architecture_plan ? " · has plan" : ""}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}
            <Textarea
              rows={8}
              placeholder="e.g. I want something that reads loan applications, checks them against our policy, and sends tricky cases to a human reviewer…"
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              disabled={loading}
            />
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button
              disabled={loading || problem.trim().length < 10}
              onClick={() => void handleStart()}
            >
              {loading
                ? "Preparing first question (20–40s)…"
                : "Get started"}
            </Button>
          </Card>
        ) : null}

        {session && loading && !pq ? (
          <Card className="p-4">
            <p className="text-sm text-muted-foreground">
              Working on your next question — this usually takes 15–30 seconds…
            </p>
          </Card>
        ) : null}

        {session ? (
          <>
            {session && !ready ? (
              <p className="text-sm text-muted-foreground">
                {topicsCovered > 0
                  ? `${topicsCovered} topic${topicsCovered === 1 ? "" : "s"} captured`
                  : userReplies > 0
                    ? "Gathering details…"
                    : "Starting interview…"}
              </p>
            ) : null}

            <Card className="p-4 max-h-[50vh] overflow-y-auto space-y-3">
              {session.messages.map((msg, i) => (
                <div
                  key={`${i}-${msg.role}`}
                  className={
                    msg.role === "user"
                      ? "ml-8 rounded-lg bg-primary/10 px-3 py-2 text-sm"
                      : "mr-8 rounded-lg bg-muted px-3 py-2 text-sm"
                  }
                >
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                    {msg.role === "user" ? "You" : "Launchpad"}
                  </div>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              ))}
              {loading ? (
                <p className="text-sm text-muted-foreground">Thinking…</p>
              ) : null}
              <div ref={bottomRef} />
            </Card>

            {ready ? (
              <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  {showChatHistory
                    ? "Interview complete. Your answers are saved below."
                    : "Interview complete — opening Workflow Builder with your architecture…"}
                </p>
                {showChatHistory && session ? (
                  <Button variant="default" size="sm" asChild>
                    <Link
                      to="/builder"
                      search={{ sessionId: session.id }}
                    >
                      Workflow builder
                    </Link>
                  </Button>
                ) : null}
              </Card>
            ) : pq ? (
              <Card className="p-4 space-y-3">
                <p className="text-base leading-relaxed">{pq.question}</p>
                <p className="text-xs text-muted-foreground">
                  Tap an option below or type your own answer.
                </p>
                {!customDescribeMode && presetChips.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {presetChips.map((chip) => (
                      <Button
                        key={chip}
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!canReply}
                        onClick={() => void handleAnswer(chip)}
                      >
                        {chip}
                      </Button>
                    ))}
                    {customChip ? (
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        disabled={!canReply}
                        onClick={() => {
                          setCustomDescribeMode(true);
                          setDraft("");
                        }}
                      >
                        {customChip}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
                <div className="flex gap-2">
                  <Textarea
                    rows={customDescribeMode ? 3 : 1}
                    placeholder="Type your answer…"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    disabled={!canReply}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && customDescribeMode) {
                        e.preventDefault();
                        if (draft.trim()) void handleAnswer(draft.trim());
                        setDraft("");
                        setCustomDescribeMode(false);
                      }
                    }}
                  />
                  <Button
                    disabled={!canReply || !draft.trim()}
                    onClick={() => {
                      void handleAnswer(draft.trim());
                      setDraft("");
                      setCustomDescribeMode(false);
                    }}
                  >
                    Send
                  </Button>
                </div>
              </Card>
            ) : null}

            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </>
        ) : null}
      </main>
    </AppShell>
  );
}
