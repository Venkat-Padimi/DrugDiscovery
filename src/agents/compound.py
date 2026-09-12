import time
import logging
from typing import List, Dict, Optional, Any, Tuple

from src.agents.base import BaseAgent
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.models import CompoundBioactivity, ScreeningPrediction
from src.domain.state import ResearchGraphState
from src.clients.chembl import ChEMBLClient, ChEMBLApiError
from src.engine.screening import CompoundScreeningEngine, PhysicochemicalSimulationEngine

logger = logging.getLogger(__name__)

# Curated reference small-molecule probes for computational screening simulation
BENCHMARK_PROBE_LIBRARY: List[Tuple[str, str]] = [
    ("REF_PROBE_01", "CC(=O)Oc1ccccc1C(=O)O"),  # Acetylsalicylic acid derivative
    ("REF_PROBE_02", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),  # Arylpropionic acid derivative
    ("REF_PROBE_03", "COc1cc2c(cc1OC)C(=O)C(CC1CCN(Cc3ccccc3)CC1)C2"),  # Donepezil piperidine derivative
    ("REF_PROBE_04", "CC1(c2cc(F)ccc2F)N=C(N)c2c1cc(F)cc2"),  # BACE1 inhibitor core scaffold
]


class CompoundScreeningAgent(BaseAgent):
    """
    Compound Screening and Bioactivity Simulation Agent.
    
    SCIENTIFIC RESPONSIBILITIES:
    1. Queries verified empirical bioactivity records from ChEMBL for top-ranked targets.
    2. Strictly categorizes ChEMBL records as DataOrigin.EXPERIMENTALLY_MEASURED.
    3. Executes reproducible computational screening via CompoundScreeningEngine.
    4. Explicitly labels in silico simulations as DataOrigin.COMPUTATIONAL_PREDICTION
       with the mandatory disclaimer:
       'Computational simulation prediction — not experimentally measured.'
    5. Zero fabrication: never invents docking scores, binding affinities, or active molecules.
    6. Non-fatal degradation: API or simulation failures degrade gracefully without halting the pipeline.
    """

    def __init__(
        self,
        chembl_client: Optional[ChEMBLClient] = None,
        screening_engine: Optional[CompoundScreeningEngine] = None,
        agent_name: str = "CompoundScreeningAgent",
    ):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.COMPOUND_SCREENING)
        self.chembl_client = chembl_client or ChEMBLClient()
        self.screening_engine = screening_engine or PhysicochemicalSimulationEngine()

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Executes compound retrieval and screening for top-ranked targets.
        """
        start_time = time.monotonic()

        # Check whether compound screening is enabled in state
        if not state.get("enable_compound_screening", True):
            self.record_trace(
                state=state,
                input_summary="Compound screening disabled in state configuration.",
                output_summary="Skipped compound screening stage.",
                tool_calls=[],
                duration_ms=0.0,
                status="success",
                notes="Compound screening disabled per user/pipeline configuration.",
            )
            state["current_stage"] = self.stage.value
            return state

        # Identify targets to screen (top N prioritized targets)
        top_n = state.get("top_n_targets_to_screen", 5)
        ranked_targets = state.get("target_rankings", [])

        targets_to_screen: List[str] = []
        if ranked_targets:
            for t in ranked_targets[:top_n]:
                sym = t.get("target_symbol")
                if sym and sym not in targets_to_screen:
                    targets_to_screen.append(sym)
        else:
            identified = state.get("identified_targets", {})
            targets_to_screen = list(identified.keys())[:top_n]

        if not targets_to_screen:
            self.record_trace(
                state=state,
                input_summary="No targets available for compound screening.",
                output_summary="0 targets screened.",
                tool_calls=[],
                duration_ms=(time.monotonic() - start_time) * 1000.0,
                status="degraded",
                notes="No prioritized or identified targets present in state.",
            )
            state["known_active_compounds"] = {}
            state["compound_screenings"] = {}
            state["current_stage"] = self.stage.value
            return state

        if "known_active_compounds" not in state:
            state["known_active_compounds"] = {}
        if "compound_screenings" not in state:
            state["compound_screenings"] = {}

        total_measured = 0
        total_predictions = 0

        for target_symbol in targets_to_screen:
            # 1. Retrieve empirical bioactivities from ChEMBL
            measured_activities: List[CompoundBioactivity] = []
            try:
                target_chembl_id = self.chembl_client.search_target(target_symbol)
                if target_chembl_id:
                    measured_activities = self.chembl_client.get_target_bioactivities(
                        target_chembl_id=target_chembl_id,
                        target_symbol=target_symbol,
                        limit=10,
                    )
            except Exception as exc:
                logger.warning("ChEMBL bioactivity retrieval error for '%s': %s", target_symbol, exc)
                self.record_error(
                    state=state,
                    error_type="ChEMBLApiError",
                    message=f"ChEMBL retrieval failed for target {target_symbol}: {exc}",
                    is_fatal=False,
                    degradation_applied=True,
                )
                measured_activities = []

            state["known_active_compounds"][target_symbol] = [
                m.model_dump() for m in measured_activities
            ]
            total_measured += len(measured_activities)

            # 2. Select candidate molecules for in silico screening
            molecules_to_screen: List[Tuple[str, str]] = []
            for act in measured_activities:
                if act.smiles:
                    molecules_to_screen.append((act.compound_id, act.smiles))

            # Supplement with benchmark reference probes if fewer than 2 molecules
            if len(molecules_to_screen) < 2:
                for probe_id, probe_smiles in BENCHMARK_PROBE_LIBRARY:
                    cid = f"{probe_id}_{target_symbol}"
                    if not any(m[0] == cid for m in molecules_to_screen):
                        molecules_to_screen.append((cid, probe_smiles))

            # 3. Execute computational screening predictions
            predictions: List[ScreeningPrediction] = []
            for cid, smiles in molecules_to_screen[:8]:
                try:
                    pred = self.screening_engine.predict_affinity(
                        target_symbol=target_symbol,
                        smiles=smiles,
                        compound_id=cid,
                    )
                    # Enforce strict scientific integrity rules
                    if pred.data_origin != DataOrigin.COMPUTATIONAL_PREDICTION:
                        pred.data_origin = DataOrigin.COMPUTATIONAL_PREDICTION
                    if not pred.disclaimer:
                        pred.disclaimer = "Computational simulation prediction — not experimentally measured."

                    predictions.append(pred)
                except Exception as exc:
                    logger.warning("Screening simulation failure for '%s' against '%s': %s", cid, target_symbol, exc)
                    self.record_error(
                        state=state,
                        error_type="ScreeningSimulationError",
                        message=f"Simulation failed for compound {cid} on target {target_symbol}: {exc}",
                        is_fatal=False,
                        degradation_applied=True,
                    )

            state["compound_screenings"][target_symbol] = [
                p.model_dump() for p in predictions
            ]
            total_predictions += len(predictions)

        duration_ms = (time.monotonic() - start_time) * 1000.0

        targets_joined = ", ".join(targets_to_screen)
        self.record_trace(
            state=state,
            input_summary=f"Screening candidate targets: {targets_joined}",
            output_summary=(
                f"Retrieved {total_measured} measured bioactivities from ChEMBL; "
                f"generated {total_predictions} in silico screening predictions."
            ),
            tool_calls=[
                "chembl.search_target()",
                "chembl.get_target_bioactivities()",
                "screening_engine.predict_affinity()",
            ],
            duration_ms=duration_ms,
            status="success",
            notes=(
                "Empirically measured bioactivities strictly segregated from in silico predictions. "
                "All computational predictions carry mandatory non-experimental disclaimers."
            ),
        )

        state["current_stage"] = self.stage.value
        return state
