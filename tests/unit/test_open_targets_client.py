import json
from pathlib import Path
import httpx
import pytest

from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.domain.enums import TractabilityModality, TractabilityBucket, DataOrigin


@pytest.fixture
def mock_ot_fixtures():
    fixture_file = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "mock_opentargets_responses.json"
    with open(fixture_file, "r", encoding="utf-8") as f:
        return json.load(f)


class TestOpenTargetsClient:

    def test_search_disease_success(self, mock_ot_fixtures):
        resp_json = mock_ot_fixtures["disease_search_alzheimer"]

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert "SearchDisease" in payload.get("query", "")
            return httpx.Response(200, json=resp_json)

        client = OpenTargetsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        res = client.search_disease("Alzheimer's disease")

        assert res is not None
        assert res["id"] == "EFO_0000249"
        assert "Alzheimer" in res["name"]

    def test_search_disease_empty(self, mock_ot_fixtures):
        resp_json = mock_ot_fixtures["disease_search_empty"]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=resp_json)

        client = OpenTargetsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        res = client.search_disease("NonExistentCondition123")
        assert res is None

    def test_search_disease_empty_string_returns_none(self):
        client = OpenTargetsClient()
        assert client.search_disease("") is None
        assert client.search_disease("   ") is None

    def test_get_associated_targets(self, mock_ot_fixtures):
        resp_json = mock_ot_fixtures["associated_targets_alzheimer"]

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert "AssociatedTargets" in payload.get("query", "")
            return httpx.Response(200, json=resp_json)

        client = OpenTargetsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        targets = client.get_associated_targets("EFO_0000249")

        assert len(targets) == 3
        symbols = [t["approved_symbol"] for t in targets]
        assert "TREM2" in symbols
        assert "BACE1" in symbols
        assert "APP" in symbols

        trem2 = next(t for t in targets if t["approved_symbol"] == "TREM2")
        assert trem2["overall_score"] == 0.88
        assert trem2["datatype_scores"]["genetic_association"] == 0.95

    def test_get_associated_targets_empty_id(self):
        client = OpenTargetsClient()
        assert client.get_associated_targets("") == []

    def test_get_target_tractability_trem2(self, mock_ot_fixtures):
        resp_json = mock_ot_fixtures["target_tractability_trem2"]

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert "TargetTractability" in payload.get("query", "")
            return httpx.Response(200, json=resp_json)

        client = OpenTargetsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        profile = client.get_target_tractability("ENSG00000095977", "TREM2")

        assert profile.target_symbol == "TREM2"
        assert profile.overall_tractability_score >= 80.0
        assert TractabilityModality.ANTIBODY in profile.modalities
        assert profile.modalities[TractabilityModality.ANTIBODY].bucket == TractabilityBucket.CLINICAL_PRECEDENCE
        assert TractabilityModality.SMALL_MOLECULE in profile.modalities
        assert profile.data_origin == DataOrigin.EXPERIMENTALLY_MEASURED

    def test_get_target_tractability_bace1(self, mock_ot_fixtures):
        resp_json = mock_ot_fixtures["target_tractability_bace1"]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=resp_json)

        client = OpenTargetsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        profile = client.get_target_tractability("ENSG00000186318", "BACE1")

        assert profile.target_symbol == "BACE1"
        assert profile.overall_tractability_score >= 90.0
        sm = profile.modalities[TractabilityModality.SMALL_MOLECULE]
        assert sm.bucket == TractabilityBucket.CLINICAL_PRECEDENCE

    def test_graphql_errors_field_raises_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"errors": [{"message": "Invalid GraphQL query syntax"}]})

        client = OpenTargetsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            max_retries=1,
        )

        with pytest.raises(OpenTargetsApiError) as exc_info:
            client.get_associated_targets("EFO_0000249")
        assert "Invalid GraphQL query" in str(exc_info.value)

    def test_server_error_500_retries_and_raises(self):
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(500, text="Internal Gateway Error")

        client = OpenTargetsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            max_retries=3,
            backoff_factor=0.01,
        )

        with pytest.raises(OpenTargetsApiError):
            client.get_associated_targets("EFO_0000249")
        assert attempts == 3
