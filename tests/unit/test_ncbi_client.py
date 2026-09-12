import json
import time
from pathlib import Path
import httpx
import pytest

from src.clients.ncbi_pubmed import NcbiPubMedClient, NcbiApiError
from src.domain.enums import DataOrigin


@pytest.fixture
def mock_pubmed_fixtures():
    fixture_file = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "mock_pubmed_responses.json"
    with open(fixture_file, "r", encoding="utf-8") as f:
        return json.load(f)


class TestNcbiPubMedClient:

    def test_search_successful(self, mock_pubmed_fixtures):
        search_json = mock_pubmed_fixtures["esearch_alzheimer_success"]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "esearch.fcgi" in str(request.url)
            assert "db=pubmed" in str(request.url)
            return httpx.Response(200, json=search_json)

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        pmids = client.search("Alzheimer disease AND therapeutic target", max_results=5)
        assert len(pmids) == 5
        assert pmids[0] == "31234567"
        assert pmids[1] == "32345678"

    def test_search_empty_results(self, mock_pubmed_fixtures):
        empty_json = mock_pubmed_fixtures["esearch_empty"]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=empty_json)

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        pmids = client.search("nonexistentdiseasequery12345")
        assert pmids == []

    def test_search_empty_query_returns_empty_without_call(self):
        client = NcbiPubMedClient(rate_limit_delay=0.0)
        assert client.search("") == []
        assert client.search("   ") == []

    def test_fetch_articles_xml_parsing(self, mock_pubmed_fixtures):
        xml_content = mock_pubmed_fixtures["efetch_xml_sample"]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "efetch.fcgi" in str(request.url)
            assert "db=pubmed" in str(request.url)
            assert "retmode=xml" in str(request.url)
            return httpx.Response(200, text=xml_content)

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        articles = client.fetch_articles_by_pmids(["31234567", "32345678"])
        assert len(articles) == 2

        # Article 1 verification: TREM2 paper
        a1 = articles[0]
        assert a1.pmid == "31234567"
        assert a1.pmcid == "PMC6589012"
        assert a1.doi == "10.1038/s41586-019-1234-5"
        assert "TREM2" in a1.title
        assert "BACKGROUND:" in a1.abstract
        assert "RESULTS:" in a1.abstract
        assert len(a1.authors) == 3
        assert "Smith J" in a1.authors
        assert a1.publication_year == 2019
        assert a1.journal == "Nature"
        assert len(a1.mesh_terms) >= 3
        assert a1.data_origin == DataOrigin.LITERATURE_RETRIEVAL
        assert a1.citation is not None
        assert a1.citation.pmid == "31234567"

        # Article 2 verification: BACE1 paper
        a2 = articles[1]
        assert a2.pmid == "32345678"
        assert a2.doi == "10.1126/science.abc1234"
        assert a2.pmcid is None  # Not present in fixture
        assert a2.publication_year == 2020
        assert a2.journal == "Science"

    def test_fetch_articles_empty_pmids_list(self):
        client = NcbiPubMedClient(rate_limit_delay=0.0)
        assert client.fetch_articles_by_pmids([]) == []

    def test_pmid_deduplication_in_fetch(self, mock_pubmed_fixtures):
        xml_content = mock_pubmed_fixtures["efetch_xml_sample"]
        requested_ids = []

        def handler(request: httpx.Request) -> httpx.Response:
            params = dict(request.url.params)
            requested_ids.append(params.get("id"))
            return httpx.Response(200, text=xml_content)

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        # Pass duplicate PMIDs
        client.fetch_articles_by_pmids(["31234567", "31234567", "32345678", "31234567"])
        assert len(requested_ids) == 1
        # Should only request unique comma-separated IDs
        assert requested_ids[0] == "31234567,32345678"

    def test_malformed_xml_raises_ncbi_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<InvalidXml><BrokenTag>")

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        with pytest.raises(NcbiApiError) as exc_info:
            client.fetch_articles_by_pmids(["12345"])
        assert "Malformed XML" in str(exc_info.value)

    def test_server_error_500_retries_and_fails(self):
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
            max_retries=3,
            backoff_factor=0.01,
        )

        with pytest.raises(NcbiApiError):
            client.search("Alzheimer")
        assert attempts == 3

    def test_rate_limit_429_retries_and_succeeds(self, mock_pubmed_fixtures):
        search_json = mock_pubmed_fixtures["esearch_alzheimer_success"]
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(429, headers={"Retry-After": "0.01"})
            return httpx.Response(200, json=search_json)

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
            max_retries=3,
            backoff_factor=0.01,
        )

        pmids = client.search("Alzheimer")
        assert len(pmids) == 5
        assert attempts == 2

    def test_parameters_include_tool_and_email(self):
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json={"esearchresult": {"idlist": []}})

        transport = httpx.MockTransport(handler)
        client = NcbiPubMedClient(
            email="test_user@domain.com",
            tool="CustomTestTool",
            api_key="test_api_key_xyz",
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.0,
        )

        client.search("TestQuery")
        assert captured_params.get("tool") == "CustomTestTool"
        assert captured_params.get("email") == "test_user@domain.com"
        assert captured_params.get("api_key") == "test_api_key_xyz"

    def test_rate_limiter_pacing(self):
        call_times = []

        def handler(request: httpx.Request) -> httpx.Response:
            call_times.append(time.monotonic())
            return httpx.Response(200, json={"esearchresult": {"idlist": []}})

        transport = httpx.MockTransport(handler)
        # Set min_interval to 0.05 seconds
        client = NcbiPubMedClient(
            http_client=httpx.Client(transport=transport),
            rate_limit_delay=0.05,
        )

        client.search("Q1")
        client.search("Q2")
        assert len(call_times) == 2
        elapsed = call_times[1] - call_times[0]
        assert elapsed >= 0.045  # Must be throttled by at least ~0.05s
