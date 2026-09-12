# Synthetic Demonstration Experimental Dataset

> [!WARNING]
> **MANDATORY SCIENTIFIC TRANSPARENCY NOTICE**:
> **"Synthetic demonstration dataset — not proprietary experimental data."**
> This dataset contains synthetic values generated solely to demonstrate the schema validation,
> provenance tracking, and ingestion architecture of the Drug Discovery & Target Identification Agent.
> It MUST NOT be represented as real proprietary in-house laboratory measurements.

---

## Purpose & Integration Architecture
Real drug discovery organizations generate heterogeneous internal datasets:
- CRISPR-Cas9 / shRNA cellular viability screens
- RNA-seq differential expression (e.g. disease tissue vs control)
- Surface Plasmon Resonance (SPR) binding kinetics
- Cellular IC50 assays and western blot validations

This repository provides an ingestion pipeline that:
1. Validates all inbound experimental records against the Pydantic `ExperimentalRecord` and `DatasetMetadata` schemas.
2. Enforces quality control (QC status flags, replicate thresholds, p-value / FDR limits).
3. Links measurements to standardized HGNC target symbols.
4. Preserves dataset versioning and provenance timestamps.
5. Ingests securely via role-based access boundaries without polluting public literature retrieval.

---

## Dataset Schema Reference
- `dataset_id`: Unique identifier (e.g., `SYNTH-ASSAY-2026-001`)
- `is_synthetic`: Always `True` for demonstration datasets.
- `disclaimer`: `"Synthetic demonstration dataset — not proprietary experimental data."`
- `target_symbol`: Standard HGNC gene symbol (e.g., `APP`, `PSEN1`, `TREM2`, `BACE1`, `MAPT`).
- `assay_type`: Laboratory assay platform (`CRISPR_KO_Viability`, `RNASeq_DifferentialExpression`, `SPR_Kinetic_Binding`).
- `measurement_name`: Normalized metric name (`viability_rescue_pct`, `log2_fold_change`, `kd_nm`).
- `measurement_value`: Numerical readout.
- `replicates`: Minimum replicate count (typically $\ge 3$).
- `qc_passed`: Boolean QC pass flag.
