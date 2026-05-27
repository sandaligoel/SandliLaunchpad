type Step = "interview" | "spec" | "architecture";

interface Props {
  current: Step;
  canArchitecture: boolean;
  onGoSpec: () => void;
  onGoArchitecture: () => void;
}

export function WorkflowSteps({
  current,
  canArchitecture,
  onGoSpec,
  onGoArchitecture,
}: Props) {
  return (
    <nav className="workflow-steps" aria-label="Launchpad workflow">
      <span
        className={`workflow-steps__item ${current === "interview" || current === "spec" ? "workflow-steps__item--active" : ""} ${current !== "architecture" ? "workflow-steps__item--done" : ""}`}
      >
        <span className="workflow-steps__num">1</span>
        Interview
      </span>
      <span className="workflow-steps__line" aria-hidden />
      <button
        type="button"
        className={`workflow-steps__item workflow-steps__item--btn ${current === "spec" ? "workflow-steps__item--active" : ""} ${current === "architecture" ? "workflow-steps__item--done" : ""}`}
        onClick={onGoSpec}
      >
        <span className="workflow-steps__num">2</span>
        Specification
      </button>
      <span className="workflow-steps__line" aria-hidden />
      <button
        type="button"
        className={`workflow-steps__item workflow-steps__item--btn ${current === "architecture" ? "workflow-steps__item--active" : ""}`}
        onClick={onGoArchitecture}
        disabled={!canArchitecture}
      >
        <span className="workflow-steps__num">3</span>
        Architecture
      </button>
    </nav>
  );
}
