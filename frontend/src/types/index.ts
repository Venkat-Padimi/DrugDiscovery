export type WorkflowStage =
  | 'supervisor_plan'
  | 'literature_search'
  | 'target_identification'
  | 'evidence_evaluation'
  | 'druggability_assessment'
  | 'target_ranking'
  | 'compound_screening'
  | 'supervisor_synthesis';

export interface ScoreBreakdown {
  disease_association_score: number;
  genetic_evidence_score: number;
  target_tractability_score: number;
  literature_evidence_score: number;
  experimental_validation_score: number;
  safety_profile_score: number;
  contradiction_penalty: number;
  weights_applied?: Record<string, number>;
  raw_composite_score: number;
  final_clamped_score: number;
}

export interface RankedTarget {
  target_symbol: string;
  target_name?: string;
  ensembl_id?: string;
  disease_name?: string;
  overall_priority_score: number;
  confidence_tier: 'high' | 'medium' | 'low' | string;
  confidence_score?: number;
  score_breakdown?: ScoreBreakdown;
  evidence_count?: number;
  tractability_summary?: string;
  experimental_validation_status?: string;
  biological_rationale?: string;
  safety_concerns?: string[];
  recommended_modalities?: string[];
}

export interface Citation {
  pmid?: string;
  pmcid?: string;
  doi?: string;
  title?: string;
  journal?: string;
  publication_year?: number;
  authors?: string[];
}

export interface EvidenceItem {
  evidence_id?: string;
  target_symbol: string;
  disease_name?: string;
  evidence_type: string;
  source_database?: string;
  causality_level?: string;
  is_contradictory?: boolean;
  citation?: Citation;
  summary_snippet?: string;
  confidence_score?: number;
  data_origin?: string;
}

export interface ModalityTractability {
  modality: string;
  bucket: string;
  top_category?: string;
  has_approved_drug?: boolean;
  has_clinical_precedence?: boolean;
}

export interface DruggabilityProfile {
  target_symbol: string;
  overall_tractability_score: number;
  modalities: Record<string, ModalityTractability | any>;
  small_molecule_tractable?: boolean;
  antibody_tractable?: boolean;
  protac_tractable?: boolean;
  data_origin?: string;
}

export interface ExperimentalRecord {
  experiment_id?: string;
  target_symbol: string;
  assay_type: string;
  measurement_type?: string;
  measured_value?: number;
  unit?: string;
  cell_line_or_model?: string;
  validation_status: string;
  is_synthetic?: boolean;
  data_origin?: string;
}

export interface CompoundBioactivity {
  compound_id: string;
  compound_name?: string;
  target_symbol: string;
  activity_type: string;
  activity_value: number;
  activity_unit: string;
  is_synthetic_or_simulated?: boolean;
  source_database?: string;
  chembl_assay_id?: string;
}

export interface ScreeningPrediction {
  target_symbol: string;
  compound_id: string;
  predicted_kd_nm: number;
  docking_score_kcal_mol?: number;
  affinity_tier?: string;
  method?: string;
  provenance_note?: string;
  disclaimer?: string;
}

export interface AgentTraceEvent {
  event_id?: string;
  stage: string;
  agent_name: string;
  input_summary?: string;
  output_summary?: string;
  tool_calls?: string[];
  status: 'success' | 'warning' | 'error' | 'degraded' | string;
  duration_ms?: number;
  timestamp?: string;
  error_details?: string;
}

export interface PubMedArticle {
  pmid: string;
  doi?: string;
  title: string;
  abstract?: string;
  journal?: string;
  publication_year?: number;
  authors?: string[];
  mesh_terms?: string[];
}

export interface ResearchGraphState {
  session_id: string;
  research_question: string;
  disease_name: string;
  disease_efo_id?: string;
  created_at?: string;
  current_stage?: string;
  status?: string;
  scoring_weights?: Record<string, number>;
  enable_compound_screening?: boolean;
  max_literature_results?: number;
  top_n_targets_to_screen?: number;
  retrieved_papers?: PubMedArticle[];
  paper_dois_or_pmids?: string[];
  identified_targets?: Record<string, any>;
  evidence_records?: EvidenceItem[];
  druggability_assessments?: Record<string, DruggabilityProfile>;
  experimental_data_matches?: Record<string, ExperimentalRecord[]>;
  target_rankings?: RankedTarget[];
  known_active_compounds?: Record<string, CompoundBioactivity[]>;
  compound_screenings?: Record<string, ScreeningPrediction[]>;
  audit_trace?: AgentTraceEvent[];
  errors?: any[];
  executive_summary?: string;
}

export interface GraphNodeData {
  label?: string;
  entity?: string;
  symbol?: string;
  name?: string;
  score?: number;
  tier?: string;
  tractability?: string;
  assay_status?: string;
  evidence_type?: string;
  pmid?: string;
  title?: string;
  causality?: string;
  is_contradictory?: boolean;
  tractability_score?: number;
  modalities?: string[];
  compound_id?: string;
  compound_name?: string;
  is_empirical?: boolean;
  activity?: string;
  predicted_kd?: string;
  disclaimer?: string;
  session_id?: string;
  total_targets?: number;
  status?: string;
  [key: string]: any;
}

export interface DiscoveryGraphData {
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    data: GraphNodeData;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    animated?: boolean;
    data?: { relationship: string };
  }>;
  meta?: {
    disease: string;
    target_count: number;
    total_nodes: number;
    total_edges: number;
  };
}

export interface InvestigationRequest {
  research_question: string;
  disease_name?: string;
  disease_efo_id?: string;
  enable_compound_screening?: boolean;
  top_n_targets_to_screen?: number;
  max_literature_results?: number;
  scoring_weights?: Record<string, number>;
}
