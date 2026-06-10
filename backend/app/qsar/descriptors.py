from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

import numpy as np


ATOM_WEIGHTS = {
    "H": 1.008,
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998,
    "P": 30.974,
    "S": 32.06,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.90,
}


@dataclass(frozen=True)
class DescriptorResult:
    vector: np.ndarray
    feature_names: list[str]
    atom_count: int
    carbon_count: int
    hetero_count: int
    structure_hash: str


class DescriptorEngine:
    """Lightweight descriptor engine.

    RDKit can be added later. This fallback keeps the repository installable on
    minimal machines and is enough to demonstrate orchestration and UI paths.
    """

    token_pattern = re.compile(r"Cl|Br|[BCNOFPSI]|c|n|o|s|p|H")

    def build(self, smiles: str, solvent_eps: float, solvent_ri: float) -> DescriptorResult:
        tokens = self.token_pattern.findall(smiles)
        normalized = [t.capitalize() if len(t) == 1 else t for t in tokens]
        normalized = ["C" if t == "C" and raw == "c" else t for t, raw in zip(normalized, tokens)] if tokens else []
        if not tokens:
            raise ValueError(f"SMILES cannot be tokenized: {smiles}")

        atom_count = len(tokens)
        carbon_count = sum(1 for t in tokens if t in {"C", "c"})
        hetero_count = sum(1 for t in tokens if t not in {"C", "c", "H"})
        aromatic_count = sum(1 for t in tokens if t in {"c", "n", "o", "s", "p"})
        ring_markers = len(re.findall(r"\d", smiles))
        branch_count = smiles.count("(")
        double_bonds = smiles.count("=")
        triple_bonds = smiles.count("#")
        halogens = sum(1 for t in tokens if t in {"F", "Cl", "Br", "I"})

        weight = 0.0
        for raw in tokens:
            atom = raw.capitalize() if raw not in {"Cl", "Br"} else raw
            if raw == "c":
                atom = "C"
            weight += ATOM_WEIGHTS.get(atom, 12.0)

        polarity_proxy = hetero_count / max(atom_count, 1)
        logp_proxy = 0.45 * carbon_count + 0.8 * halogens - 0.95 * hetero_count - 0.12 * branch_count
        tpsa_proxy = 17.0 * hetero_count + 7.5 * double_bonds
        mean_charge_proxy = (hetero_count * -0.045 + halogens * -0.015 + aromatic_count * 0.01) / max(atom_count, 1)
        topology_complexity = math.log1p(atom_count + 2 * branch_count + 3 * ring_markers + double_bonds + 2 * triple_bonds)

        vector = np.array(
            [
                weight,
                logp_proxy,
                tpsa_proxy,
                atom_count,
                carbon_count,
                hetero_count,
                aromatic_count,
                ring_markers,
                topology_complexity,
                mean_charge_proxy,
                polarity_proxy,
                float(solvent_eps),
                float(solvent_ri),
            ],
            dtype=float,
        )
        return DescriptorResult(
            vector=vector,
            feature_names=[
                "molecular_weight",
                "logp_proxy",
                "tpsa_proxy",
                "atom_count",
                "carbon_count",
                "hetero_count",
                "aromatic_count",
                "ring_markers",
                "topology_complexity",
                "mean_charge_proxy",
                "polarity_proxy",
                "solvent_eps",
                "solvent_ri",
            ],
            atom_count=atom_count,
            carbon_count=carbon_count,
            hetero_count=hetero_count,
            structure_hash=hashlib.sha256(smiles.encode("utf-8")).hexdigest()[:16],
        )
