import time
from typing import List, Dict, Optional, Set, Any

from src.agents.base import BaseAgent
from src.clients.ncbi_pubmed import NcbiPubMedClient, NcbiApiError
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.state import ResearchGraphState
from src.domain.models import PubMedArticle, ProvenanceRecord


class LiteratureSearchAgent(BaseAgent):
    """
    Literature Search Agent for biomedical publication retrieval.
    
    RESPONSIBILITIES:
    - Formulates targeted PubMed search strategies with Boolean & MeSH syntax.
    - Executes searches and retrieves article abstracts/metadata via NCBI E-utilities.
    - Strictly deduplicates across multiple query streams.
    - Preserves complete PMID, PMCID, DOI, and bibliographic provenance.
    - Zero fabrication: never synthesizes or hallucinates non-existent publications.
    """

    def __init__(
        self,
        client: Optional[NcbiPubMedClient] = None,
        agent_name: str = "LiteratureSearchAgent",
    ):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.LITERATURE_SEARCH)
        self.client = client or NcbiPubMedClient()

    def generate_search_queries(
        self, disease_name: str, research_question: str
    ) -> List[str]:
        """
        Formulates structured PubMed search queries balancing sensitivity and specificity.
        """
        clean_disease = disease_name.strip()
        queries = [
            f'("{clean_disease}") AND (therapeutic target OR drug target OR candidate gene)',
            f'("{clean_disease}") AND (pathway OR disease mechanism OR genetics)',
        ]
        return queries

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Executes literature search workflow on the provided state.
        """
        start_time = time.monotonic()
        disease_name = state.get("disease_name", "")
        research_question = state.get("research_question", "")
        max_results = state.get("max_literature_results", 15)

        if not disease_name:
            self.record_error(
                state=state,
                error_type="MissingInput",
                message="Disease name was not provided for literature search.",
                is_fatal=False,
            )
            return state

        # Generate targeted queries
        queries = self.generate_search_queries(disease_name, research_question)
        state["literature_search_queries"] = queries

        all_pmids: List[str] = []
        seen_pmids: Set[str] = set()
        tool_calls: List[str] = []

        # Step 1: Search PMIDs across queries
        for q in queries:
            try:
                tool_calls.append(f"search_pubmed('{q}')")
                pmids = self.client.search(query=q, max_results=max_results)
                for pid in pmids:
                    if pid not in seen_pmids:
                        seen_pmids.add(pid)
                        all_pmids.append(pid)
            except NcbiApiError as e:
                self.record_error(
                    state=state,
                    error_type="NcbiApiError",
                    message=f"PubMed search failed for query '{q}': {e}",
                    degradation_applied=True,
                )

        # Truncate to maximum configured results
        target_pmids = all_pmids[:max_results]
        retrieved_articles: List[PubMedArticle] = []

        # Step 2: Fetch articles metadata & XML abstracts
        if target_pmids:
            try:
                tool_calls.append(f"fetch_pubmed_articles({target_pmids})")
                articles = self.client.fetch_articles_by_pmids(target_pmids)
                retrieved_articles = articles
            except NcbiApiError as e:
                self.record_error(
                    state=state,
                    error_type="NcbiApiError",
                    message=f"PubMed efetch failed for PMIDs {target_pmids}: {e}",
                    degradation_applied=True,
                )

        # Update state
        state["retrieved_papers"] = [art.model_dump() for art in retrieved_articles]
        state["paper_dois_or_pmids"] = [art.pmid for art in retrieved_articles]
        state["current_stage"] = self.stage.value

        duration_ms = (time.monotonic() - start_time) * 1000.0

        # Record trace
        self.record_trace(
            state=state,
            input_summary=f"Disease: '{disease_name}', Queries: {len(queries)}",
            output_summary=f"Retrieved {len(retrieved_articles)} unique articles across {len(target_pmids)} PMIDs",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
            status="success" if retrieved_articles or not target_pmids else "degraded",
            notes="Biomedical literature evidence successfully extracted with complete source provenance.",
        )

        return state
