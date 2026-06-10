import { useEffect, useRef, useState } from "react";
import type { InterviewSession } from "@/api/affine/types";
import { isCustomDescribeChip } from "@/api/affine/chipUtils";
import { ChatMessageContent } from "./ChatMessageContent";

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
  const awaitingRevision = Boolean(session?.awaiting_problem_revision);
  const isOpenChat =
    session?.chat_phase === "open" ||
    (!session?.chat_phase &&
      !session?.pending_question &&
      !session?.agent_workflow &&
      !Object.keys(session?.clarifying_answers ?? {}).length &&
      !awaitingRevision);
  const fieldKey = session?.pending_question?.field_key ?? "";
  const isClarifying =
    fieldKey.startsWith("clarifying:") || fieldKey.startsWith("discovery:");
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
  const canReply =
    session &&
    !ready &&
    (isOpenChat || session.pending_question || awaitingRevision) &&
    !loading;
  const workflow = session?.agent_workflow;
  const matchedAgents = workflow?.matched_agents ?? [];
  const totalQuestions = workflow?.questions?.length ?? 0;
  const answeredCount = workflow
    ? Object.values(workflow.answers ?? {}).filter((v) => v?.trim()).length
    : 0;
  const questionProgress =
    totalQuestions > 0
      ? `Question ${Math.min(answeredCount + 1, totalQuestions)} of ${totalQuestions}`
      : null;
  const nearWorkflowEnd =
    (workflow?.coverage_score ?? 0) >= 70 ||
    (workflow?.critical_items?.length ?? 0) === 0;
  const loadingMessage =
    session && isOpenChat
      ? "Thinking…"
      : session && nearWorkflowEnd
        ? "Generating your architecture plan (15–30s)…"
        : "Preparing next question (usually 10–25s)…";
  const topicLabel = session?.pending_question?.topic_label?.trim();
  const lastMessageIndex = session ? session.messages.length - 1 : -1;

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
            Ask anything about workflows and agents — like ChatGPT. When you describe
            what you want to automate, we switch into workflow scoping and builder mode.
          </p>
        </header>
        <div className="chat-start">
          <label htmlFor="problem">Message</label>
          <textarea
            id="problem"
            rows={6}
            placeholder="Ask a question, request examples, or describe a workflow to build…"
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            disabled={loading}
          />
          {error ? <p className="chat-error">{error}</p> : null}
          <button
            type="button"
            className="btn btn--primary"
            disabled={loading || problem.trim().length < 1}
            onClick={() => onStart(problem.trim())}
          >
            {loading ? "Starting…" : "Send"}
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
            {questionProgress ? (
              <span className="chat-panel__progress">{questionProgress}</span>
            ) : null}
          </p>
        ) : null}
        {matchedAgents.length > 0 ? (
          <div className="chat-matched-agents" aria-label="Matched catalog agents">
            <span className="chat-matched-agents__label">Pipeline agents</span>
            <div className="chat-matched-agents__list">
              {matchedAgents.slice(0, 8).map((a) => (
                <span key={a.agent_id} className="chat-matched-agents__pill" title={a.reason}>
                  {a.name}
                </span>
              ))}
              {matchedAgents.length > 8 ? (
                <span className="chat-matched-agents__pill chat-matched-agents__pill--more">
                  +{matchedAgents.length - 8}
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </header>

      <div className="chat-messages" role="log" aria-live="polite">
        {session.messages.map((msg, i) => {
          const pendingQuestion = session.pending_question?.question?.trim();
          const isVerboseScopingReply =
            msg.content.includes("Current understanding:") ||
            msg.content.includes("Still unclear:");
          const hideDuplicateQuestion =
            msg.role === "assistant" &&
            i === lastMessageIndex &&
            Boolean(session.pending_question) &&
            !awaitingRevision &&
            (msg.content.trim() === pendingQuestion ||
              msg.field_key === session.pending_question?.field_key ||
              isVerboseScopingReply);

          if (hideDuplicateQuestion) {
            return null;
          }

          return (
            <div
              key={`${i}-${msg.role}`}
              className={`chat-bubble chat-bubble--${msg.role}`}
            >
              <span className="chat-bubble__role">
                {msg.role === "user" ? "You" : "Launchpad"}
              </span>
              {msg.role === "assistant" ? (
                <ChatMessageContent content={msg.content} />
              ) : (
                <div className="chat-message-content chat-message-content--plain">
                  {msg.content}
                </div>
              )}
            </div>
          );
        })}
        {loading ? (
          <div className="chat-bubble chat-bubble--assistant chat-bubble--typing">
            <span className="chat-bubble__role">Launchpad</span>
            <p>
              {loadingMessage}
              <span className="chat-typing-dots" aria-hidden>
                <span />
                <span />
                <span />
              </span>
            </p>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      {error ? <p className="chat-error">{error}</p> : null}

      {awaitingRevision && !ready ? (
        <div className="chat-current-question" role="region" aria-label="Update problem statement">
          <p className="chat-current-question__label">Update problem statement</p>
          <p className="chat-current-question__text">
            Paste your new workflow description below. Scoping will restart from the beginning.
          </p>
        </div>
      ) : null}

      {session.pending_question && !ready && !awaitingRevision ? (
        <div className="chat-current-question" role="region" aria-label="Current question">
          <p className="chat-current-question__label">Current question</p>
          <p className="chat-current-question__text">
            {session.pending_question.question}
          </p>
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

          {!isOpenChat &&
          !awaitingRevision &&
          !customDescribeMode &&
          (presetChips.length > 0 || customChip) ? (
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
            {customDescribeMode || awaitingRevision || isOpenChat ? (
              <textarea
                ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                rows={awaitingRevision ? 6 : isOpenChat ? 4 : 3}
                placeholder={
                  awaitingRevision
                    ? "Describe the workflow you want to build…"
                    : isOpenChat
                      ? "Ask anything or describe a workflow to build…"
                      : "Describe your answer in detail…"
                }
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={!canReply}
                aria-label={awaitingRevision ? "New problem statement" : "Custom answer"}
              />
            ) : (
              <input
                ref={inputRef as React.RefObject<HTMLInputElement>}
                type="text"
                placeholder={
                  canReply
                    ? isClarifying
                      ? "Your answer (1–2 sentences)…"
                      : "Type your answer…"
                    : "Waiting for the next question…"
                }
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={!canReply}
              />
            )}
            <div className="chat-compose__actions">
              {!isOpenChat && !customDescribeMode && canReply && !awaitingRevision ? (
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
