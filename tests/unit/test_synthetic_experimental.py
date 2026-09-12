import json
import pytest
from pathlib import Path

from src.domain.enums import DataOrigin
from src.engine.experimental_loader import ExperimentalDatasetLoader


class TestSyntheticExperimentalData:

    def test_load_sample_dataset(self, synthetic_data_path):
        assert synthetic_data_path.exists(), f"Sample dataset missing at {synthetic_data_path}"

        loader = ExperimentalDatasetLoader(synthetic_data_path)
        metadata, records = loader.load()

        assert metadata.dataset_id == "SYNTH-ASSAY-2026-001"
        assert metadata.is_synthetic is True
        assert "Synthetic demonstration dataset" in metadata.disclaimer
        assert len(records) >= 8

        # Every record must be strictly tagged as synthetic demonstration
        for record in records:
            assert record.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION
            assert "Synthetic demonstration dataset" in record.synthetic_disclaimer
            assert record.replicates >= 1
            assert record.target_symbol != ""

    def test_find_by_target(self, synthetic_data_path):
        loader = ExperimentalDatasetLoader(synthetic_data_path)
        loader.load()

        trem2_records = loader.find_by_target("TREM2")
        assert len(trem2_records) >= 2
        for r in trem2_records:
            assert r.target_symbol == "TREM2"

        # Case-insensitivity test
        trem2_lower = loader.find_by_target("trem2")
        assert len(trem2_lower) == len(trem2_records)

        empty_records = loader.find_by_target("NONEXISTENT_GENE_123")
        assert len(empty_records) == 0

    def test_find_by_assay(self, synthetic_data_path):
        loader = ExperimentalDatasetLoader(synthetic_data_path)
        loader.load()

        crispr_records = loader.find_by_assay("CRISPR")
        assert len(crispr_records) >= 2
        for r in crispr_records:
            assert "crispr" in r.assay_type.lower()

    def test_missing_file_raises(self, tmp_path):
        missing_file = tmp_path / "non_existent_dataset.json"
        loader = ExperimentalDatasetLoader(missing_file)
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_malformed_record_raises_validation_error(self, tmp_path):
        bad_json = {
            "metadata": {
                "dataset_id": "BAD-DS",
                "dataset_name": "Bad Dataset",
                "is_synthetic": True,
                "disclaimer": "Synthetic demo",
                "platform": "Test",
            },
            "records": [
                {
                    "record_id": "R1",
                    "dataset_id": "BAD-DS",
                    "target_symbol": "T1",
                    "cell_line_or_model": "Cell",
                    "assay_type": "Assay",
                    "measurement_name": "M",
                    "measurement_value": 10.0,
                    "measurement_unit": "uM",
                    "replicates": -5,  # Invalid: replicates must be >= 1
                }
            ],
        }
        bad_file = tmp_path / "bad.json"
        with open(bad_file, "w") as f:
            json.dump(bad_json, f)

        loader = ExperimentalDatasetLoader(bad_file)
        with pytest.raises(Exception):
            loader.load()
