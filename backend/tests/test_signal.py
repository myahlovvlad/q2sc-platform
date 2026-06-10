import numpy as np

from app.qsar.signal import SignalEngine


def test_snv_centers_constant_signal():
    normalized = SignalEngine.snv(np.ones(16))

    assert np.allclose(normalized, 0.0)


def test_peak_detection_rejects_mismatched_axes():
    peaks = SignalEngine.detect_top_peaks(np.arange(5), np.arange(4))

    assert peaks == []


def test_lorentzian_expansion_has_peak_near_shift():
    axis = np.linspace(0.0, 100.0, 1001)
    signal = SignalEngine.lorentzian_expansion(
        shifts=np.array([40.0]),
        intensities=np.array([10.0]),
        x_axis=axis,
    )

    assert axis[int(np.argmax(signal))] == 40.0
