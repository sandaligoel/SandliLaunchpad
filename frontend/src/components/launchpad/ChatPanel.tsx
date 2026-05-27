import { useEffect, useRef, useState } from "react";
import type { InterviewSession } from "@/api/affine/types";
import { isCustomDescribeChip } from "@/api/affine/chipUtils";

interface Props {
  session: InterviewSession | null;
  loading: boolean;
  error: string | null;
  onStart: (problemStatement: string) => void;
  onAnswer: (answer: string) => void;
  /** Narrow column when architecture workspace is open */
  compact?: boolean;
}

export function ChatPanel({
  session,
  loading,
  error,
  onStart,
  onAnswer,
  compact = false,
}: Props) {
  const [draft, setDraft] = useState("");
  const [problem, setProblem] = useState("");
  const [customDescribeMode, setCustomDescribeMode] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, loading]);

  useEffect(() => {
    if (!session?.pending_question) {
      setCustomDescribeMode(false);
    }
  }, [session?.pending_question?.field_key]);

  useEffect(() => {
    if (customDescribeMode && inputRef.current) {
      inputRef.current.focus();
    }
  }, [customDescribeMode]);

  const ready = session?.spec.status === "ready";
  const clarifyingHint = session?.pending_question?.why_it_matters;
  const isClarifying = session?.pending_question?.field_key?.startsWith(
    "clarifying:",
  );
  const chips = session?.pending_question?.chips ?? [];
  const presetChips = chips.filter((c) => !isCustomDescribeChip(c));
  const customChip = chips.find(isCustomDescribeChip);
  const canReply = session && !ready && session.pending_question && !loading;

  const submitDraft = () => {
    const text = draft.trim();
    if (!text || !canReply) return;
    onAnswer(text);
    setDraft("");
    setCustomDescribeMode(false);
  };

  const handleChipClick = (chip: string) => {
    if (!canReply) return;
    if (isCustomDescribeChip(chip)) {
      setCustomDescribeMode(true);
      setDraft("");
      return;
    }
    onAnswer(chip);
    setCustomDescribeMode(false);
  };

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
    <section className={`chat-panel ${compact ? "chat-panel--compact" : ""}`}>
      <header className="chat-panel__header">
        <h2>{compact ? "Interview" : "Requirements interview"}</h2>
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
          {isClarifying && clarifyingHint ? (
            <p className="chat-clarifying-hint" role="note">
              <strong>Why this matters:</strong> {clarifyingHint}
            </p>
          ) : null}

          {customDescribeMode ? (
            <p className="chat-custom-hint" role="status">
              Type your answer below, then press Send to continue.
            </p>
          ) : null}

          {!customDescribeMode && (presetChips.length > 0 || customChip) ? (
            <div className="chip-row" role="group" aria-label="Quick answers">
              {presetChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className="chip"
                  disabled={!canReply}
                  onClick={() => handleChipClick(chip)}
                >
                  {chip}
                </button>
              ))}
              {customChip ? (
                <button
                  type="button"
                  className="chip chip--custom"
                  disabled={!canReply}
                  onClick={() => handleChipClick(customChip)}
                >
                  {customChip}
                </button>
              ) : null}
            </div>
          ) : null}

          <form
            className={`chat-compose ${customDescribeMode ? "chat-compose--custom" : ""}`}
            onSubmit={(e) => {
              e.preventDefault();
              submitDraft();
            }}
          >
            {customDescribeMode ? (
              <textarea
                ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                rows={3}
                placeholder="Describe your answer in detail…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={!canReply}
                aria-label="Custom answer"
              />
            ) : (
              <input
                ref={inputRef as React.RefObject<HTMLInputElement>}
                type="text"
                placeholder={
                  canReply
                    ? isClarifying
                      ? "Your answer (1–2 sentences)…"
                      : "Or type a custom answer…"
                    : "Waiting for the next question…"
                }
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={!canReply}
              />
            )}
            <div className="chat-compose__actions">
              {customDescribeMode ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={!canReply}
                  onClick={() => {
                    setCustomDescribeMode(false);
                    setDraft("");
                  }}
                >
                  Back to options
                </button>
              ) : null}
              <button
                type="submit"
                className="btn btn--primary"
                disabled={!canReply || !draft.trim()}
              >
                Send
              </button>
            </div>
          </form>
        </>
      )}
    </section>
  );
}
