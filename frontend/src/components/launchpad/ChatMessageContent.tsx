import { useMemo } from "react";

const SECTION_HEADERS = [
  "Current understanding:",
  "Still unclear:",
  "Why I'm asking:",
  "Examples:",
  "Question:",
] as const;

type SectionHeader = (typeof SECTION_HEADERS)[number];

type ParsedSection = {
  header: SectionHeader;
  lines: string[];
};

function normalizeContent(content: string): string {
  return content.replace(/\r\n/g, "\n").trim();
}

function expandMarkerLines(lines: string[]): string[] {
  const expanded: string[] = [];
  for (const line of lines) {
    const parts = line
      .split(/(?=\s*[✓?•]\s+)/)
      .map((part) => part.trim())
      .filter(Boolean);
    expanded.push(...(parts.length > 0 ? parts : [line]));
  }
  return expanded;
}

function parseArchitectSections(content: string): ParsedSection[] | null {
  const normalized = normalizeContent(content);
  if (!normalized) return null;

  const headerRe =
    /(Current understanding:|Still unclear:|Why I'm asking:|Examples:|Question:)/g;
  const matches = [...normalized.matchAll(headerRe)];
  if (matches.length === 0) return null;

  const sections: ParsedSection[] = [];
  for (let i = 0; i < matches.length; i += 1) {
    const header = matches[i][1] as SectionHeader;
    if (!SECTION_HEADERS.includes(header)) continue;

    const bodyStart = matches[i].index! + matches[i][0].length;
    const bodyEnd =
      i + 1 < matches.length ? matches[i + 1].index! : normalized.length;
    const body = normalized.slice(bodyStart, bodyEnd).trim();

    const lines = expandMarkerLines(
      body
        .split(/\n+/)
        .flatMap((line) => line.split(/(?<=[.!?])\s+(?=[✓?•]\s)/))
        .map((line) => line.trim())
        .filter(Boolean),
    );

    sections.push({ header, lines });
  }

  return sections.length > 0 ? sections : null;
}

function stripListMarker(line: string): { marker: string; text: string } {
  const match = line.match(/^([✓?•\-*])\s+(.*)$/s);
  if (!match) return { marker: "", text: line };
  return { marker: match[1], text: match[2] };
}

type ChatMessageContentProps = {
  content: string;
  /** Hide the Question block when the same text is shown in the current-question panel. */
  omitQuestion?: boolean;
};

export function ChatMessageContent({
  content,
  omitQuestion = false,
}: ChatMessageContentProps) {
  const sections = useMemo(() => parseArchitectSections(content), [content]);

  if (!sections) {
    return (
      <div className="chat-message-content chat-message-content--plain">
        {normalizeContent(content)}
      </div>
    );
  }

  const visibleSections = omitQuestion
    ? sections.filter((section) => section.header !== "Question:")
    : sections;

  if (visibleSections.length === 0) {
    return (
      <div className="chat-message-content chat-message-content--plain">
        {normalizeContent(content)}
      </div>
    );
  }

  return (
    <div className="chat-message-content">
      {visibleSections.map((section) => {
        const title = section.header.replace(/:$/, "");
        const isParagraph =
          section.header === "Why I'm asking:" || section.header === "Question:";
        const listClass =
          section.header === "Current understanding:"
            ? "chat-message-section__list--known"
            : section.header === "Still unclear:"
              ? "chat-message-section__list--unclear"
              : section.header === "Examples:"
                ? "chat-message-section__list--examples"
                : "";

        return (
          <section key={section.header} className="chat-message-section">
            <h4 className="chat-message-section__title">{title}</h4>
            {isParagraph ? (
              <p className="chat-message-section__paragraph">
                {section.lines.join(" ")}
              </p>
            ) : (
              <ul className={`chat-message-section__list ${listClass}`.trim()}>
                {section.lines.map((line, index) => {
                  const { marker, text } = stripListMarker(line);
                  return (
                    <li key={`${section.header}-${index}`}>
                      {marker ? (
                        <span className="chat-message-section__marker" aria-hidden>
                          {marker}
                        </span>
                      ) : null}
                      <span>{text}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
