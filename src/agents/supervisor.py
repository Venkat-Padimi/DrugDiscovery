import re
import time
from typing import Dict, List, Optional, Any

from src.agents.base import BaseAgent
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.state import ResearchGraphState


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent coordinating specialized research agents in the LangGraph workflow.
    
    RESPONSIBILITIES:
    - Analyzes the research question and plans the investigation sequence.
    - Decomposes disease queries and delegates tasks to specialized agents.
    - Monitors evidence completeness, data origin boundaries, and contradictions.
    - Synthesizes findings into an explainable executive overview.
    - Never invents citations, binding values, or scientific scores.
    """

    def __init__(self, agent_name: str = "SupervisorAgent"):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.INITIALIZATION)

    def extract_disease_name_from_question(self, question: str) -> str:
        """Heuristic fallback extraction of disease entity from research query."""
        patterns = [
            r"(?:for|in|of|targeting|treating)\s+([A-Za-z0-9'\s\-]+?)(?:\.|\?|,|$)",
            r"(?:targets?\s+for)\s+([A-Za-z0-9'\s\-]+)",
        ]
        for pat in patterns:
            m = re.search(pat, question, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # Clean trailing filler words
                cleaned = re.sub(r"\b(therapeutic|promising|novel|potential|candidate|drug|disease|targets?)\b", "", extracted, flags=re.IGNORECASE).strip()
                if len(cleaned) >= 3:
                    return cleaned
        return question.strip()

    def plan(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Initializes and plans the multi-agent investigation.
        """
        start_time = time.monotonic()
        question = state.get("research_question", "")
        disease_name = state.get("disease_name", "")

        # If disease name was not explicitly provided, extract from question
        if not disease_name and question:
            disease_name = self.extract_disease_name_from_question(question)
            state["disease_name"] = disease_name

        planned_stages = [
            WorkflowStage.LITERATURE_SEARCH.value,
            WorkflowStage.TARGET_IDENTIFICATION.value,
            WorkflowStage.TRACTABILITY_ASSESSMENT.value,
            WorkflowStage.EXPERIMENTAL_MATCHING.value,
            WorkflowStage.TARGET_RANKING.value,
            WorkflowStage.REPORTING.value,
        ]

        state["current_stage"] = WorkflowStage.INITIALIZATION.value
        state["status"] = "in_progress"

        duration_ms = (time.monotonic() - start_time) * 1000.0

        self.record_trace(
            state=state,
            input_summary=f"Question: '{question}', Disease: '{disease_name}'",
            output_summary=f"Planned {len(planned_stages)} stages: {', '.join(planned_stages)}",
            tool_calls=["plan_investigation()"],
            duration_ms=duration_ms,
            status="success",
            notes="Investigation plan formulated. Ready for Literature Search Agent delegation.",
        )

        return state

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """Default run delegates to plan."""
        return self.plan(state)

    def synthesize(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Synthesizes the workflow findings into an executive summary without fabricating data.
        """
        start_time = time.monotonic()
        rankings = state.get("target_rankings", [])
        disease_name = state.get("disease_name", "Target Disease")
        errors = state.get("errors", [])

        if not rankings:
            summary = (
                f"Investigation for '{disease_name}' completed with insufficient evidence. "
                "No candidate targets met the threshold for high-confidence prioritization."
            )
            state["executive_summary"] = summary
            state["current_stage"] = WorkflowStage.COMPLETED.value
            state["status"] = "degraded" if errors else "completed"
            return state

        top_targets = rankings[:3]
        target_summaries = []
        for idx, t in enumerate(top_targets, start=1):
            sym = t.get("target_symbol", "")
            score = t.get("overall_priority_score", 0.0)
            tier = t.get("confidence_tier", "medium")
            pmids_count = len(t.get("key_pmids", []))
            strengths = "; ".join(t.get("strengths", [])) or "Identified via multi-modal association."
            target_summaries.append(
                f"{idx}. {sym} (Priority: {score:.1f}/100, Confidence: {tier.upper()}): {strengths} [PMID evidence count: {pmids_count}]"
            )

        summary_text = (
            f"Autonomous multi-agent investigation completed for '{disease_name}'.\n\n"
            f"Top Prioritized Therapeutic Targets:\n" + "\n".join(target_summaries) + "\n\n"
            "All candidate targets are scored using deterministic multi-criteria weighting. "
            "Internal experimental data reflects synthetic demonstration assays. "
            "Empirical laboratory validation is required before therapeutic development."
        )

        state["executive_summary"] = summary_text
        state["current_stage"] = WorkflowStage.COMPLETED.value
        state["status"] = "degraded" if any(e.get("degradation_applied") for e in errors) else "completed"

        duration_ms = (time.monotonic() - start_time) * 1000.0

        self.record_trace(
            state=state,
            input_summary=f"Ranked targets: {len(rankings)}",
            output_summary=f"Executive synthesis compiled for top {len(top_targets)} targets.",
            tool_calls=["supervisor_synthesize()"],
            duration_ms=duration_ms,
            status="success",
            notes="Final executive synthesis complete.",
        )

        return state
