"""Parser for Affine solution catalog PDFs (multi-project, structured agent blocks)."""

from __future__ import annotations

import re

from backend.app.schemas.solution_document import (
    ParsedSolution,
    ParsedSolutionAgent,
    SolutionCatalogDocument,
)
from backend.app.utils.text import dedupe_preserve_order, normalize_whitespace

# Split catalog into per-solution segments: "Project Name — Solution Summary"
SOLUTION_SPLIT_RE = re.compile(
    r"(?=\n([^\n]{4,120}?)\s*—\s*Solution Summary\s*\n)",
    re.MULTILINE,
)

# Agent headings: "Entity Extraction Agent" or "GPT-4o Fashion Vision Analyzer (module.py)"
AGENT_HEADING_RE = re.compile(
    r"(?:^|\n)"
    r"([A-Z][^\n•]{2,100}?"
    r"(?:Agent|Validator|Drafter|Engine|Pipeline|Generator|Classifier|Analyzer|"
    r"Compositor|Service|Stub|Indexer|Orchestrator|Coordinator|Router))"
    r"(?:\s*\([^)\n]{1,60}\))?"
    r"\s*\n",
    re.MULTILINE,
)

FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "function": re.compile(
        r"Function:\s*(.+?)(?=\n•\s*\n(?:Input|Output|Model|Position)|\n[A-Z][a-z].{10,}?\n|$)",
        re.DOTALL,
    ),
    "input": re.compile(
        r"Input:\s*(.+?)(?=\n•\s*\n(?:Output|Model|Position|Function)|\n[A-Z][a-z].{10,}?\n|$)",
        re.DOTALL,
    ),
    "output": re.compile(
        r"Output:\s*(.+?)(?=\n•\s*\n(?:Model|Position|Input|Function)|\n[A-Z][a-z].{10,}?\n|$)",
        re.DOTALL,
    ),
    "model": re.compile(
        r"Model/Service:\s*(.+?)(?=\n•\s*\n(?:Position|Function|Input)|\n[A-Z][a-z].{10,}?\n|$)",
        re.DOTALL,
    ),
    "position": re.compile(
        r"Position in flow:\s*(.+?)(?=\n•\s*\n|\n[A-Z][A-Za-z].{8,}?\n|$)",
        re.DOTALL,
    ),
}


