import pytest

from src.domain.enums import DataOrigin
from src.domain.models import ScreeningPrediction
from src.engine.screening import CompoundScreeningEngine, PhysicochemicalSimulationEngine


class TestCompoundScreeningAbstraction:

    @pytest.fixture
    def engine(self):
        return PhysicochemicalSimulationEngine()

    def test_engine_implements_interface(self, engine):
        assert isinstance(engine, CompoundScreeningEngine)

    def test_predict_affinity_single_molecule(self, engine):
        # Aspirin SMILES: CC(=O)Oc1ccccc1C(=O)O
        smiles = "CC(=O)Oc1ccccc1C(=O)O"
        pred = engine.predict_affinity(target_symbol="PTGS2", smiles=smiles)

        assert isinstance(pred, ScreeningPrediction)
        assert pred.target_symbol == "PTGS2"
        assert pred.smiles == smiles
        assert pred.data_origin == DataOrigin.COMPUTATIONAL_PREDICTION
        assert "not experimentally measured" in pred.disclaimer.lower()

        # Check molecular descriptors calculated
        assert pred.molecular_weight is not None and pred.molecular_weight > 100.0
        assert pred.logp is not None
        assert pred.tpsa is not None and pred.tpsa > 0.0

        # Check binding metrics
        assert pred.predicted_binding_affinity_kcal_mol is not None
        assert pred.predicted_kd_nm is not None
        assert pred.confidence_interval is not None
        assert pred.confidence_interval[0] < pred.confidence_interval[1]

    def test_batch_screening(self, engine):
        smiles_list = [
            "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
            "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
            "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        ]
        results = engine.screen_compounds(target_symbol="PTGS1", compound_smiles_list=smiles_list)

        assert len(results) == 3
        for r in results:
            assert r.target_symbol == "PTGS1"
            assert r.data_origin == DataOrigin.COMPUTATIONAL_PREDICTION
            assert r.prediction_method == "PhysicoChemicalHeuristic_v1"

    def test_predictions_are_deterministic(self, engine):
        smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
        pred1 = engine.predict_affinity(target_symbol="ADORA2A", smiles=smiles)
        pred2 = engine.predict_affinity(target_symbol="ADORA2A", smiles=smiles)

        assert pred1.predicted_binding_affinity_kcal_mol == pred2.predicted_binding_affinity_kcal_mol
        assert pred1.molecular_weight == pred2.molecular_weight
        assert pred1.logp == pred2.logp
        assert pred1.tpsa == pred2.tpsa
        assert pred1.predicted_kd_nm == pred2.predicted_kd_nm
