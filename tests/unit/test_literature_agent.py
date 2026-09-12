import pytest
from unittest.mock import MagicMock

from src.agents.literature import LiteratureSearchAgent
from src.clients.ncbi_pubmed import NcbiPubMedClient, NcbiApiError
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.models import PubMedArticle, CitationReference
from src.domain.state import create_initial_state


@pytest.fixture
def mock_articles():
    return [
        PubMedArticle(
            pmid="31234567",
            pmcid="PMC6589012",
            doi="10.1038/s41586-019-1234-5",
            title="Microglial TREM2 activation restores cognitive deficits",
            abstract="Targeting TREM2 represents a promising immunotherapeutic approach.",
            authors=["Smith J", "Doe J"],
            journal="Nature",
            publication_year=2019,
            mesh_terms=["Alzheimer Disease", "Receptors, Immunologic"],
            citation=CitationReference(
                pmid="31234567",
                pmcid="PMC6589012",
                doi="10.1038/s41586-019-1234-5",
                title="Microglial TREM2 activation restores cognitive deficits",
                authors=["Smith J", "Doe J"],
                journal="Nature",
                publication_year=2019,
            ),
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
        ),
        PubMedArticle(
            pmid="32345678",
            doi="10.1126/science.abc1234",
            title="BACE1 inhibition and amyloid processing in clinical development",
            abstract="Small molecule inhibitors of BACE1 decrease amyloid-beta synthesis.",
            authors=["Johnson K"],
            journal="Science",
            publication_year=2020,
            mesh_terms=["Alzheimer Disease", "Amyloid Precursor Protein Secretases"],
            citation=CitationReference(
                pmid="32345678",
                doi="10.1126/science.abc1234",
                title="BACE1 inhibition and amyloid processing in clinical development",
                authors=["Johnson K"],
                journal="Science",
                publication_year=2020,
            ),
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
        ),
    ]


class TestLiteratureSearchAgent:

    def test_generate_search_queries(self):
        agent = LiteratureSearchAgent(client=MagicMock())
        queries = agent.generate_search_queries("Alzheimer's disease", "Find targets")
        assert len(queries) >= 2
        assert any("therapeutic target" in q for q in queries)
        assert any("Alzheimer's disease" in q for q in queries)

    def test_run_successful_search_and_state_update(self, mock_articles):
        mock_client = MagicMock(spec=NcbiPubMedClient)
        # 2 queries return overlapping PMIDs
        mock_client.search.side_effect = [
            ["31234567", "32345678"],
            ["32345678", "33456789"],  # 32345678 is duplicate
        ]
        mock_client.fetch_articles_by_pmids.return_value = mock_articles

        agent = LiteratureSearchAgent(client=mock_client)
        state = create_initial_state(
            session_id="SESS-001",
            research_question="Identify targets for Alzheimer's disease",
            disease_name="Alzheimer's disease",
            max_literature_results=10,
        )

        updated_state = agent.run(state)

        # Verify state updates
        assert updated_state["current_stage"] == WorkflowStage.LITERATURE_SEARCH.value
        assert len(updated_state["literature_search_queries"]) >= 2
        assert len(updated_state["retrieved_papers"]) == 2
        assert updated_state["paper_dois_or_pmids"] == ["31234567", "32345678"]

        # Verify audit trace
        assert len(updated_state["audit_trace"]) == 1
        trace = updated_state["audit_trace"][0]
        assert trace["agent_name"] == "LiteratureSearchAgent"
        assert trace["stage"] == WorkflowStage.LITERATURE_SEARCH
        assert trace["status"] == "success"
        assert trace["duration_ms"] >= 0.0

        # Verify client calls: PMIDs deduplicated before efetch
        mock_client.fetch_articles_by_pmids.assert_called_once_with(["31234567", "32345678", "33456789"])

        # Verify provenance preservation on retrieved papers
        for paper in updated_state["retrieved_papers"]:
            assert paper["data_origin"] == "literature_retrieval"
            assert paper["citation"] is not None
            assert paper["pmid"] in ["31234567", "32345678"]

    def test_run_missing_disease_name_handles_gracefully(self):
        mock_client = MagicMock(spec=NcbiPubMedClient)
        agent = LiteratureSearchAgent(client=mock_client)

        state = create_initial_state(
            session_id="SESS-EMPTY",
            research_question="Query with no disease",
            disease_name="",
        )

        updated_state = agent.run(state)
        mock_client.search.assert_not_called()
        assert len(updated_state["errors"]) == 1
        assert updated_state["errors"][0]["error_type"] == "MissingInput"

    def test_run_api_error_records_degradation(self):
        mock_client = MagicMock(spec=NcbiPubMedClient)
        mock_client.search.side_effect = NcbiApiError("NCBI rate limit or connection timeout")

        agent = LiteratureSearchAgent(client=mock_client)
        state = create_initial_state(
            session_id="SESS-ERR",
            research_question="Query with failing client",
            disease_name="Alzheimer's disease",
        )

        updated_state = agent.run(state)
        assert len(updated_state["errors"]) >= 1
        assert updated_state["errors"][0]["error_type"] == "NcbiApiError"
        assert updated_state["errors"][0]["degradation_applied"] is True
        assert len(updated_state["retrieved_papers"]) == 0
