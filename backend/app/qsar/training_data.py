from __future__ import annotations

import numpy as np
from .descriptors import DescriptorEngine


CALIBRATION_LIBRARY = [
    ("Ethanol", "CCO", 24.3, 1.36, [15.2, 58.3, 0.0, 0.0]),
    ("Butanol", "CCCCO", 24.3, 1.36, [13.9, 20.1, 34.5, 63.2]),
    ("Isopropanol", "CC(O)C", 32.7, 1.32, [22.4, 25.8, 63.1, 0.0]),
    ("Methanol", "CO", 32.7, 1.32, [49.3, 0.0, 0.0, 0.0]),
    ("Acetone", "CC(=O)C", 4.8, 1.42, [30.2, 206.1, 0.0, 0.0]),
    ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O", 4.8, 1.42, [21.1, 124.8, 131.4, 170.2]),
    ("Toluene", "Cc1ccccc1", 4.8, 1.42, [21.5, 125.1, 128.3, 137.8]),
    ("Aniline", "Nc1ccccc1", 46.7, 1.47, [115.2, 129.4, 146.1, 0.0]),
]


def build_training_matrices() -> tuple[np.ndarray, np.ndarray, list[str]]:
    engine = DescriptorEngine()
    x_rows = []
    y_rows = []
    feature_names: list[str] | None = None
    for _name, smiles, eps, ri, peaks in CALIBRATION_LIBRARY:
        result = engine.build(smiles=smiles, solvent_eps=eps, solvent_ri=ri)
        x_rows.append(result.vector)
        y_rows.append(peaks)
        feature_names = result.feature_names
    return np.vstack(x_rows), np.asarray(y_rows, dtype=float), feature_names or []
