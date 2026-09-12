import time
import logging
from typing import List, Dict, Optional, Any

from src.agents.base import BaseAgent
from src.domain.enums import WorkflowStage
from src.domain.models import (
    TargetCandidate,
    EvidenceItem,
    DruggabilityProfile,
    ExperimentalRecord,
    RankedTarget,
)
from src.domain.state import ResearchGraphState
from src.engine.scoring import TargetScoringEngine

logger = logging.getLogger(__name__)


class TargetRankingAgent(BaseAgent):
    """
    Target Ranking & Prioritization Agent.
    
    RESPONSIBILITIES:
    - Combines multi-modal evidence into an explainable, transparent target ranking.
    - Executes deterministic multi-criteria scoring outside of the LLM.
    - Documents individual score components, penalties, and confidence metrics.
    - Never generates arbitrary black-box numbers or hallucinated rankings.
    """

    def __init__(
        self,
        scoring_engine: Optional[TargetScoringEngine] = None,
        agent_name: str = "TargetRankingAgent",
    ):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.TARGET_RANKING)
        self.scoring_engine = scoring_engine or TargetScoringEngine()

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Ranks all candidate targets deterministically using structured evidence and tractability.
        """
        start_time = time.monotonic()
        identified_targets_raw = state.get("identified_targets", {})
        evidence_records_raw = state.get("evidence_records", [])
        druggability_raw = state.get("druggability_assessments", {})
        experimental_raw = state.get("experimental_data_matches", {})

        if not identified_targets_raw:
            self.record_trace(
                state=state,
                input_summary="No targets available to rank.",
                output_summary="Target ranking completed with 0 ranked targets.",
                tool_calls=["rank_targets()"],
                duration_ms=(time.monotonic() - start_time) * 1000.0,
                status="degraded",
                notes="No identified targets to rank.",
            )
            state["target_rankings"] = []
            state["current_stage"] = self.stage.value
            return state

        # Deserialize objects
        all_evidence: List[EvidenceItem] = []
        for r in evidence_records_raw:
            try:
                all_evidence.append(EvidenceItem(**r))
            except Exception as e:
                logger.warning("Skipping malformed evidence item in ranking: %s", e)

        druggability_profiles: Dict[str, DruggabilityProfile] = {}
        for s, p_dict in druggability_raw.items():
            try:
                druggability_profiles[s] = DruggabilityProfile(**p_dict)
            except Exception:
                pass

        experimental_records_map: Dict[str, List[ExperimentalRecord]] = {}
        for s, recs in experimental_raw.items():
            parsed_recs = []
            for r in recs:
                try:
                    parsed_recs.append(ExperimentalRecord(**r))
                except Exception:
                    pass
            experimental_records_map[s] = parsed_recs

        ranked_targets: List[RankedTarget] = []

        for sym, cand_dict in identified_targets_raw.items():
            try:
                candidate = TargetCandidate(**cand_dict)
            except Exception:
                candidate = TargetCandidate(target_symbol=sym, disease_name=state.get("disease_name", ""))

            sym_evidence = [ev for ev in all_evidence if ev.target_symbol == sym]
            sym_tractability = druggability_profiles.get(sym)
            sym_exp = experimental_records_map.get(sym, [])

            # Get Open Targets overall score from evidence if available
            ot_score = None
            for ev in sym_evidence:
                if ev.source_database == "OpenTargets" and ev.confidence_score > 0:
                    ot_score = ev.confidence_score
                    break

            ranked = self.scoring_engine.rank_target(
                target=candidate,
                evidence_items=sym_evidence,
                druggability_profile=sym_tractability,
                experimental_records=sym_exp,
                open_targets_overall_score=ot_score,
            )
            ranked_targets.append(ranked)

        # Sort deterministically by overall_priority_score descending
        ranked_targets.sort(key=lambda t: t.overall_priority_score, reverse=True)

        state["target_rankings"] = [r.model_dump() for r in ranked_targets]
        state["current_stage"] = self.stage.value

        duration_ms = (time.monotonic() - start_time) * 1000.0

        self.record_trace(
            state=state,
            input_summary=f"Ranking {len(identified_targets_raw)} targets using {len(all_evidence)} evaluated evidence records",
            output_summary=f"Successfully ranked {len(ranked_targets)} targets deterministically.",
            tool_calls=["deterministic_target_scoring()"],
            duration_ms=duration_ms,
            status="success",
            notes="Deterministic composite prioritization executed across all evidence dimensions.",
        )

        return state
