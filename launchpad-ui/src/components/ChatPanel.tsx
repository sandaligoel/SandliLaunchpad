import { useEffect, useRef, useState } from "react";
import type { InterviewSession } from "../types";

interface Props {
  session: InterviewSession | null;
  loading: boolean;
  error: string | null;
  onStart: (problemStatement: string) => void;
  onAnswer: (answer: string) => void;
}

export function ChatPanel({
  session,
  loading,
  error,
  onStart,
  onAnswer,
}: Props) {
  const [draft, setDraft] = useState("");
  const [problem, setProblem] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, loading]);

  const ready = session?.spec.status === "ready";
  const chips = session?.pending_question?.chips ?? [];
  const canReply = session && !ready && session.pending_question && !loading;

  if (!session) {
    return (
      <section className="chat-panel">
        <header className="chat-panel__header">
          <h2>Requirements interview</h2>
          <p className="chat-panel__subtitle">
            Describe the agent you want to build. The assistant will fill the
            specification one question at a time.
          </p>
        </header>
        <div className="chat-start">
          <label htmlFor="problem">Problem statement</label>
          <textarea
            id="problem"
            rows={8}
            placeholder="e.g. We need an agent to pre-screen KYC applications by extracting UBO relationships from corporate filings and flagging high-risk entities for analyst review…"
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            disabled={loading}
          />
          {error ? <p className="chat-error">{error}</p> : null}
          <button
            type="button"
            className="btn btn--primary"
            disabled={loading || problem.trim().length < 10}
            onClick={() => onStart(problem.trim())}
          >
            {loading ? "Starting…" : "Start interview"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="chat-panel">
      <header className="chat-panel__header">
        <h2>Requirements interview</h2>
        <p className="chat-panel__subtitle">
          Session <code className="mono">{session.id.slice(0, 8)}</code>
        </p>
      </header>

      <div className="chat-messages" role="log" aria-live="polite">
        {session.messages.map((msg, i) => (
          <div
            key={`${i}-${msg.role}`}
            className={`chat-bubble chat-bubble--${msg.role}`}
          >
            <span className="chat-bubble__role">
              {msg.role === "user" ? "You" : "Launchpad"}
            </span>
            <p>{msg.content}</p>
          </div>
        ))}
        {loading ? (
          <div className="chat-bubble chat-bubble--assistant chat-bubble--typing">
            <span className="chat-bubble__role">Launchpad</span>
            <p>Thinking…</p>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      {error ? <p className="chat-error">{error}</p> : null}

      {ready ? (
        <div className="chat-ready">
          <p>Specification complete — ready for architecture generation (Phase 3).</p>
        </div>
      ) : (
        <>
          {chips.length > 0 ? (
            <div className="chip-row" role="group" aria-label="Quick answers">
              {chips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className="chip"
                  disabled={!canReply}
                  onClick={() => onAnswer(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          ) : null}
          <form
            className="chat-compose"
            onSubmit={(e) => {
              e.preventDefault();
              const text = draft.trim();
              if (!text || !canReply) return;
              onAnswer(text);
              setDraft("");
            }}
          >
            <input
              type="text"
              placeholder={
                canReply
                  ? "Or type a custom answer…"
                  : "Waiting for the next question…"
              }
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={!canReply}
            />
            <button
              type="submit"
              className="btn btn--primary"
              disabled={!canReply || !draft.trim()}
            >
              Send
            </button>
          </form>
        </>
      )}
    </section>
  );
}
