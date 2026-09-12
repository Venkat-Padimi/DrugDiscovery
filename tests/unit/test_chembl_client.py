import json
from pathlib import Path
import httpx
import pytest

from src.clients.chembl import ChEMBLClient, ChEMBLApiError
from src.domain.enums import DataOrigin


@pytest.fixture
def mock_chembl_fixtures():
    fixture_file = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "mock_chembl_responses.json"
    with open(fixture_file, "r", encoding="utf-8") as f:
        return json.load(f)


class TestChEMBLClient:

    def test_search_target_bace1(self, mock_chembl_fixtures):
        resp_json = mock_chembl_fixtures["target_search_bace1"]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "target/search.json" in str(request.url)
            assert "q=BACE1" in str(request.url)
            return httpx.Response(200, json=resp_json)

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            mock_fallback=False,
        )
        target_id = client.search_target("BACE1")
        assert target_id == "CHEMBL2487"

    def test_search_target_trem2(self, mock_chembl_fixtures):
        resp_json = mock_chembl_fixtures["target_search_trem2"]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=resp_json)

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            mock_fallback=False,
        )
        target_id = client.search_target("TREM2")
        assert target_id == "CHEMBL4822"

    def test_search_target_empty_results(self, mock_chembl_fixtures):
        resp_json = mock_chembl_fixtures["target_search_empty"]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=resp_json)

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            mock_fallback=False,
        )
        target_id = client.search_target("UNKNOWN_GENE_XYZ")
        assert target_id is None

    def test_search_target_empty_query(self):
        client = ChEMBLClient(mock_fallback=False)
        assert client.search_target("") is None
        assert client.search_target("   ") is None

    def test_get_target_bioactivities_bace1(self, mock_chembl_fixtures):
        resp_json = mock_chembl_fixtures["activities_bace1"]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "activity.json" in str(request.url)
            assert "target_chembl_id=CHEMBL2487" in str(request.url)
            return httpx.Response(200, json=resp_json)

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            mock_fallback=False,
        )
        activities = client.get_target_bioactivities("CHEMBL2487", target_symbol="BACE1", limit=5)

        assert len(activities) == 2
        act1 = activities[0]
        assert act1.compound_id == "CHEMBL3545112"
        assert act1.compound_name == "VERUBECESTAT"
        assert act1.target_symbol == "BACE1"
        assert act1.activity_type == "IC50"
        assert act1.activity_value == 2.2
        assert act1.activity_unit == "nM"
        assert act1.assay_chembl_id == "CHEMBL1928374"
        assert act1.data_origin == DataOrigin.EXPERIMENTALLY_MEASURED

    def test_get_target_bioactivities_empty_id(self):
        client = ChEMBLClient(mock_fallback=False)
        assert client.get_target_bioactivities("") == []
        assert client.get_target_bioactivities("   ") == []

    def test_chembl_500_server_error_retries_and_raises(self):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, content=b"Internal Server Error")

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            max_retries=2,
            backoff_factor=0.01,
            mock_fallback=False,
        )

        with pytest.raises(ChEMBLApiError) as exc_info:
            client.search_target("BACE1")

        assert call_count == 2
        assert "ChEMBL request failed after 2 attempts" in str(exc_info.value)

    def test_connection_error_raises_when_fallback_disabled(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Network is completely unreachable")

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            max_retries=1,
            backoff_factor=0.01,
            mock_fallback=False,
        )

        with pytest.raises(ChEMBLApiError) as exc_info:
            client.search_target("BACE1")

        assert "ChEMBL connection failure" in str(exc_info.value)

    def test_connection_error_uses_fixture_when_fallback_enabled(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Simulated offline environment")

        client = ChEMBLClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            max_retries=1,
            backoff_factor=0.01,
            mock_fallback=True,
        )

        target_id = client.search_target("BACE1")
        assert target_id == "CHEMBL2487"

        activities = client.get_target_bioactivities("CHEMBL2487", target_symbol="BACE1")
        assert len(activities) >= 1
        assert activities[0].data_origin == DataOrigin.EXPERIMENTALLY_MEASURED
