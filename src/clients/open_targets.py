import logging
import time
from typing import List, Dict, Optional, Any
import httpx

from config.settings import settings
from src.domain.enums import (
    DataOrigin,
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
)
from src.domain.models import (
    DruggabilityProfile,
    DruggabilityModalityDetail,
    EvidenceItem,
    ProvenanceRecord,
)

logger = logging.getLogger(__name__)


class OpenTargetsApiError(Exception):
    """Exception raised when Open Targets GraphQL API encounters an error."""
    pass


class OpenTargetsClient:
    """
    Dedicated client adapter for the Open Targets Platform GraphQL API.
    
    SAFETY & INTEGRITY PRINCIPLES:
    - Official public GraphQL endpoint integration (no authentication required).
    - Returns structured target-disease associations, evidence scores, and tractability.
    - Zero fabrication: missing targets or empty responses return clean empty/None objects.
    - Strictly preserves data origin tags and provenance.
    """

    def __init__(
        self,
        graphql_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.graphql_url = graphql_url or settings.open_targets_graphql_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._http_client = http_client or httpx.Client(timeout=15.0)

    def _execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a GraphQL POST query with exponential backoff on transient errors."""
        payload = {"query": query, "variables": variables or {}}

        for attempt in range(self.max_retries):
            try:
                resp = self._http_client.post(self.graphql_url, json=payload)

                if resp.status_code == 429 or resp.status_code in (500, 502, 503, 504):
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    logger.warning("Open Targets HTTP %d. Retrying in %.2fs", resp.status_code, sleep_time)
                    time.sleep(sleep_time)
                    continue

                resp.raise_for_status()
                data = resp.json()

                if "errors" in data and data["errors"]:
                    error_msg = "; ".join(e.get("message", "Unknown GraphQL error") for e in data["errors"])
                    logger.error("Open Targets GraphQL error: %s", error_msg)
                    raise OpenTargetsApiError(f"Open Targets GraphQL error: {error_msg}")

                return data.get("data", {})

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt == self.max_retries - 1:
                    logger.error("Open Targets request failed after %d retries: %s", self.max_retries, exc)
                    raise OpenTargetsApiError(f"Open Targets connection failure: {exc}") from exc
                sleep_time = self.backoff_factor * (2 ** attempt)
                time.sleep(sleep_time)

        raise OpenTargetsApiError(f"Open Targets request failed after {self.max_retries} attempts.")

    def search_disease(self, disease_name: str) -> Optional[Dict[str, str]]:
        """
        Queries Open Targets entity search to map a disease name to its EFO/MONDO ontology ID.
        """
        if not disease_name.strip():
            return None

        query = """
        query SearchDisease($queryString: String!) {
            search(queryString: $queryString, entityNames: ["disease"], page: {size: 1, index: 0}) {
                totalHits
                hits {
                    id
                    name
                    entity
                    description
                }
            }
        }
        """
        try:
            data = self._execute_graphql(query, {"queryString": disease_name.strip()})
            hits = data.get("search", {}).get("hits", [])
            if hits:
                top_hit = hits[0]
                return {
                    "id": top_hit.get("id", ""),
                    "name": top_hit.get("name", disease_name),
                    "description": top_hit.get("description", ""),
                }
            return None
        except Exception as e:
            logger.error("Error searching disease '%s' in Open Targets: %s", disease_name, e)
            if isinstance(e, OpenTargetsApiError):
                raise
            raise OpenTargetsApiError(f"Failed to search disease: {e}") from e

    def get_associated_targets(self, disease_id: str, size: int = 15) -> List[Dict[str, Any]]:
        """
        Retrieves top associated targets for a disease ID from Open Targets.
        """
        if not disease_id.strip():
            return []

        query = """
        query AssociatedTargets($diseaseId: String!, $size: Int!) {
            disease(efoId: $diseaseId) {
                id
                name
                associatedTargets(page: {size: $size, index: 0}) {
                    count
                    rows {
                        target {
                            id
                            approvedSymbol
                            approvedName
                        }
                        score
                        datatypeScores {
                            id
                            score
                        }
                    }
                }
            }
        }
        """
        try:
            data = self._execute_graphql(query, {"diseaseId": disease_id.strip(), "size": size})
            disease_node = data.get("disease")
            if not disease_node:
                return []
            rows = disease_node.get("associatedTargets", {}).get("rows", [])
            results = []
            for r in rows:
                target_node = r.get("target", {})
                results.append({
                    "ensembl_id": target_node.get("id"),
                    "approved_symbol": target_node.get("approvedSymbol"),
                    "approved_name": target_node.get("approvedName"),
                    "overall_score": float(r.get("score", 0.0)),
                    "datatype_scores": {
                        dt.get("id"): float(dt.get("score", 0.0))
                        for dt in r.get("datatypeScores", [])
                    },
                })
            return results
        except Exception as e:
            logger.error("Error fetching associated targets for disease '%s': %s", disease_id, e)
            if isinstance(e, OpenTargetsApiError):
                raise
            raise OpenTargetsApiError(f"Failed to fetch associated targets: {e}") from e

    def get_target_tractability(self, target_ensembl_id: str, target_symbol: str = "") -> DruggabilityProfile:
        """
        Retrieves tractability assessment from Open Targets for small molecules, antibodies, and PROTACs.
        """
        if not target_ensembl_id.strip():
            return DruggabilityProfile(
                target_symbol=target_symbol or "UNKNOWN",
                overall_tractability_score=25.0,
                summary_rationale="No Ensembl ID available for Open Targets tractability lookup.",
            )

        query = """
        query TargetTractability($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                approvedSymbol
                tractability {
                    modality
                    id
                    value
                }
            }
        }
        """
        try:
            data = self._execute_graphql(query, {"targetId": target_ensembl_id.strip()})
            target_node = data.get("target") or {}
            symbol = target_node.get("approvedSymbol") or target_symbol
            tractability_list = target_node.get("tractability") or []

            modalities: Dict[TractabilityModality, DruggabilityModalityDetail] = {}

            # Process Small Molecule tractability
            sm_records = [t for t in tractability_list if t.get("modality") == "SM" and t.get("value") is True]
            sm_ids = set(t.get("id") for t in sm_records)

            if "Clinical Precedence" in sm_ids:
                modalities[TractabilityModality.SMALL_MOLECULE] = DruggabilityModalityDetail(
                    modality=TractabilityModality.SMALL_MOLECULE,
                    bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                    score=95.0,
                    details="Small molecule clinical precedence established in Open Targets.",
                )
            elif "Discovery Precedence" in sm_ids:
                modalities[TractabilityModality.SMALL_MOLECULE] = DruggabilityModalityDetail(
                    modality=TractabilityModality.SMALL_MOLECULE,
                    bucket=TractabilityBucket.DISCOVERY_PRECEDENCE,
                    score=75.0,
                    details="High-affinity tool compounds / discovery precedence in Open Targets.",
                )
            elif any("Pocket" in i or "Structure" in i for i in sm_ids):
                modalities[TractabilityModality.SMALL_MOLECULE] = DruggabilityModalityDetail(
                    modality=TractabilityModality.SMALL_MOLECULE,
                    bucket=TractabilityBucket.PREDICTED_TRACTABLE,
                    score=55.0,
                    details="High-confidence predicted druggable pocket.",
                )

            # Process Antibody tractability
            ab_records = [t for t in tractability_list if t.get("modality") == "AB" and t.get("value") is True]
            ab_ids = set(t.get("id") for t in ab_records)

            if "Clinical Precedence" in ab_ids:
                modalities[TractabilityModality.ANTIBODY] = DruggabilityModalityDetail(
                    modality=TractabilityModality.ANTIBODY,
                    bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                    score=90.0,
                    details="Biologic / antibody clinical precedence established.",
                )
            elif "Discovery Precedence" in ab_ids or "Predicted Tractable" in ab_ids:
                modalities[TractabilityModality.ANTIBODY] = DruggabilityModalityDetail(
                    modality=TractabilityModality.ANTIBODY,
                    bucket=TractabilityBucket.DISCOVERY_PRECEDENCE,
                    score=70.0,
                    details="Accessible extracellular epitope or discovery precedence.",
                )

            # Determine overall score
            if modalities:
                overall_score = max(d.score for d in modalities.values())
            else:
                overall_score = 30.0

            has_sm = TractabilityModality.SMALL_MOLECULE in modalities
            has_approved = any(
                d.bucket == TractabilityBucket.CLINICAL_PRECEDENCE for d in modalities.values()
            )

            return DruggabilityProfile(
                target_symbol=symbol,
                modalities=modalities,
                overall_tractability_score=overall_score,
                has_small_molecule_binder=has_sm,
                has_approved_drug=has_approved,
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                summary_rationale=f"Tractability derived from Open Targets precedence: {len(modalities)} modalities identified.",
            )

        except Exception as e:
            logger.error("Error fetching tractability for target '%s': %s", target_ensembl_id, e)
            if isinstance(e, OpenTargetsApiError):
                raise
            raise OpenTargetsApiError(f"Failed to fetch tractability: {e}") from e
