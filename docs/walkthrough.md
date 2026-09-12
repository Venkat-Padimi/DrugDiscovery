# Development Walkthrough: Phases 1–7

A chronological record of the multi-phase implementation and verification of the Drug Discovery & Target Identification Agent.

---

## Phase 1: Architecture & Scientific Data Models
- **Scientific Taxonomy & Enums** ([`src/domain/enums.py`](../src/domain/enums.py)):
  - Defined `WorkflowStage`, `EvidenceType`, `CausalityLevel`, `TractabilityModality`, `DataOrigin`.
- **Domain Models & Pydantic Validation** ([`src/domain/models.py`](../src/domain/models.py)):
  - Structured schemas for `TargetCandidate`, `EvidenceItem`, `DruggabilityAssessment`, `ExperimentalRecord`, `CompoundBioactivity`, `CompoundScreeningResult`, `TargetRankingRecord`.
- **Deterministic Target Scoring Engine** ([`src/engine/scoring.py`](../src/engine/scoring.py)):
  - Mathematical 6-dimension weighted scoring engine with boundary clamps $[0, 100]$ and contradiction penalty logic.
- **Synthetic Experimental Ingestion Pipeline** ([`src/engine/experimental_loader.py`](../src/engine/experimental_loader.py)):
  - Validates inbound assay records with QC flags, replicate thresholds, and p-value checks.
- **Compound Screening Abstraction** ([`src/engine/screening.py`](../src/engine/screening.py)):
  - Interface definition and deterministic mock screening engine with Lipinski rule evaluations.

---

## Phase 2: Biomedical Literature Search Agent & NCBI Integration
- **NCBI E-utilities Client Adapter** ([`src/clients/ncbi_pubmed.py`](../src/clients/ncbi_pubmed.py)):
  - Robust XML parser extracting PMIDs, titles, abstracts, journal metadata, and publication years.
  - Rate-limiting (pacing) supporting 3 req/sec public rate and 10 req/sec with optional API key.
  - Exponential backoff retry logic on HTTP 429 and transient 5xx errors.
- **Literature Search Agent** ([`src/agents/literature.py`](../src/agents/literature.py)):
  - Formulates MeSH-informed boolean search terms and extracts bibliographic provenance.
- **Deterministic Fixtures** ([`data/fixtures/mock_pubmed_responses.json`](../data/fixtures/mock_pubmed_responses.json)):
  - Enables offline testing with real PubMed citations for Alzheimer's, Parkinson's, and ALS.

---

## Phase 3: Target Identification & Open Targets Integration
- **Gene Identifier Normalizer** ([`src/domain/normalization.py`](../src/domain/normalization.py)):
  - Normalizes gene symbols to standardized HGNC nomenclature and Ensembl identifiers (`ENSG...`).
- **Open Targets Platform GraphQL Client** ([`src/clients/open_targets.py`](../src/clients/open_targets.py)):
  - Queries disease associations, genetic evidence scores, and modality tractability precedence.
- **Target Identification Agent** ([`src/agents/target_id.py`](../src/agents/target_id.py)):
  - Extracts candidate targets from literature abstracts and correlates them with Open Targets profiles.

---

## Phase 4: Multi-Agent Orchestration & LangGraph Supervisor
- **Supervisor Agent** ([`src/agents/supervisor.py`](../src/agents/supervisor.py)):
  - Decomposes research questions, formulates execution plans, and generates executive summaries.
- **LangGraph Stateful Orchestrator** ([`src/engine/workflow.py`](../src/engine/workflow.py)):
  - Direct cyclic graph with conditional routing, step counter guards, and graceful degradation handlers.

---

## Phase 5: Evidence Evaluation & Druggability Agents
- **Evidence Evaluation Agent** ([`src/agents/evidence_eval.py`](../src/agents/evidence_eval.py)):
  - Enforces causality boundaries (downgrading over-claimed co-occurrences).
  - Automatically flags contradictory biological effect directions (protective vs. pathogenic).
- **Druggability Agent** ([`src/agents/druggability.py`](../src/agents/druggability.py)):
  - Profiles Small Molecules, Monoclonal Antibodies, and PROTACs based on clinical precedence.
- **Target Ranking Agent** ([`src/agents/ranking.py`](../src/agents/ranking.py)):
  - Encapsulates deterministic composite scoring and builds multi-dimensional radar coordinates.

---

## Phase 6: Compound Screening Layer & Bioactivity Simulation
- **ChEMBL REST Client Adapter** ([`src/clients/chembl.py`](../src/clients/chembl.py)):
  - Retrieves empirical wet-lab binding and functional assays (`IC50`, `Ki`, `Kd`, `EC50` in nM).
  - Preserves molecule ChEMBL IDs and assay ChEMBL IDs.
- **Compound Screening Agent** ([`src/agents/compound.py`](../src/agents/compound.py)):
  - Evaluates top $N$ prioritized targets.
  - Enforces strict 4-tier segregation and attaches the mandatory disclaimer:
    `"Computational simulation prediction — not experimentally measured."`

---

## Phase 7: Interactive UI, Streamlit Visualization & Reporting Dashboard
- **Interactive Streamlit Dashboard** ([`app.py`](../app.py), [`src/ui/app.py`](../src/ui/app.py)):
  - Query presets (Alzheimer's, Parkinson's, ALS), parameter sliders, and duplicate submission guards.
  - Responsive 8-stage visual workflow stepper.
- **Multi-Modal Visualizations** ([`src/ui/visualizations.py`](../src/ui/visualizations.py)):
  - Horizontal bar ranking chart, 6-dimension evidence radar chart, modality distribution donut chart, and dual-trace compound bioactivity comparison.
- **Scientific Reporting & Export** ([`src/engine/reporter.py`](../src/engine/reporter.py)):
  - Generates comprehensive Markdown research reports and one-click JSON state downloads.
- **FastAPI Backend Service** ([`src/api/app.py`](../src/api/app.py)):
  - Headless API service exposing `/api/health`, `/api/investigate`, and `/api/report`.
