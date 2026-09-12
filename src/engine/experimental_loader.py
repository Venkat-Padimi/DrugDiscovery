import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.domain.models import DatasetMetadata, ExperimentalRecord
from src.domain.enums import DataOrigin


class ExperimentalDatasetLoader:
    """
    Ingestion and validation manager for experimental datasets.
    
    SAFETY PRINCIPLES:
    - Strictly enforces schema validation on inbound experimental data.
    - Demands synthetic dataset labeling when synthetic data is loaded.
    - Prevents unverified experimental data from masquerading as validated proprietary IP.
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path
        self._metadata: Optional[DatasetMetadata] = None
        self._records: List[ExperimentalRecord] = []

    def load(self, path: Optional[Path] = None) -> Tuple[DatasetMetadata, List[ExperimentalRecord]]:
        target_path = path or self.dataset_path
        if not target_path or not Path(target_path).exists():
            raise FileNotFoundError(f"Experimental dataset file not found at: {target_path}")

        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        raw_meta = raw_data.get("metadata", {})
        raw_records = raw_data.get("records", [])

        # Validate metadata
        metadata = DatasetMetadata(**raw_meta)
        
        # Validate records
        validated_records: List[ExperimentalRecord] = []
        for r in raw_records:
            record = ExperimentalRecord(**r)
            # Enforce synthetic labeling if metadata is synthetic
            if metadata.is_synthetic:
                record.data_origin = DataOrigin.SYNTHETIC_DEMONSTRATION
                record.synthetic_disclaimer = metadata.disclaimer
            validated_records.append(record)

        self._metadata = metadata
        self._records = validated_records
        return metadata, validated_records

    @property
    def metadata(self) -> Optional[DatasetMetadata]:
        return self._metadata

    @property
    def records(self) -> List[ExperimentalRecord]:
        return self._records

    def find_by_target(self, target_symbol: str) -> List[ExperimentalRecord]:
        """Filters records by HGNC target gene symbol."""
        symbol_upper = target_symbol.strip().upper()
        return [r for r in self._records if r.target_symbol.upper() == symbol_upper]

    def find_by_assay(self, assay_type: str) -> List[ExperimentalRecord]:
        """Filters records by laboratory assay platform."""
        assay_lower = assay_type.strip().lower()
        return [r for r in self._records if assay_lower in r.assay_type.lower()]
