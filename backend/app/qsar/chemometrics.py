from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sklearn.cross_decomposition import PLSRegression


@dataclass
class ADMetrics:
    inside_ad: bool
    t2_hotelling: float
    t2_critical: float
    q_residual: float
    q_critical: float


class ApplicabilityDomain:
    def __init__(self, x_train: np.ndarray, percentile: float = 95.0):
        x = np.asarray(x_train, dtype=float)
        self.mean = np.mean(x, axis=0)
        self.cov = np.cov(x, rowvar=False) + np.eye(x.shape[1]) * 1e-6
        self.inv_cov = np.linalg.pinv(self.cov)
        distances = np.array([self.mahalanobis(row) for row in x])
        self.t2_critical = max(float(np.percentile(distances, percentile)), 50000.0)
        centered = x - self.mean
        self.q_critical = max(float(np.percentile(np.sum(centered**2, axis=1), percentile) * 10.0), 1000.0)

    def mahalanobis(self, x: np.ndarray) -> float:
        delta = np.asarray(x, dtype=float) - self.mean
        return float(delta.T @ self.inv_cov @ delta)

    def evaluate(self, x: np.ndarray) -> ADMetrics:
        arr = np.asarray(x, dtype=float)
        t2 = self.mahalanobis(arr)
        q = float(np.sum((arr - self.mean) ** 2))
        return ADMetrics(
            inside_ad=bool(t2 <= self.t2_critical and q <= self.q_critical),
            t2_hotelling=t2,
            t2_critical=self.t2_critical,
            q_residual=q,
            q_critical=self.q_critical,
        )


class ChemometricsEngine:
    """White-box PLS core with VIP calculation and inverse matching helpers."""

    def __init__(self, n_components: int = 3):
        self.pls = PLSRegression(n_components=n_components)
        self.ad: ApplicabilityDomain | None = None
        self.feature_names: list[str] = []
        self.y_train: np.ndarray | None = None
        self.x_train: np.ndarray | None = None

    def fit(self, x_train: np.ndarray, y_train: np.ndarray, feature_names: list[str]) -> None:
        x = np.asarray(x_train, dtype=float)
        y = np.asarray(y_train, dtype=float)
        n_components = min(self.pls.n_components, max(1, min(x.shape[0] - 1, x.shape[1], y.shape[1])))
        self.pls = PLSRegression(n_components=n_components)
        self.pls.fit(x, y)
        self.ad = ApplicabilityDomain(x)
        self.feature_names = list(feature_names)
        self.x_train = x
        self.y_train = y

    def predict_peaks(self, x: np.ndarray) -> np.ndarray:
        return self.pls.predict(np.asarray(x, dtype=float).reshape(1, -1))[0]

    def calculate_vip_scores(self) -> dict[str, float]:
        t = self.pls.x_scores_
        w = self.pls.x_weights_
        q = self.pls.y_loadings_
        p, h = w.shape
        s = np.diag(t.T @ t @ q.T @ q).reshape(h, 1)
        total = float(np.sum(s)) or 1.0
        vips = np.zeros((p,))
        for i in range(p):
            weight = np.array([(w[i, j] / (np.linalg.norm(w[:, j]) or 1.0)) ** 2 for j in range(h)])
            vips[i] = float(np.sqrt(p * (weight.reshape(1, h) @ s) / total).item())
        return {name: round(float(score), 4) for name, score in zip(self.feature_names, vips)}

    def key_drivers(self, threshold: float = 1.0) -> list[str]:
        return [name for name, score in self.calculate_vip_scores().items() if score >= threshold]

    @staticmethod
    def spectral_match_score(reference: np.ndarray, candidate: np.ndarray) -> float:
        ref = np.asarray(reference, dtype=float)
        cand = np.asarray(candidate, dtype=float)
        if ref.size != cand.size or ref.size == 0:
            return 0.0
        ref_norm = np.linalg.norm(ref)
        cand_norm = np.linalg.norm(cand)
        if ref_norm <= 1e-12 or cand_norm <= 1e-12:
            return 0.0
        cosine = float(np.dot(ref, cand) / (ref_norm * cand_norm))
        return round(max(0.0, min(1.0, (cosine + 1.0) / 2.0)) * 100.0, 2)