class SolutionDocumentParser:
    """Parses solution_agents.pdf-style catalogs into structured projects."""

    def parse_full_text(
        self,
        full_text: str,
        filename: str,
        page_count: int,
        content_hash: str,
    ) -> SolutionCatalogDocument:
        segments = self._split_solutions(full_text)
        solutions: list[ParsedSolution] = []
        seen_names: set[str] = set()
        name_counts: dict[str, int] = {}

        for project_name, segment in segments:
            key = project_name.strip().lower()
            if key in seen_names:
                name_counts[key] = name_counts.get(key, 1) + 1
                project_name = f"{project_name} ({name_counts[key]})"
                key = project_name.strip().lower()
            seen_names.add(key)
            parsed = self._parse_solution_segment(project_name, segment)
            if parsed.agents or parsed.solution_summary:
                solutions.append(parsed)

        return SolutionCatalogDocument(
            filename=filename,
            page_count=page_count,
            content_hash=content_hash,
            solutions=solutions,
        )

    @staticmethod
    def is_solution_catalog(full_text: str, filename: str = "") -> bool:
        name_hint = "solution_agents" in filename.lower() or "solution" in filename.lower()
        markers = (
            "— Solution Summary" in full_text or "- Solution Summary" in full_text,
            "AI Agents & Components" in full_text,
            "Position in flow:" in full_text,
        )
        return name_hint or sum(markers) >= 2

    def _split_solutions(self, full_text: str) -> list[tuple[str, str]]:
        parts = SOLUTION_SPLIT_RE.split(full_text)
        results: list[tuple[str, str]] = []

        # First solution often sits in preamble (no newline before title)
        preamble = parts[0].strip() if parts else ""
        first = re.match(
            r"^(.+?)\s*[—-]\s*Solution Summary\s*\n(.*)",
            preamble,
            re.DOTALL,
        )
        if first:
            results.append((first.group(1).strip(), preamble))

        i = 1
        while i < len(parts) - 1:
            name = parts[i].strip()
            body = parts[i + 1]
            results.append((name, f"{name} — Solution Summary\n{body}"))
            i += 2

        if not results:
            results.append(("Solution Catalog", full_text))
        return results

    def _parse_solution_segment(self, project_name: str, segment: str) -> ParsedSolution:
        client = self._extract_labeled_field(segment, r"Client:\s*")
        vertical = self._extract_labeled_field(segment, r"Vertical:\s*")
        business_problem = self._extract_section(
            segment, "Business Problem", ["Solution Overview", "Key Features", "AI Agents"]
        )
        solution_summary = self._extract_section(
            segment,
            "Solution Overview",
            ["Key Features", "AI Agents & Components", "AI Agents", "Tech Stack"],
        )
        if not solution_summary:
            solution_summary = self._extract_section(
                segment, "Key Features", ["AI Agents", "Tech Stack", "Data Flow"]
            )

        tech_stack = self._parse_tech_stack(segment)
        workflow_steps = self._parse_numbered_flow(segment)
        integrations = self._parse_integrations(segment)
        agents = self._parse_agents(segment)

        outcomes = ""
        if "Key Features" in segment:
            outcomes = self._extract_section(
                segment, "Key Features", ["AI Agents", "Tech Stack", "Data Flow"]
            )[:2000]

        return ParsedSolution(
            project_name=project_name.strip(),
            client=client,
            vertical=vertical,
            business_problem=business_problem,
            solution_summary=solution_summary,
            tech_stack=tech_stack,
            outcomes=outcomes,
            agents=agents,
            workflow_steps=workflow_steps,
            integrations=integrations,
            segment_text=segment,
        )

    def _parse_agents(self, segment: str) -> list[ParsedSolutionAgent]:
        agents: list[ParsedSolutionAgent] = []
        agent_block = self._extract_section(
            segment,
            "AI Agents & Components",
            ["Tech Stack", "Data Flow", "External Integrations", "— Solution Summary"],
        )
        if not agent_block:
            agent_block = segment

        headings = list(AGENT_HEADING_RE.finditer(agent_block))
        if not headings:
            return agents

        for idx, match in enumerate(headings):
            name = normalize_whitespace(match.group(1))
            start = match.end()
            end = headings[idx + 1].start() if idx + 1 < len(headings) else len(agent_block)
            block = agent_block[start:end]
            agents.append(self._parse_agent_block(name, block))

        return [a for a in agents if a.agent_name]

    def _parse_agent_block(self, name: str, block: str) -> ParsedSolutionAgent:
        def field(key: str) -> str:
            m = FIELD_PATTERNS[key].search(block)
            return normalize_whitespace(m.group(1)) if m else ""

        inputs_raw = field("input")
        outputs_raw = field("output")
        inputs = [inputs_raw] if inputs_raw else []
        outputs = [outputs_raw] if outputs_raw else []

        return ParsedSolutionAgent(
            agent_name=name,
            function_summary=field("function"),
            inputs=inputs,
            outputs=outputs,
            model_used=field("model"),
            workflow_position=field("position"),
            raw_content=block[:4000],
        )

    def _parse_tech_stack(self, segment: str) -> list[str]:
        block = self._extract_section(
            segment, "Tech Stack", ["Data Flow", "External Integrations", "Architecture"]
        )
        if not block:
            return []
        items: list[str] = []
        for line in block.split("\n"):
            line = line.strip().lstrip("•").strip()
            if not line or line.endswith(":"):
                continue
            if line.startswith(("Frontend:", "Backend:", "AI/ML:", "Infrastructure:", "Databases:", "Integrations:")):
                continue
            if len(line) > 2 and len(line) < 120:
                items.append(line)
        return dedupe_preserve_order(items)

    def _parse_numbered_flow(self, segment: str) -> list[str]:
        block = self._extract_section(
            segment, "Data Flow", ["External Integrations", "Architecture", "Tech Stack"]
        )
        if not block:
            return []
        steps = re.findall(r"^\s*\d+\.\s*(.+?)(?=\n\s*\d+\.|\n[A-Z][a-z]+ |\Z)", block, re.M | re.S)
        return [normalize_whitespace(s)[:500] for s in steps if s.strip()]

    def _parse_integrations(self, segment: str) -> list[str]:
        block = self._extract_section(
            segment,
            "External Integrations",
            ["Architecture", "Deployment", "— Solution Summary", "Data Flow"],
        )
        if not block:
            return []
        items: list[str] = []
        for line in block.split("\n"):
            line = line.strip().lstrip("•").strip()
            if line and not line.endswith(":") and len(line) < 200:
                name = line.split(":")[0].strip()
                if name:
                    items.append(name)
        return dedupe_preserve_order(items)

    @staticmethod
    def _extract_labeled_field(text: str, label_pattern: str) -> str:
        m = re.search(label_pattern + r"(.+?)(?=\n•|\n[A-Z][a-z]+ |\Z)", text, re.S)
        return normalize_whitespace(m.group(1)) if m else ""

    @staticmethod
    def _extract_section(text: str, heading: str, stop_headings: list[str]) -> str:
        pattern = rf"{re.escape(heading)}\s*\n(.*?)(?="
        stops = "|".join(re.escape(h) for h in stop_headings)
        pattern += rf"(?:{stops})|\Z)"
        m = re.search(pattern, text, re.S | re.I)
        return normalize_whitespace(m.group(1)) if m else ""
