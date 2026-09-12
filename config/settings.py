import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    disease_association: float = Field(default=0.25, ge=0.0, le=1.0)
    genetic_evidence: float = Field(default=0.20, ge=0.0, le=1.0)
    target_tractability: float = Field(default=0.20, ge=0.0, le=1.0)
    literature_evidence: float = Field(default=0.15, ge=0.0, le=1.0)
    experimental_validation: float = Field(default=0.10, ge=0.0, le=1.0)
    safety_profile: float = Field(default=0.10, ge=0.0, le=1.0)
    contradiction_penalty_min: float = Field(default=15.0, ge=0.0)
    contradiction_penalty_max: float = Field(default=30.0, ge=0.0)

    def validate_weights(self) -> bool:
        total = (
            self.disease_association
            + self.genetic_evidence
            + self.target_tractability
            + self.literature_evidence
            + self.experimental_validation
            + self.safety_profile
        )
        return abs(total - 1.0) < 1e-4


class Settings(BaseModel):
    # App
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    dashboard_port: int = Field(default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "8501")))

    # NCBI E-utilities
    ncbi_email: str = Field(default_factory=lambda: os.getenv("NCBI_EMAIL", "researcher@example.com"))
    ncbi_tool: str = Field(default_factory=lambda: os.getenv("NCBI_TOOL", "DrugDiscoveryAgent"))
    ncbi_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("NCBI_API_KEY"))

    # Open Targets & ChEMBL
    open_targets_graphql_url: str = Field(
        default_factory=lambda: os.getenv("OPEN_TARGETS_GRAPHQL_URL", "https://api.platform.opentargets.org/api/v4/graphql")
    )
    chembl_base_url: str = Field(
        default_factory=lambda: os.getenv("CHEMBL_BASE_URL", "https://www.ebi.ac.uk/chembl/api/data")
    )

    # LLM
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    synthetic_data_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "synthetic_experimental" / "sample_target_validation_assays.json"
    )

    # Weights
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)

    @classmethod
    def load(cls) -> "Settings":
        weights_file = Path(__file__).resolve().parent / "default_weights.yaml"
        weights = ScoringWeights()
        if weights_file.exists():
            try:
                with open(weights_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    weights = ScoringWeights(**data)
            except Exception:
                pass
        return cls(scoring_weights=weights)


settings = Settings.load()
