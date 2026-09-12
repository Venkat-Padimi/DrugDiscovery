import pytest
from unittest.mock import MagicMock

from src.agents.supervisor import SupervisorAgent
from src.agents.literature import LiteratureSearchAgent
from src.agents.target_id import TargetIdentificationAgent
from src.agents.compound import CompoundScreeningAgent
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.state import create_initial_state
from src.engine.workflow import build_research_graph, ResearchWorkflowRunner


@pytest.fixture
def sample_papers_fixture():
    return [
        {
            "pmid": "31234567",
            "pmcid": "PMC6589012",
            "doi": "10.1038/s41586-019-1234-5",
            "title": "Microglial TREM2 activation restores cognitive deficits",
            "abstract": "Targeting TREM2 represents a promising immunotherapeutic approach.",
            "authors": ["Smith J", "Doe J"],
            "journal": "Nature",
            "publication_year": 2019,
            "mesh_terms": ["Alzheimer Disease", "Receptors, Immunologic"],
            "citation": {
                "pmid": "31234567",
                "pmcid": "PMC6589012",
                "doi": "10.1038/s41586-019-1234-5",
                "title": "Microglial TREM2 activation restores cognitive deficits",
                "authors": ["Smith J", "Doe J"],
                "journal": "Nature",
                "publication_year": 2019,
            },
            "data_origin": "literature_retrieval",
        }
    ]


@pytest.fixture
def mock_lit_agent(sample_papers_fixture):
    agent = MagicMock(spec=LiteratureSearchAgent)
    agent.agent_name = "LiteratureSearchAgent"
    agent.stage = WorkflowStage.LITERATURE_SEARCH

    def mock_run(state):
        state["retrieved_papers"] = sample_papers_fixture
        state["literature_search_queries"] = ["Alzheimer AND target"]
        state["paper_dois_or_pmids"] = ["31234567"]
        state["current_stage"] = WorkflowStage.LITERATURE_SEARCH.value
        state["audit_trace"].append({
            "agent_name": "LiteratureSearchAgent",
            "stage": WorkflowStage.LITERATURE_SEARCH,
            "input_summary": "Queries formulated",
            "output_summary": "1 paper retrieved",
            "tool_calls": ["search_pubmed()"],
            "status": "success",
            "duration_ms": 10.0,
        })
        return state

    agent.run.side_effect = mock_run
    return agent


@pytest.fixture
def mock_target_agent():
    agent = MagicMock(spec=TargetIdentificationAgent)
    agent.agent_name = "TargetIdentificationAgent"
    agent.stage = WorkflowStage.TARGET_IDENTIFICATION

    def mock_run(state):
        state["identified_targets"] = {
            "TREM2": {
                "target_symbol": "TREM2",
                "target_name": "triggering receptor expressed on myeloid cells 2",
                "ensembl_id": "ENSG00000095977",
                "disease_name": state.get("disease_name", "Alzheimer's disease"),
            }
        }
        state["evidence_records"] = [
            {
                "evidence_id": "EV-001",
                "target_symbol": "TREM2",
                "target_ensembl_id": "ENSG00000095977",
                "disease_name": "Alzheimer's disease",
                "evidence_type": "literature_cooccurrence",
                "causality_level": "functional_association",
                "study_type": "in_vitro_cellular",
                "confidence_score": 0.85,
                "data_origin": "literature_retrieval",
                "source_database": "PubMed",
                "citation": {
                    "pmid": "31234567",
                    "title": "Microglial TREM2 activation restores cognitive deficits",
                    "doi": "10.1038/s41586-019-1234-5",
                },
                "extracted_statement": "Statement linking TREM2 to Alzheimer's pathology.",
            },
            {
                "evidence_id": "EV-OT-001",
                "target_symbol": "TREM2",
                "target_ensembl_id": "ENSG00000095977",
                "disease_name": "Alzheimer's disease",
                "evidence_type": "genetic_association",
                "causality_level": "causal_demonstrated",
                "study_type": "human_gwas",
                "confidence_score": 0.95,
                "data_origin": "experimentally_measured",
                "source_database": "OpenTargets",
                "citation": {
                    "title": "GWAS locus for Alzheimer's",
                },
                "extracted_statement": "Genetic association with Alzheimer's disease.",
            }
        ]
        state["current_stage"] = WorkflowStage.TARGET_IDENTIFICATION.value
        state["audit_trace"].append({
            "agent_name": "TargetIdentificationAgent",
            "stage": WorkflowStage.TARGET_IDENTIFICATION,
            "input_summary": "Extracted targets",
            "output_summary": "1 target identified",
            "tool_calls": ["open_targets.get_associated_targets()"],
            "status": "success",
            "duration_ms": 15.0,
        })
        return state

    agent.run.side_effect = mock_run
    return agent


