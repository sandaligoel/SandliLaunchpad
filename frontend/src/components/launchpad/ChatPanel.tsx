import { useEffect, useRef, useState } from "react";
import type { InterviewSession } from "@/api/affine/types";
import { isCustomDescribeChip } from "@/api/affine/chipUtils";

function parseInlineQuestionOptions(question: string): string[] {
  const text = question.trim();
  if (!text) return [];

  const suggestedLineMatch = text.match(/suggested\s*:\s*(.+)$/i);
  const suggestedText = suggestedLineMatch?.[1]?.trim() ?? "";
  if (suggestedText) {
    const fromSuggested = suggestedText
      .split(/[·|]/)
      .map((part) => part.replace(/[`"']/g, "").trim())
      .filter(Boolean);
    if (fromSuggested.length >= 2) return fromSuggested;
  }

  const tail = text.replace(/\?$/, "");
  const afterDash = tail.match(/[—:-]\s*(.+)$/);
  const optionCandidate = (afterDash?.[1] ?? "").trim();
  if (!optionCandidate) return [];

  const normalized = optionCandidate.replace(/\s+or\s+/gi, ", ");
  const fromQuestion = normalized
    .split(",")
    .map((part) => part.replace(/[`"']/g, "").trim())
    .filter((part) => part.length > 1);

  return fromQuestion.length >= 2 ? fromQuestion : [];
}

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
  const isClarifying = session?.pending_question?.field_key?.startsWith(
    "clarifying:",
  );
  const chips = session?.pending_question?.chips ?? [];
  const inlineChips = parseInlineQuestionOptions(
    session?.pending_question?.question ?? "",
  );
  const effectiveChips = chips.length > 0 ? chips : inlineChips;
  const chipsWithOther =
    effectiveChips.length > 0 &&
    !effectiveChips.some((chip) => isCustomDescribeChip(chip))
      ? [...effectiveChips, "Other / describe in chat"]
      : effectiveChips;
  const suggestedChip = session?.pending_question?.suggested_chip?.trim();
  const presetChips = chipsWithOther.filter((c) => !isCustomDescribeChip(c));
  const customChip = chipsWithOther.find(isCustomDescribeChip);
  const canReply = session && !ready && session.pending_question && !loading;
  const workflow = session?.agent_workflow;
  const nearWorkflowEnd =
    (workflow?.coverage_score ?? 0) >= 70 ||
    (workflow?.critical_items?.length ?? 0) === 0;
  const loadingMessage =
    session && nearWorkflowEnd
      ? "Generating your architecture plan (15–30s)…"
      : "Preparing next question (usually 10–25s)…";
  const topicLabel = session?.pending_question?.topic_label?.trim();
  const whyItMatters = session?.pending_question?.why_it_matters?.trim();
  const suggestionReason = session?.pending_question?.suggestion_reason?.trim();

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
          <h2>Chat</h2>
          <p className="chat-panel__subtitle">
            Describe what you want to automate. We match agents from the catalog and
            ask setup questions for their inputs — pick an option or type your answer.
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
            {loading ? "Starting…" : "Start chat"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className={`chat-panel ${compact ? "chat-panel--compact" : ""}`}>
      <header className="chat-panel__header">
        <h2>Chat</h2>
        <p className="chat-panel__subtitle">
          Session <code className="mono">{session.id.slice(0, 8)}</code>
          {workflow &&
          (workflow.coverage_score != null || workflow.risk_score != null) ? (
            <span className="chat-panel__metrics">
              {" "}
              · Coverage {workflow.coverage_score ?? 0}%
              {workflow.required_input_count
                ? ` (${workflow.required_input_count} inputs)`
                : ""}{" "}
              · Risk {workflow.risk_score ?? 0}/10
            </span>
          ) : null}
        </p>
        {topicLabel && session.pending_question ? (
          <p className="chat-panel__topic" role="status">
            <span className="chat-panel__topic-label">{topicLabel}</span>
          </p>
        ) : null}
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
            <p>{loadingMessage}</p>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      {error ? <p className="chat-error">{error}</p> : null}

      {session.pending_question && (whyItMatters || suggestionReason) ? (
        <div className="chat-context-hint" role="note">
          {whyItMatters ? <p>{whyItMatters}</p> : null}
          {suggestionReason ? (
            <p className="chat-context-hint__reason">{suggestionReason}</p>
          ) : null}
        </div>
      ) : null}

      {ready ? (
        <div className="chat-ready">
          <p>Chat complete — you can open the workflow builder when ready.</p>
        </div>
      ) : (
        <>
          {customDescribeMode ? (
            <p className="chat-custom-hint" role="status">
              Type your answer below, then press Send to continue.
            </p>
          ) : null}

          {!customDescribeMode && (presetChips.length > 0 || customChip) ? (
            <div className="chip-row" role="group" aria-label="Quick answers">
              {presetChips.map((chip) => {
                const isSuggested =
                  suggestedChip &&
                  chip.trim().toLowerCase() === suggestedChip.toLowerCase();
                return (
                  <button
                    key={chip}
                    type="button"
                    className={`chip ${isSuggested ? "chip--suggested" : ""}`}
                    disabled={!canReply}
                    onClick={() => handleChipClick(chip)}
                    title={chip}
                  >
                    {isSuggested ? (
                      <span className="chip__badge">Suggested</span>
                    ) : null}
                    {chip}
                  </button>
                );
              })}
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
              {!customDescribeMode && canReply ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => onAnswer("finish")}
                >
                  Finish early
                </button>
              ) : null}
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
