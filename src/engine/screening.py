import abc
import re
import math
from typing import List, Optional, Tuple, Dict, Any

from src.domain.enums import DataOrigin
from src.domain.models import CompoundBioactivity, ScreeningPrediction


class CompoundScreeningEngine(abc.ABC):
    """
    Abstract interface for chemical compound screening and binding prediction.
    
    ARCHITECTURAL RULE:
    Strictly separates experimentally measured bioactivities from computational
    simulations and agent interpretations. Never present in silico predictions
    as established laboratory facts.
    """

    @abc.abstractmethod
    def screen_compounds(
        self,
        target_symbol: str,
        compound_smiles_list: List[str],
    ) -> List[ScreeningPrediction]:
        """Runs computational screening for candidate SMILES against a target."""
        pass

    @abc.abstractmethod
    def predict_affinity(
        self,
        target_symbol: str,
        smiles: str,
        compound_id: Optional[str] = None,
    ) -> ScreeningPrediction:
        """Predicts in silico binding affinity for a single molecule."""
        pass


class PhysicochemicalSimulationEngine(CompoundScreeningEngine):
    """
    Lightweight, reproducible computational screening adapter.
    Calculates deterministic molecular property descriptors (MW, LogP estimate, TPSA)
    and estimates binding feasibility score without requiring proprietary docking binaries.
    
    Explicitly labeled as COMPUTATIONAL_PREDICTION with simulation disclaimer.
    """

    def __init__(self, method_name: str = "PhysicoChemicalHeuristic_v1"):
        self.method_name = method_name

    def _estimate_molecular_weight(self, smiles: str) -> float:
        """Deterministic atomic weight estimation from SMILES string."""
        weights = {
            'C': 12.011, 'N': 14.007, 'O': 15.999, 'S': 32.06,
            'P': 30.974, 'F': 18.998, 'Cl': 35.45, 'Br': 79.904, 'I': 126.90
        }
        mw = 0.0
        # Count explicit heavy atoms
        for atom, wt in weights.items():
            count = len(re.findall(atom, smiles))
            mw += count * wt
        # Add implicit hydrogens estimate
        mw += len(re.findall(r'[cnops]', smiles)) * 1.008 + 10.0
        return round(max(50.0, mw), 2)

    def _estimate_logp(self, smiles: str) -> float:
        """Deterministic crude LogP estimate based on carbon-to-polar ratio."""
        c_count = len(re.findall(r'[Cc]', smiles))
        polar_count = len(re.findall(r'[NnOo]', smiles))
        ratio = c_count / max(1, polar_count)
        logp = (ratio * 0.4) - 0.5
        return round(min(8.0, max(-3.0, logp)), 2)

    def _estimate_tpsa(self, smiles: str) -> float:
        """Deterministic topological polar surface area estimate in Angstroms^2."""
        o_count = len(re.findall(r'[Oo]', smiles))
        n_count = len(re.findall(r'[Nn]', smiles))
        tpsa = (o_count * 20.23) + (n_count * 12.89)
        return round(max(0.0, tpsa), 2)

    def predict_affinity(
        self,
        target_symbol: str,
        smiles: str,
        compound_id: Optional[str] = None,
    ) -> ScreeningPrediction:
        """
        Calculates deterministic simulated affinity score.
        Clearly flagged as COMPUTATIONAL_PREDICTION.
        """
        cid = compound_id or f"CMPD_{abs(hash(smiles)) % 100000:05d}"
        mw = self._estimate_molecular_weight(smiles)
        logp = self._estimate_logp(smiles)
        tpsa = self._estimate_tpsa(smiles)

        # Lipinski compliance heuristic
        lipinski_violations = 0
        if mw > 500: lipinski_violations += 1
        if logp > 5: lipinski_violations += 1
        if tpsa > 140: lipinski_violations += 1

        # Heuristic docking score approximation (-12 to -4 kcal/mol)
        base_kcal = -7.5
        score_mod = (lipinski_violations * 1.5) - (min(3.0, max(0.5, logp)) * 0.4)
        pred_kcal = round(base_kcal + score_mod, 2)

        # Calculate theoretical Kd in nM from delta G: Kd = exp(deltaG / (R*T))
        # R = 1.987e-3 kcal/(mol*K), T = 298.15 K -> RT ~ 0.592 kcal/mol
        try:
            kd_molar = math.exp(pred_kcal / 0.592)
            kd_nm = round(min(1e6, max(0.1, kd_molar * 1e9)), 1)
        except OverflowError:
            kd_nm = 5000.0

        ci_lower = round(pred_kcal - 1.2, 2)
        ci_upper = round(pred_kcal + 1.2, 2)

        return ScreeningPrediction(
            compound_id=cid,
            smiles=smiles,
            target_symbol=target_symbol,
            prediction_method=self.method_name,
            predicted_binding_affinity_kcal_mol=pred_kcal,
            predicted_kd_nm=kd_nm,
            confidence_interval=(ci_lower, ci_upper),
            molecular_weight=mw,
            logp=logp,
            tpsa=tpsa,
            data_origin=DataOrigin.COMPUTATIONAL_PREDICTION,
            disclaimer="Computational simulation prediction — not experimentally measured.",
        )

    def screen_compounds(
        self,
        target_symbol: str,
        compound_smiles_list: List[str],
    ) -> List[ScreeningPrediction]:
        """Batch screening calculation for multiple molecules."""
        return [
            self.predict_affinity(target_symbol=target_symbol, smiles=smiles)
            for smiles in compound_smiles_list
        ]
