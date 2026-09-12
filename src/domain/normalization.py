import re
from typing import Dict, Optional, Tuple


class GeneIdentifierNormalizer:
    """
    Standardized nomenclature normalizer for human gene and protein target symbols.
    
    CRITICAL ARCHITECTURAL FUNCTION:
    - Normalizes gene synonyms, aliases, and hyphenated variations to official HGNC symbols.
    - Prevents target fragmentation (e.g. TREM-2 vs TREM2) across literature and databases.
    - Resolves Ensembl IDs safely without fabricating non-existent IDs.
    """

    # Reference mapping: canonical HGNC symbol -> (Approved Name, Ensembl ID, list of aliases)
    _REFERENCE_TARGETS: Dict[str, Tuple[str, str, Tuple[str, ...]]] = {
        "TREM2": (
            "triggering receptor expressed on myeloid cells 2",
            "ENSG00000095977",
            ("TREM-2", "TREM 2", "TRIGGERING RECEPTOR EXPRESSED ON MYELOID CELLS 2"),
        ),
        "BACE1": (
            "beta-secretase 1",
            "ENSG00000186318",
            ("BACE-1", "BACE 1", "BETA SECRETASE 1", "BETA-SITE APP CLEAVING ENZYME 1", "ASP2", "MEMAPSIN-2"),
        ),
        "APP": (
            "amyloid beta precursor protein",
            "ENSG00000142192",
            ("A-BETA", "ABETA", "AMYLOID PRECURSOR PROTEIN", "AMYLOID-BETA PRECURSOR PROTEIN", "AAA", "CVAP", "AD1"),
        ),
        "PSEN1": (
            "presenilin 1",
            "ENSG00000080815",
            ("PS-1", "PS1", "PSEN-1", "PRESENILIN-1", "PRESENILIN 1", "AD3"),
        ),
        "PSEN2": (
            "presenilin 2",
            "ENSG00000143801",
            ("PS-2", "PS2", "PSEN-2", "PRESENILIN-2", "PRESENILIN 2", "AD4"),
        ),
        "APOE": (
            "apolipoprotein E",
            "ENSG00000130203",
            ("APO-E", "APOLIPOPROTEIN E", "APOLIPOPROTEIN-E", "AD2"),
        ),
        "MAPT": (
            "microtubule associated protein tau",
            "ENSG00000186868",
            ("TAU", "MICROTUBULE ASSOCIATED PROTEIN TAU", "FTDP-17", "MTBT1"),
        ),
        "GSK3B": (
            "glycogen synthase kinase 3 beta",
            "ENSG00000082701",
            ("GSK-3B", "GSK3-BETA", "GSK-3BETA", "GLYCOGEN SYNTHASE KINASE 3 BETA"),
        ),
        "SNCA": (
            "synuclein alpha",
            "ENSG00000145335",
            ("ALPHA-SYNUCLEIN", "A-SYNUCLEIN", "SYNUCLEIN ALPHA", "PARK1", "PARK4"),
        ),
        "LRRK2": (
            "leucine rich repeat kinase 2",
            "ENSG00000188906",
            ("DARDARIN", "LEUCINE RICH REPEAT KINASE 2", "PARK8"),
        ),
        "SOD1": (
            "superoxide dismutase 1",
            "ENSG00000142168",
            ("SUPEROXIDE DISMUTASE 1", "ALS", "ALS1", "IPOA"),
        ),
        "TARDBP": (
            "TAR DNA binding protein",
            "ENSG00000120948",
            ("TDP-43", "TDP43", "TAR DNA BINDING PROTEIN 43"),
        ),
        "CDK4": (
            "cyclin dependent kinase 4",
            "ENSG00000135446",
            ("CDK-4", "CYCLIN DEPENDENT KINASE 4", "CKR4", "PSK-J3"),
        ),
        "EGFR": (
            "epidermal growth factor receptor",
            "ENSG00000146648",
            ("ERBB", "ERBB1", "HER1", "EPIDERMAL GROWTH FACTOR RECEPTOR"),
        ),
    }

    def __init__(self):
        # Build alias lookup table
        self._alias_to_canonical: Dict[str, str] = {}
        for canonical, (_, _, aliases) in self._REFERENCE_TARGETS.items():
            self._alias_to_canonical[canonical.upper()] = canonical
            for alias in aliases:
                norm_alias = self._clean_token(alias)
                self._alias_to_canonical[norm_alias] = canonical

    @staticmethod
    def _clean_token(token: str) -> str:
        """Strips hyphens, extra whitespace, and standardizes casing."""
        cleaned = re.sub(r"[\s\-_]+", "", token.strip().upper())
        return cleaned

    def normalize_symbol(self, raw_symbol_or_alias: str) -> str:
        """
        Resolves an input string or alias to its canonical HGNC gene symbol.
        If unknown, returns normalized uppercase alphanumeric token.
        """
        if not raw_symbol_or_alias:
            return ""

        token = self._clean_token(raw_symbol_or_alias)
        if token in self._alias_to_canonical:
            return self._alias_to_canonical[token]

        # Return standardized uppercase alphanumeric symbol
        clean_raw = re.sub(r"[^A-Za-z0-9]", "", raw_symbol_or_alias).upper()
        return clean_raw

    def get_known_ensembl_id(self, symbol: str) -> Optional[str]:
        """Returns verified Ensembl ID for canonical symbol, or None if unmapped."""
        canonical = self.normalize_symbol(symbol)
        if canonical in self._REFERENCE_TARGETS:
            return self._REFERENCE_TARGETS[canonical][1]
        return None

    def get_known_approved_name(self, symbol: str) -> Optional[str]:
        """Returns approved full name for canonical symbol, or None if unmapped."""
        canonical = self.normalize_symbol(symbol)
        if canonical in self._REFERENCE_TARGETS:
            return self._REFERENCE_TARGETS[canonical][0]
        return None


# Global default instance
normalizer = GeneIdentifierNormalizer()
