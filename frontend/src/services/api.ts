import type {
  ResearchGraphState,
  InvestigationRequest,
  RankedTarget,
  DiscoveryGraphData,
  AgentTraceEvent,
} from '../types';
import { DEMO_INVESTIGATION_STATE } from './demoData';

const API_BASE = '/api';

export async function checkHealth(): Promise<{ status: string; platform: string }> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    return { status: 'offline', platform: 'Drug Discovery Agent Backend (Offline/Demo Mode)' };
  }
}

export async function getPresets(): Promise<Record<string, { question: string; disease_name: string }>> {
  try {
    const res = await fetch(`${API_BASE}/presets`);
    if (!res.ok) throw new Error('Failed to fetch presets');
    return await res.json();
  } catch (err) {
    return {
      "Alzheimer's Disease (TREM2 & BACE1)": {
        question: "Identify promising therapeutic targets for Alzheimer's disease.",
        disease_name: "Alzheimer's disease",
      },
      "Parkinson's Disease (SNCA & LRRK2)": {
        question: "Identify high-confidence therapeutic targets for Parkinson's disease.",
        disease_name: "Parkinson's disease",
      },
      "Amyotrophic Lateral Sclerosis (SOD1 & TARDBP)": {
        question: "Prioritize candidate therapeutic targets for Amyotrophic lateral sclerosis.",
        disease_name: "Amyotrophic lateral sclerosis",
      },
    };
  }
}

export async function runInvestigation(request: InvestigationRequest): Promise<ResearchGraphState> {
  const res = await fetch(`${API_BASE}/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Investigation failed with status ${res.status}`);
  }
  return await res.json();
}

export async function getSession(sessionId: string): Promise<ResearchGraphState> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(`Session ${sessionId} not found`);
    return await res.json();
  } catch (err) {
    return DEMO_INVESTIGATION_STATE;
  }
}

export async function getSessionTargets(sessionId: string): Promise<RankedTarget[]> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/targets`);
    if (!res.ok) throw new Error('Failed to fetch targets');
    return await res.json();
  } catch (err) {
    return DEMO_INVESTIGATION_STATE.target_rankings || [];
  }
}

export async function getSessionTargetDetail(sessionId: string, targetSymbol: string): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/targets/${targetSymbol}`);
    if (!res.ok) throw new Error('Target not found');
    return await res.json();
  } catch (err) {
    // Generate fallback from demo state
    const state = DEMO_INVESTIGATION_STATE;
    const ranking = state.target_rankings?.find((r) => r.target_symbol === targetSymbol);
    const evidence = state.evidence_records?.filter((e) => e.target_symbol === targetSymbol) || [];
    const druggability = state.druggability_assessments?.[targetSymbol] || {};
    const experimental = state.experimental_data_matches?.[targetSymbol] || [];
    const known_compounds = state.known_active_compounds?.[targetSymbol] || [];
    const simulated_compounds = state.compound_screenings?.[targetSymbol] || [];
    return {
      target_symbol: targetSymbol,
      metadata: state.identified_targets?.[targetSymbol] || {},
      ranking,
      evidence,
      druggability,
      experimental,
      known_compounds,
      simulated_compounds,
    };
  }
}

export async function getSessionGraph(sessionId: string, maxTargets = 6): Promise<DiscoveryGraphData> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/graph?max_targets=${maxTargets}`);
    if (!res.ok) throw new Error('Graph fetch failed');
    return await res.json();
  } catch (err) {
    // Return empty fallback or client will generate
    return { nodes: [], edges: [] };
  }
}

export async function getSessionAudit(sessionId: string): Promise<AgentTraceEvent[]> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/audit`);
    if (!res.ok) throw new Error('Audit fetch failed');
    return await res.json();
  } catch (err) {
    return DEMO_INVESTIGATION_STATE.audit_trace || [];
  }
}

export async function getSessionReport(sessionId: string): Promise<{ report: any; markdown: string }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/report`);
  if (!res.ok) throw new Error('Report fetch failed');
  return await res.json();
}
