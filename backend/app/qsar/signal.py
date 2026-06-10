from __future__ import annotations

import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve


class SignalEngine:
    """Signal processing primitives for spectroscopy workflows."""

    @staticmethod
    def snv(signal: np.ndarray) -> np.ndarray:
        arr = np.asarray(signal, dtype=float)
        mean = np.mean(arr)
        std = np.std(arr)
        if std <= 1e-12:
            return arr - mean
        return (arr - mean) / std

    @staticmethod
    def asymmetric_least_squares(y: np.ndarray, lam: float = 1e4, p: float = 0.001, n_iter: int = 10) -> np.ndarray:
        """AsLS baseline correction.

        Returns corrected signal. For invalid short arrays it returns the input centered.
        """
        y = np.asarray(y, dtype=float)
        length = len(y)
        if length < 5:
            return y - np.mean(y)
        d = diags([1, -2, 1], [0, 1, 2], shape=(length - 2, length)).tocsr()
        weights = np.ones(length)
        baseline = np.zeros(length)
        for _ in range(n_iter):
            w = diags(weights, 0).tocsr()
            z = w + lam * (d.T @ d)
            baseline = spsolve(z, weights * y)
            weights = p * (y > baseline) + (1 - p) * (y <= baseline)
        return y - baseline

    @staticmethod
    def lorentzian_expansion(shifts: np.ndarray, intensities: np.ndarray, x_axis: np.ndarray, gamma: float = 0.4) -> np.ndarray:
        x = np.asarray(x_axis, dtype=float)
        signal = np.zeros_like(x)
        for shift, intensity in zip(np.asarray(shifts, dtype=float), np.asarray(intensities, dtype=float)):
            if not np.isfinite(shift) or abs(float(shift)) < 1e-12:
                continue
            signal += float(intensity) * (gamma**2 / ((x - float(shift)) ** 2 + gamma**2))
        return signal

    @staticmethod
    def detect_top_peaks(x_axis: np.ndarray, y_axis: np.ndarray, max_peaks: int = 6, min_distance: int = 20) -> list[tuple[float, float]]:
        x = np.asarray(x_axis, dtype=float)
        y = np.asarray(y_axis, dtype=float)
        if len(x) != len(y) or len(x) == 0:
            return []
        candidates: list[tuple[int, float]] = []
        for i in range(1, len(y) - 1):
            if y[i] > y[i - 1] and y[i] > y[i + 1]:
                candidates.append((i, float(y[i])))
        candidates.sort(key=lambda item: item[1], reverse=True)
        selected: list[int] = []
        for idx, _value in candidates:
            if all(abs(idx - prev) >= min_distance for prev in selected):
                selected.append(idx)
            if len(selected) >= max_peaks:
                break
        return [(float(x[idx]), float(y[idx])) for idx in selected]
