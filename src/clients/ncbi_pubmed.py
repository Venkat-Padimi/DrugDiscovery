import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx

from config.settings import settings
from src.domain.enums import DataOrigin
from src.domain.models import PubMedArticle, CitationReference, ProvenanceRecord

logger = logging.getLogger(__name__)


class NcbiApiError(Exception):
    """Exception raised when an NCBI E-utilities API call fails after retries."""
    pass


class NcbiPubMedClient:
    """
    Dedicated client adapter for NCBI Entrez E-utilities (PubMed/PMC).
    
    COMPLIANCE & RESILIENCE RULES:
    - Automatically provides tool name and email according to NCBI guidelines.
    - Respects NCBI rate limits: <= 3 req/sec without API key, <= 10 req/sec with key.
    - Implements exponential backoff on HTTP 429 and transient 5xx errors.
    - Completely isolated from domain and scoring logic.
    - Zero fabrication: missing or failed calls return clean empty/error states.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        tool: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        http_client: Optional[httpx.Client] = None,
        rate_limit_delay: Optional[float] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.email = email or settings.ncbi_email
        self.tool = tool or settings.ncbi_tool
        self.api_key = api_key or settings.ncbi_api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Determine rate limit interval
        if rate_limit_delay is not None:
            self.min_interval = rate_limit_delay
        elif self.api_key:
            self.min_interval = 0.11  # ~9 req/sec
        else:
            self.min_interval = 0.35  # ~2.8 req/sec

        self._last_request_time = 0.0
        self._http_client = http_client or httpx.Client(timeout=15.0)

    def _throttle(self) -> None:
        """Enforces NCBI request pacing."""
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _build_params(self, extra_params: Dict[str, Any]) -> Dict[str, Any]:
        """Injects standard NCBI identification parameters."""
        params = {
            "tool": self.tool,
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        params.update(extra_params)
        return params

    def _execute_request(self, endpoint: str, params: Dict[str, Any]) -> httpx.Response:
        """
        Executes HTTP request with exponential backoff on 429 and transient errors.
        """
        url = self.base_url + endpoint
        full_params = self._build_params(params)

        for attempt in range(self.max_retries):
            self._throttle()
            try:
                response = self._http_client.get(url, params=full_params)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self.backoff_factor * (2 ** attempt)))
                    logger.warning("NCBI rate limit 429 encountered. Backing off for %.2fs", retry_after)
                    time.sleep(retry_after)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    logger.warning("NCBI server error %d. Retrying in %.2fs", response.status_code, sleep_time)
                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()
                return response

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt == self.max_retries - 1:
                    logger.error("NCBI request failed after %d retries: %s", self.max_retries, exc)
                    raise NcbiApiError(f"NCBI connection failure: {exc}") from exc
                sleep_time = self.backoff_factor * (2 ** attempt)
                time.sleep(sleep_time)

        raise NcbiApiError(f"NCBI request failed after {self.max_retries} attempts: {url}")

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
    ) -> List[str]:
        """
        Searches PubMed using esearch.fcgi and returns list of PMIDs.
        """
        if not query.strip():
            return []

        params = {
            "db": "pubmed",
            "term": query.strip(),
            "retmode": "json",
            "retmax": max_results,
            "sort": sort,
        }

        try:
            resp = self._execute_request("esearch.fcgi", params)
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            return [str(pid) for pid in id_list]
        except Exception as e:
            logger.error("Error during PubMed esearch for query '%s': %s", query, e)
            if isinstance(e, NcbiApiError):
                raise
            raise NcbiApiError(f"Failed to parse esearch response: {e}") from e

    def fetch_articles_by_pmids(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Retrieves article metadata and structured abstracts using efetch.fcgi with XML output.
        """
        if not pmids:
            return []

        # Deduplicate PMIDs while preserving order
        unique_pmids = list(dict.fromkeys(pmids))
        id_str = ",".join(unique_pmids)

        params = {
            "db": "pubmed",
            "id": id_str,
            "retmode": "xml",
        }

        resp = self._execute_request("efetch.fcgi", params)
        return self._parse_efetch_xml(resp.text)

    def _parse_efetch_xml(self, xml_content: str) -> List[PubMedArticle]:
        """
        Robustly parses PubMedArticleSet XML into validated PubMedArticle models.
        """
        articles: List[PubMedArticle] = []
        if not xml_content.strip():
            return articles

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error("XML parse error on efetch response: %s", e)
            raise NcbiApiError(f"Malformed XML from NCBI: {e}") from e

        for article_node in root.findall(".//PubmedArticle"):
            try:
                medline = article_node.find("MedlineCitation")
                if medline is None:
                    continue

                # PMID
                pmid_elem = medline.find("PMID")
                pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ""
                if not pmid:
                    continue

                article_info = medline.find("Article")
                if article_info is None:
                    continue

                # Title
                title_elem = article_info.find("ArticleTitle")
                title = "".join(title_elem.itertext()).strip() if title_elem is not None else "Untitled"

                # Abstract
                abstract_elem = article_info.find("Abstract")
                abstract_parts = []
                if abstract_elem is not None:
                    for text_node in abstract_elem.findall("AbstractText"):
                        label = text_node.attrib.get("Label")
                        text_val = "".join(text_node.itertext()).strip()
                        if label:
                            abstract_parts.append(f"{label}: {text_val}")
                        else:
                            abstract_parts.append(text_val)
                abstract = "\n\n".join(abstract_parts) if abstract_parts else "No abstract available."

                # Authors
                authors = []
                author_list_node = article_info.find("AuthorList")
                if author_list_node is not None:
                    for author_node in author_list_node.findall("Author"):
                        last_name = author_node.findtext("LastName")
                        initials = author_node.findtext("Initials") or author_node.findtext("ForeName")
                        if last_name:
                            author_str = f"{last_name} {initials}" if initials else last_name
                            authors.append(author_str.strip())

                # Journal
                journal_elem = article_info.find(".//Journal/Title")
                if journal_elem is None:
                    journal_elem = medline.find(".//MedlineJournalInfo/MedlineTA")
                journal = journal_elem.text.strip() if journal_elem is not None and journal_elem.text else None

                # Publication Year
                year_elem = article_info.find(".//JournalIssue/PubDate/Year")
                if year_elem is None:
                    year_elem = article_info.find(".//JournalIssue/PubDate/MedlineDate")
                if year_elem is None:
                    year_elem = medline.find(".//DateCompleted/Year")
                if year_elem is None:
                    year_elem = medline.find(".//DateRevised/Year")

                pub_year = None
                if year_elem is not None and year_elem.text:
                    try:
                        digits = "".join(c for c in year_elem.text if c.isdigit())
                        if len(digits) >= 4:
                            pub_year = int(digits[:4])
                    except ValueError:
                        pass

                # MeSH Headings
                mesh_terms = []
                mesh_list = medline.find("MeshHeadingList")
                if mesh_list is not None:
                    for mesh in mesh_list.findall(".//DescriptorName"):
                        if mesh.text:
                            mesh_terms.append(mesh.text.strip())

                # Identifiers (DOI, PMCID)
                doi = None
                pmcid = None
                pubmed_data = article_node.find("PubmedData")
                if pubmed_data is not None:
                    for aid in pubmed_data.findall(".//ArticleId"):
                        id_type = aid.attrib.get("IdType")
                        if id_type == "doi" and aid.text:
                            doi = aid.text.strip()
                        elif id_type == "pmc" and aid.text:
                            pmcid = aid.text.strip()

                citation = CitationReference(
                    pmid=pmid,
                    pmcid=pmcid,
                    doi=doi,
                    title=title,
                    authors=authors,
                    journal=journal,
                    publication_year=pub_year,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )

                article = PubMedArticle(
                    pmid=pmid,
                    pmcid=pmcid,
                    doi=doi,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    publication_year=pub_year,
                    mesh_terms=mesh_terms,
                    citation=citation,
                    data_origin=DataOrigin.LITERATURE_RETRIEVAL,
                )
                articles.append(article)

            except Exception as e:
                logger.warning("Skipping malformed article record in XML: %s", e)
                continue

        return articles

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
    ) -> List[PubMedArticle]:
        """Convenience method to execute search followed by XML metadata retrieval."""
        pmids = self.search(query=query, max_results=max_results, sort=sort)
        if not pmids:
            return []
        return self.fetch_articles_by_pmids(pmids)
