from __future__ import annotations

import re
from dataclasses import dataclass

from config import AppConfig
from data_pipeline.io_utils import read_json
from rag.retriever import extract_query_terms
from schemas import SourceAttribution, ToolResult
from tools.base import ActionTool, ToolParameter


GENERIC_HEADINGS = {
    "program description",
    "program dates",
    "program dates & registration",
    "program dates and registration",
    "program registration",
    "program registration dates and information",
    "program eligibility",
    "program format & location",
    "format & location",
    "contacts",
    "contact",
    "newsletter",
    "programs & events",
}


@dataclass(slots=True)
class EventEntry:
    name: str
    summary: str
    dates: str
    section: str
    url: str


class EventRecommendationTool(ActionTool):
    name = "event_recommendation"
    description = "Recommend relevant hub sessions or events."
    parameters = [
        ToolParameter(
            name="topic",
            description="The student's topic of interest.",
            follow_up_question="What topic are you interested in for events or sessions?",
        )
    ]

    def __init__(self, config: AppConfig) -> None:
        self.cleaned_docs = read_json(config.paths.cleaned_docs_path, default=[])

    def _infer_program_name(self, heading: str, content: str, fallback: str = "") -> str:
        clean_heading = heading.strip()
        if clean_heading and clean_heading.lower() not in GENERIC_HEADINGS:
            return clean_heading

        patterns = [
            r'Introducing CIE.?s new “([^”]+)” series',
            r'In this new virtual pre-arrival session, ([^,]+),',
            r'CIE.?s “([^”]+)” program',
            r'CIE.?s “([^”]+)” series',
            r'Join us for ([^,]+), an orientation',
            r'Swing by the ([^.]+?) on',
            r'Then try your hand at ([^,]+),',
            r'The ([A-Z][A-Za-z0-9 &:+\-]+?) aims to provide',
            r'Join us for a fun board game night! “([^”]+)”',
            r'Discover the power of words in ([^,]+),',
            r'Join us for “([^”]+)”',
            r'([A-Z][A-Za-z0-9 &:+\-]+?) is a one-stop shop health services virtual information-session',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split()).strip(" .")

        if fallback:
            return fallback
        return "Programs & Events"

    def _programs_doc(self) -> dict | None:
        for doc in self.cleaned_docs:
            if doc.get("title", "").strip().lower() == "programs & events":
                return doc
        return None

    def _build_event_entries(self) -> list[EventEntry]:
        doc = self._programs_doc()
        if not doc:
            return []

        entries: list[EventEntry] = []
        current_name = "Programs & Events"
        current_summary = ""

        for section in doc.get("sections", []):
            heading = (section.get("heading") or "").strip()
            content = " ".join((section.get("content") or "").split())
            lower_heading = heading.lower()

            if not content:
                continue

            if "description" in lower_heading or lower_heading in {"programs & events", "health services overview", "cultural adjustment workshop"}:
                current_name = self._infer_program_name(heading, content, fallback=current_name)
                current_summary = content
                continue

            if "date" in lower_heading:
                name = self._infer_program_name(heading, current_summary, fallback=current_name)
                if name == "Programs & Events":
                    continue
                entries.append(
                    EventEntry(
                        name=name,
                        summary=current_summary[:320].strip(),
                        dates=content,
                        section=heading or "Program dates",
                        url=str(doc.get("url", "")),
                    )
                )

        unique: list[EventEntry] = []
        seen: set[str] = set()
        for entry in entries:
            key = entry.name.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(entry)
        return unique

    def _rank_entries(self, topic: str, entries: list[EventEntry]) -> list[EventEntry]:
        query_terms = extract_query_terms(topic)
        if not query_terms or query_terms == {"events"} or query_terms == {"event"}:
            return entries[:3]

        scored: list[tuple[int, EventEntry]] = []
        for entry in entries:
            haystack = f"{entry.name} {entry.summary} {entry.dates}".lower()
            score = sum(1 for term in query_terms if term in haystack)
            score += sum(2 for term in query_terms if term in entry.name.lower())
            if score > 0:
                scored.append((score, entry))

        if not scored:
            return entries[:3]

        scored.sort(key=lambda item: item[0], reverse=True)
        ranked = [entry for _, entry in scored[:3]]
        ranked_names = {entry.name for entry in ranked}
        for entry in entries:
            if entry.name in ranked_names:
                continue
            ranked.append(entry)
            ranked_names.add(entry.name)
            if len(ranked) >= 3:
                break
        return ranked[:3]

    def run(self, params: dict[str, str]) -> ToolResult:
        topic = params.get("topic", "").strip()
        entries = self._build_event_entries()
        if not entries:
            return ToolResult(tool_name=self.name, output="I don't know")

        recommendations = self._rank_entries(topic, entries)
        if not recommendations:
            return ToolResult(tool_name=self.name, output="I don't know")

        lines = []
        sources: list[SourceAttribution] = []
        for entry in recommendations:
            summary = entry.summary.rstrip(".")
            if len(summary) > 180:
                summary = summary[:177].rstrip() + "..."
            lines.append(f"- **{entry.name}**: {summary}. **Dates:** {entry.dates}")
            sources.append(
                SourceAttribution(
                    title="Programs & Events",
                    url=entry.url,
                    section=entry.section,
                )
            )

        output = "Here are some relevant CIE events and sessions:\n\n" + "\n".join(lines)
        return ToolResult(tool_name=self.name, output=output, sources=sources)
