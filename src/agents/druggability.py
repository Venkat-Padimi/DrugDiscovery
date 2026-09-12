import time
import logging
from typing import Dict, Optional, Any

from src.agents.base import BaseAgent
from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.domain.enums import WorkflowStage, TractabilityModality, TractabilityBucket, DataOrigin
from src.domain.models import DruggabilityProfile, DruggabilityModalityDetail
from src.domain.normalization import normalizer, GeneIdentifierNormalizer
from src.domain.state import ResearchGraphState

logger = logging.getLogger(__name__)


class DruggabilityAgent(BaseAgent):
    """
    Druggability & Tractability Assessment Agent.
    
    RESPONSIBILITIES:
    - Evaluates therapeutic tractability across modalities (Small Molecule, Antibody, PROTAC).
    - Uses verified Open Targets tractability evidence rather than ungrounded LLM opinions.
    - Clearly distinguishes external clinical/ChEMBL precedence from platform laboratory assays.
    - Robustly handles targets with missing, partial, or unannotated tractability.
    """

    def __init__(
        self,
        open_targets_client: Optional[OpenTargetsClient] = None,
        gene_normalizer: Optional[GeneIdentifierNormalizer] = None,
        agent_name: str = "DruggabilityAgent",
    ):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.TRACTABILITY_ASSESSMENT)
        self.ot_client = open_targets_client or OpenTargetsClient()
        self.normalizer = gene_normalizer or normalizer

    def evaluate_target_tractability(
        self, target_symbol: str, ensembl_id: Optional[str] = None
    ) -> DruggabilityProfile:
        """
        Retrieves and normalizes tractability for a single target symbol.
        """
        resolved_ensembl = ensembl_id or self.normalizer.get_known_ensembl_id(target_symbol)

        if not resolved_ensembl:
            return DruggabilityProfile(
                target_symbol=target_symbol,
                overall_tractability_score=25.0,
                summary_rationale="Incomplete tractability data: unmapped Ensembl ID.",
            )

        try:
            profile = self.ot_client.get_target_tractability(resolved_ensembl, target_symbol)
            if isinstance(profile, DruggabilityProfile):
                return profile
            return DruggabilityProfile(
                target_symbol=target_symbol,
                overall_tractability_score=25.0,
                summary_rationale="Unassessed tractability fallback.",
            )
        except OpenTargetsApiError as e:
            logger.warning("Open Targets tractability lookup failed for %s: %s", target_symbol, e)
            return DruggabilityProfile(
                target_symbol=target_symbol,
                overall_tractability_score=30.0,
                summary_rationale=f"Tractability query degraded due to Open Targets API error: {e}",
            )

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Runs druggability assessments for all identified targets in state.
        """
        start_time = time.monotonic()
        identified_targets = state.get("identified_targets", {})
        tool_calls = []

        if not identified_targets:
            self.record_trace(
                state=state,
                input_summary="No identified targets in state.",
                output_summary="Tractability assessment completed with 0 targets.",
                tool_calls=["assess_tractability()"],
                duration_ms=(time.monotonic() - start_time) * 1000.0,
                status="degraded",
                notes="No targets available for druggability assessment.",
            )
            state["current_stage"] = self.stage.value
            return state

        druggability_dict: Dict[str, DruggabilityProfile] = {}

        for sym, cand_dict in identified_targets.items():
            ensembl_id = cand_dict.get("ensembl_id")
            tool_calls.append(f"open_targets.get_target_tractability('{sym}')")
            profile = self.evaluate_target_tractability(sym, ensembl_id)
            druggability_dict[sym] = profile

        state["druggability_assessments"] = {
            s: p.model_dump() for s, p in druggability_dict.items()
        }
        state["current_stage"] = self.stage.value

        duration_ms = (time.monotonic() - start_time) * 1000.0

        modalities_summary = sum(len(p.modalities) for p in druggability_dict.values())
        self.record_trace(
            state=state,
            input_summary=f"Assessing tractability for {len(identified_targets)} candidate targets",
            output_summary=f"Evaluated {len(druggability_dict)} target druggability profiles with {modalities_summary} modality annotations.",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
            status="success",
            notes="Tractability profiles synthesized across Small Molecule, Antibody, and PROTAC modalities.",
        )

        return state
