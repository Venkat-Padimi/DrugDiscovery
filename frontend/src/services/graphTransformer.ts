import type { ResearchGraphState, DiscoveryGraphData } from '../types';

export function stateToDiscoveryGraph(state: ResearchGraphState, maxTargets = 6): DiscoveryGraphData {
  if (!state) return { nodes: [], edges: [] };

  const diseaseName = state.disease_name || state.research_question || 'Target Pathology';
  const rankings = state.target_rankings || [];

  const nodes: any[] = [];
  const edges: any[] = [];

  // Root Disease Node
  const diseaseNodeId = 'node-disease';
  nodes.push({
    id: diseaseNodeId,
    type: 'diseaseNode',
    position: { x: 500, y: 30 },
    data: {
      label: diseaseName,
      entity: diseaseName,
      session_id: state.session_id,
      total_targets: rankings.length,
      status: state.status,
    },
  });

  const topTargets = rankings.slice(0, maxTargets);
  const spacingX = 260;
  const baseX = Math.max(50, 500 - (topTargets.length * spacingX) / 2);

  const evidenceRecords = state.evidence_records || [];
  const druggabilityDict = state.druggability_assessments || {};
  const knownCompoundsDict = state.known_active_compounds || {};
  const screeningsDict = state.compound_screenings || {};

  topTargets.forEach((r, tIdx) => {
    const sym = r.target_symbol;
    const score = r.overall_priority_score;
    const tier = r.confidence_tier?.toUpperCase() || 'MEDIUM';
    const targetName = r.target_name || sym;

    const targetNodeId = `node-target-${sym}`;
    const targetX = baseX + tIdx * spacingX;
    const targetY = 200;

    // Target Node
    nodes.push({
      id: targetNodeId,
      type: 'targetNode',
      position: { x: targetX, y: targetY },
      data: {
        symbol: sym,
        name: targetName,
        score,
        tier,
        tractability: r.tractability_summary || 'Unassessed',
        assay_status: r.experimental_validation_status || 'None',
      },
    });

    // Edge: Disease -> Target
    edges.push({
      id: `edge-disease-${sym}`,
      source: diseaseNodeId,
      target: targetNodeId,
      label: 'ASSOCIATED_WITH',
      animated: true,
      data: { relationship: 'ASSOCIATED_WITH' },
    });

    // Evidence Nodes
    const targetEv = evidenceRecords.filter((ev) => ev.target_symbol === sym).slice(0, 2);
    targetEv.forEach((ev, eIdx) => {
      const evId = `node-ev-${sym}-${eIdx}`;
      const isContradictory = Boolean(ev.is_contradictory);
      const citation = ev.citation || {};
      const relLabel = isContradictory ? 'CONTRADICTED_BY' : 'SUPPORTED_BY';

      nodes.push({
        id: evId,
        type: 'evidenceNode',
        position: { x: targetX - 70 + eIdx * 140, y: targetY + 160 },
        data: {
          target_symbol: sym,
          evidence_type: ev.evidence_type,
          pmid: citation.pmid || ev.source_database || 'PubMed',
          title: citation.title || 'Evidence Reference',
          causality: ev.causality_level || 'association',
          is_contradictory: isContradictory,
        },
      });

      edges.push({
        id: `edge-ev-${sym}-${eIdx}`,
        source: targetNodeId,
        target: evId,
        label: relLabel,
        data: { relationship: relLabel },
      });
    });

    // Druggability Node
    const drugInfo = druggabilityDict[sym];
    if (drugInfo) {
      const drugNodeId = `node-drug-${sym}`;
      nodes.push({
        id: drugNodeId,
        type: 'druggabilityNode',
        position: { x: targetX + 50, y: targetY + 300 },
        data: {
          target_symbol: sym,
          tractability_score: drugInfo.overall_tractability_score,
          modalities: Object.keys(drugInfo.modalities || {}),
        },
      });

      edges.push({
        id: `edge-drug-${sym}`,
        source: targetNodeId,
        target: drugNodeId,
        label: 'TRACTABILITY_OF',
        data: { relationship: 'TRACTABILITY_OF' },
      });
    }

    // Compound Node
    const knownList = knownCompoundsDict[sym] || [];
    const simList = screeningsDict[sym] || [];

    if (knownList.length > 0) {
      const topChembl = knownList[0];
      const compId = `node-compound-known-${sym}`;
      nodes.push({
        id: compId,
        type: 'compoundNode',
        position: { x: targetX - 60, y: targetY + 420 },
        data: {
          target_symbol: sym,
          compound_id: topChembl.compound_id,
          compound_name: topChembl.compound_name || topChembl.compound_id,
          is_empirical: true,
          activity: `${topChembl.activity_type}=${topChembl.activity_value} ${topChembl.activity_unit}`,
          disclaimer: 'Empirically measured bioactivity (ChEMBL)',
        },
      });

      edges.push({
        id: `edge-compound-known-${sym}`,
        source: compId,
        target: targetNodeId,
        label: 'TARGET_OF',
        data: { relationship: 'TARGET_OF' },
      });
    } else if (simList.length > 0) {
      const topSim = simList[0];
      const compId = `node-compound-sim-${sym}`;
      nodes.push({
        id: compId,
        type: 'compoundNode',
        position: { x: targetX - 60, y: targetY + 420 },
        data: {
          target_symbol: sym,
          compound_id: topSim.compound_id,
          compound_name: topSim.compound_id,
          is_empirical: false,
          predicted_kd: `Est. Kd: ${topSim.predicted_kd_nm} nM`,
          disclaimer: 'Computational simulation prediction — not experimentally measured.',
        },
      });

      edges.push({
        id: `edge-compound-sim-${sym}`,
        source: compId,
        target: targetNodeId,
        label: 'SCREENED_AGAINST',
        data: { relationship: 'SCREENED_AGAINST' },
      });
    }
  });

  return {
    nodes,
    edges,
    meta: {
      disease: diseaseName,
      target_count: topTargets.length,
      total_nodes: nodes.length,
      total_edges: edges.length,
    },
  };
}
