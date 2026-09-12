import pytest

from src.domain.normalization import GeneIdentifierNormalizer


class TestGeneIdentifierNormalizer:

    @pytest.fixture
    def norm(self):
        return GeneIdentifierNormalizer()

    def test_normalize_common_aliases(self, norm):
        assert norm.normalize_symbol("TREM-2") == "TREM2"
        assert norm.normalize_symbol("trem2") == "TREM2"
        assert norm.normalize_symbol("BACE-1") == "BACE1"
        assert norm.normalize_symbol("beta-secretase 1") == "BACE1"
        assert norm.normalize_symbol("A-beta") == "APP"
        assert norm.normalize_symbol("PS-1") == "PSEN1"
        assert norm.normalize_symbol("PSEN-1") == "PSEN1"
        assert norm.normalize_symbol("ApoE") == "APOE"
        assert norm.normalize_symbol("TDP-43") == "TARDBP"
        assert norm.normalize_symbol("alpha-synuclein") == "SNCA"
        assert norm.normalize_symbol("GSK-3beta") == "GSK3B"

    def test_get_known_ensembl_id(self, norm):
        assert norm.get_known_ensembl_id("TREM2") == "ENSG00000095977"
        assert norm.get_known_ensembl_id("TREM-2") == "ENSG00000095977"
        assert norm.get_known_ensembl_id("BACE1") == "ENSG00000186318"
        assert norm.get_known_ensembl_id("APP") == "ENSG00000142192"
        assert norm.get_known_ensembl_id("UNKNOWN_GENE_XYZ") is None

    def test_get_known_approved_name(self, norm):
        name = norm.get_known_approved_name("TREM2")
        assert name is not None
        assert "triggering receptor" in name.lower()

    def test_unknown_symbol_fallback(self, norm):
        # Unmapped symbol should be cleanly converted to uppercase alphanumeric without crashing
        assert norm.normalize_symbol("custom-gene-1") == "CUSTOMGENE1"
        assert norm.normalize_symbol("") == ""