@pytest.fixture
def mock_druggability_agent():
    from src.agents.druggability import DruggabilityAgent
    agent = MagicMock(spec=DruggabilityAgent)
    agent.agent_name = "DruggabilityAgent"
    agent.stage = WorkflowStage.TRACTABILITY_ASSESSMENT

    def mock_run(state):
        state["druggability_assessments"] = {
            "TREM2": {
                "target_symbol": "TREM2",
                "overall_tractability_score": 90.0,
                "has_small_molecule_binder": True,
                "has_approved_drug": False,
                "modalities": {},
                "safety_concerns": [],
            }
        }
        state["current_stage"] = WorkflowStage.TRACTABILITY_ASSESSMENT.value
        return state

    agent.run.side_effect = mock_run
    return agent


class TestResearchWorkflow:

    def test_full_workflow_end_to_end(self, mock_lit_agent, mock_target_agent, mock_druggability_agent):
        supervisor = SupervisorAgent()
        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=mock_lit_agent,
            target_agent=mock_target_agent,
            druggability_agent=mock_druggability_agent,
        )

        initial_state = create_initial_state(
            session_id="SESS-E2E-01",
            research_question="Identify promising therapeutic targets for Alzheimer's disease.",
            disease_name="Alzheimer's disease",
        )

        final_state = runner.run(initial_state)

        # 1. Pipeline status and stage
        assert final_state["status"] == "completed"
        assert final_state["current_stage"] == WorkflowStage.COMPLETED.value
        assert final_state["step_count"] >= 3

        # 2. Retrieved papers & targets
        assert len(final_state["retrieved_papers"]) == 1
        assert "TREM2" in final_state["identified_targets"]

        # 3. Deterministic rankings & executive summary
        assert len(final_state["target_rankings"]) == 1
        assert final_state["target_rankings"][0]["overall_priority_score"] > 60.0
        assert final_state["executive_summary"] is not None
        assert "TREM2" in final_state["executive_summary"]

        # 4. Observability: Audit trace has events from all stages
        agents_in_trace = [e["agent_name"] for e in final_state["audit_trace"]]
        assert "SupervisorAgent" in agents_in_trace
        assert "LiteratureSearchAgent" in agents_in_trace
        assert "TargetIdentificationAgent" in agents_in_trace

    def test_workflow_routing_empty_literature(self, mock_target_agent):
        supervisor = SupervisorAgent()

        # Mock literature agent returning 0 papers
        empty_lit_agent = MagicMock(spec=LiteratureSearchAgent)
        empty_lit_agent.agent_name = "LiteratureSearchAgent"
        empty_lit_agent.stage = WorkflowStage.LITERATURE_SEARCH

        def empty_lit_run(state):
            state["retrieved_papers"] = []
            state["current_stage"] = WorkflowStage.LITERATURE_SEARCH.value
            return state

        empty_lit_agent.run.side_effect = empty_lit_run

        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=empty_lit_agent,
            target_agent=mock_target_agent,
        )

        initial_state = create_initial_state(
            session_id="SESS-ROUTING-01",
            research_question="Target search with empty literature",
            disease_name="Rare Condition",
        )

        final_state = runner.run(initial_state)

        # Verified routed via direct fallback node
        trace_summaries = [e.get("output_summary", "") for e in final_state["audit_trace"]]
        assert any("direct Open Targets query fallback" in s for s in trace_summaries)
        assert final_state["status"] == "completed"
        assert "TREM2" in final_state["identified_targets"]

    def test_workflow_routing_insufficient_evidence(self):
        supervisor = SupervisorAgent()

        # Both agents return empty
        empty_lit = MagicMock(spec=LiteratureSearchAgent)
        empty_lit.run.side_effect = lambda s: {**s, "retrieved_papers": []}

        empty_target = MagicMock(spec=TargetIdentificationAgent)
        empty_target.run.side_effect = lambda s: {**s, "identified_targets": {}, "target_rankings": []}

        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=empty_lit,
            target_agent=empty_target,
        )

        initial_state = create_initial_state(
            session_id="SESS-ROUTING-EMPTY",
            research_question="Unknown disease query",
            disease_name="Unknown Disease",
        )

        final_state = runner.run(initial_state)

        # Verified routed via insufficient evidence node
        assert final_state["status"] == "degraded"
        assert any(e.get("error_type") == "InsufficientEvidence" for e in final_state["errors"])
        assert "insufficient evidence" in final_state["executive_summary"].lower()

    def test_loop_protection_max_steps(self, sample_papers_fixture):
        supervisor = SupervisorAgent()
        lit_mock = MagicMock(spec=LiteratureSearchAgent)
        lit_mock.run.side_effect = lambda s: {**s, "retrieved_papers": sample_papers_fixture}

        target_mock = MagicMock(spec=TargetIdentificationAgent)
        target_mock.run.side_effect = lambda s: {**s, "identified_targets": {"T1": {}}}

        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=lit_mock,
            target_agent=target_mock,
        )

        # Artificially limit max_steps to 1
        initial_state = create_initial_state(
            session_id="SESS-LOOP-PROT",
            research_question="Loop test",
            disease_name="Alzheimer's",
            max_steps=1,
        )

        final_state = runner.run(initial_state)

        # Graph halted safely without infinite loop
        assert final_state["step_count"] <= 3

    def test_provenance_preservation_across_transitions(
        self, sample_papers_fixture, mock_lit_agent, mock_target_agent, mock_druggability_agent
    ):
        supervisor = SupervisorAgent()
        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=mock_lit_agent,
            target_agent=mock_target_agent,
            druggability_agent=mock_druggability_agent,
        )

        initial_state = create_initial_state(
            session_id="SESS-PROV-01",
            research_question="Provenance verification in Alzheimer's",
            disease_name="Alzheimer's disease",
        )

        final_state = runner.run(initial_state)

        # Verify publication provenance is intact
        paper = final_state["retrieved_papers"][0]
        assert paper["pmid"] == "31234567"
        assert paper["data_origin"] == DataOrigin.LITERATURE_RETRIEVAL
        assert paper["citation"]["pmid"] == "31234567"
        assert paper["citation"]["doi"] == "10.1038/s41586-019-1234-5"

        # Verify ranked target links to key PMID
        top_ranked = final_state["target_rankings"][0]
        assert "31234567" in top_ranked["key_pmids"]

    def test_workflow_with_compound_screening_integration(
        self, sample_papers_fixture, mock_lit_agent, mock_target_agent, mock_druggability_agent
    ):
        supervisor = SupervisorAgent()
        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=mock_lit_agent,
            target_agent=mock_target_agent,
            druggability_agent=mock_druggability_agent,
        )

        initial_state = create_initial_state(
            session_id="SESS-CMPD-WF-01",
            research_question="Investigate TREM2 compound screening",
            disease_name="Alzheimer's disease",
            enable_compound_screening=True,
        )

        final_state = runner.run(initial_state)

        assert final_state["status"] == "completed"
        assert "known_active_compounds" in final_state
        assert "compound_screenings" in final_state
        # TREM2 should have screened compounds
        assert "TREM2" in final_state["compound_screenings"]
        for pred in final_state["compound_screenings"]["TREM2"]:
            assert pred["data_origin"] == DataOrigin.COMPUTATIONAL_PREDICTION
            assert "Computational simulation prediction" in pred["disclaimer"]

        agents_in_trace = [e["agent_name"] for e in final_state["audit_trace"]]
        assert "CompoundScreeningAgent" in agents_in_trace

    def test_workflow_screening_disabled_bypasses_node(
        self, sample_papers_fixture, mock_lit_agent, mock_target_agent, mock_druggability_agent
    ):
        supervisor = SupervisorAgent()
        runner = ResearchWorkflowRunner(
            supervisor_agent=supervisor,
            literature_agent=mock_lit_agent,
            target_agent=mock_target_agent,
            druggability_agent=mock_druggability_agent,
        )

        initial_state = create_initial_state(
            session_id="SESS-CMPD-WF-DIS",
            research_question="Investigate with screening disabled",
            disease_name="Alzheimer's disease",
            enable_compound_screening=False,
        )

        final_state = runner.run(initial_state)

        assert final_state["status"] == "completed"
        # Bypassed node: compound screening agent was not in trace
        agents_in_trace = [e["agent_name"] for e in final_state["audit_trace"]]
        assert "CompoundScreeningAgent" not in agents_in_trace

