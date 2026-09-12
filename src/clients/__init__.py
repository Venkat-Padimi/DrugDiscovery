"""
Client adapters for external biomedical data services (NCBI PubMed/PMC, Open Targets, ChEMBL).
"""

from src.clients.ncbi_pubmed import NcbiPubMedClient, NcbiApiError
from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.clients.chembl import ChEMBLClient, ChEMBLApiError

__all__ = [
    "NcbiPubMedClient",
    "NcbiApiError",
    "OpenTargetsClient",
    "OpenTargetsApiError",
    "ChEMBLClient",
    "ChEMBLApiError",
]
