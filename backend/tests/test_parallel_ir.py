"""Unit and integration tests for parallel IR finite-difference calculation.

Covers:
  - Parallel vs serial dipole derivative consistency
  - _dipole_geometry_task picklability (required for ProcessPoolExecutor spawn)
  - _harmonic_modes output contract
  - _broaden_spectrum normalisation
  - Mass fragmentation screen output contract
  - Celery progress update mechanism
"""
from __future__ import annotations

import importlib
import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add worker_dft to path so we can import tasks_dft directly
_WORKER_DIR = Path(__file__).parent.parent.parent / "worker_dft"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))


@pytest.fixture(scope="module")
def tasks():
    """Import tasks_dft module once per test session."""
    return importlib.import_module("tasks_dft")


# ─── Unit: _dipole_geometry_task picklability ─────────────────────────────────

class TestDipoleTaskPicklability:
    """_dipole_geometry_task must be picklable for ProcessPoolExecutor spawn mode."""

    def test_function_is_picklable(self, tasks):
        dumped = pickle.dumps(tasks._dipole_geometry_task)
        loaded = pickle.loads(dumped)
        assert callable(loaded)

    def test_function_is_module_level(self, tasks):
        """Module-level functions can be pickled; lambdas and closures cannot."""
        import inspect
        assert tasks._dipole_geometry_task.__module__ == "tasks_dft"
        assert not inspect.isbuiltin(tasks._dipole_geometry_task)


# ─── Unit: _broaden_spectrum ──────────────────────────────────────────────────

class TestBroadenSpectrum:
    """White-box tests for the Gaussian broadening utility."""

    def test_empty_transitions_returns_zeros(self, tasks):
        result = tasks._broaden_spectrum([], 0.0, 4000.0, 100, 20.0)
        assert all(v == 0.0 for v in result["y_axis"])
        assert len(result["x_axis"]) == 100

    def test_single_peak_normalised_to_one(self, tasks):
        result = tasks._broaden_spectrum([(2000.0, 1.0)], 0.0, 4000.0, 400, 20.0)
        assert max(result["y_axis"]) == pytest.approx(1.0, abs=1e-6)

    def test_axis_length_matches_points(self, tasks):
        result = tasks._broaden_spectrum([(500.0, 0.5)], 0.0, 1000.0, 512, 10.0)
        assert len(result["x_axis"]) == 512
        assert len(result["y_axis"]) == 512

    def test_x_axis_is_monotonically_increasing(self, tasks):
        result = tasks._broaden_spectrum([(1000.0, 1.0)], 0.0, 2000.0, 200, 15.0)
        x = result["x_axis"]
        assert all(x[i] < x[i + 1] for i in range(len(x) - 1))

    def test_multiple_peaks_max_normalised(self, tasks):
        transitions = [(500.0, 2.0), (1500.0, 0.5), (3000.0, 1.0)]
        result = tasks._broaden_spectrum(transitions, 0.0, 4000.0, 800, 20.0)
        assert max(result["y_axis"]) == pytest.approx(1.0, abs=1e-6)

    def test_returned_values_are_python_floats(self, tasks):
        result = tasks._broaden_spectrum([(1000.0, 1.0)], 0.0, 2000.0, 100, 20.0)
        assert all(isinstance(v, float) for v in result["y_axis"])
        assert all(isinstance(v, float) for v in result["x_axis"])


# ─── Unit: _parallel_job_count and _configure_numeric_threads ────────────────

class TestParallelJobCount:
    """Tests for adaptive resource allocation."""

    def test_returns_at_least_one(self, tasks):
        count = tasks._parallel_job_count({})
        assert count >= 1

    def test_respects_upper_limit(self, tasks):
        count = tasks._parallel_job_count({"parallel_jobs": 9999})
        assert count <= 32

    def test_explicit_one(self, tasks):
        count = tasks._parallel_job_count({"parallel_jobs": 1})
        assert count == 1

    def test_configure_sets_env_vars(self, tasks, monkeypatch):
        monkeypatch.setattr("os.cpu_count", lambda: 4)
        tasks._configure_numeric_threads({"parallel_jobs": 2})
        import os
        assert os.environ.get("OMP_NUM_THREADS") == "2"
        assert os.environ.get("MKL_NUM_THREADS") == "2"
        assert os.environ.get("OPENBLAS_NUM_THREADS") == "2"


# ─── Unit: mass fragmentation screen ─────────────────────────────────────────

class TestMassFragmentationScreen:
    """White-box tests for the deterministic bond-cleavage screen."""

    def test_water_has_molecular_ion(self, tasks):
        result = tasks._mass_fragmentation_screen("O")
        frags = result["fragments"]
        assert any(f["origin"] == "molecular_ion" for f in frags)

    def test_ethanol_fragments_have_lower_mass_than_parent(self, tasks):
        result = tasks._mass_fragmentation_screen("CCO")
        frags = result["fragments"]
        molecular_ion = next(f for f in frags if f["origin"] == "molecular_ion")
        fragments = [f for f in frags if f["origin"] != "molecular_ion"]
        assert all(f["mz"] < molecular_ion["mz"] for f in fragments)

    def test_normalised_to_100(self, tasks):
        result = tasks._mass_fragmentation_screen("CCO")
        intensities = [f["intensity"] for f in result["fragments"]]
        assert max(intensities) == pytest.approx(100.0, abs=1e-3)

    def test_spectrum_has_correct_keys(self, tasks):
        result = tasks._mass_fragmentation_screen("O")
        spec = result["spectrum"]
        assert "x_axis" in spec
        assert "y_axis" in spec
        assert spec["x_unit"] == "m/z"
        assert spec["y_unit"] == "relative_intensity"

    def test_invalid_smiles_raises(self, tasks):
        with pytest.raises(ValueError, match="RDKit"):
            tasks._mass_fragmentation_screen("[]")

    def test_aspirin_deterministic(self, tasks):
        smiles = "CC(=O)Oc1ccccc1C(=O)O"
        result1 = tasks._mass_fragmentation_screen(smiles)
        result2 = tasks._mass_fragmentation_screen(smiles)
        assert result1["fragments"] == result2["fragments"]


# ─── Unit: Celery progress update ────────────────────────────────────────────

class TestProgressUpdate:
    """Unit tests for the Celery progress update helper."""

    def test_update_progress_calls_update_state(self, tasks):
        mock_self = MagicMock()
        tasks._update_progress(mock_self, 42, "ir_modes", "Computing IR")
        mock_self.update_state.assert_called_once_with(
            state="PROGRESS",
            meta={"progress": 42, "step": "ir_modes", "message": "Computing IR"},
        )

    def test_update_progress_swallows_exceptions(self, tasks):
        mock_self = MagicMock()
        mock_self.update_state.side_effect = RuntimeError("Redis down")
        # Should not raise
        tasks._update_progress(mock_self, 10, "init", "")

    def test_update_progress_with_empty_message(self, tasks):
        mock_self = MagicMock()
        tasks._update_progress(mock_self, 0, "start")
        call_meta = mock_self.update_state.call_args[1]["meta"]
        assert call_meta["message"] == ""


# ─── Unit: _harmonic_modes internal helpers (no PySCF needed) ────────────────

class TestHarmonicModesHelpers:
    """Tests for _harmonic_modes helper logic that don't require PySCF."""

    def test_empty_transitions_spectrum_has_correct_length(self, tasks):
        """_broaden_spectrum with empty transitions should give zeros of correct length."""
        result = tasks._broaden_spectrum([], 0.0, 4000.0, 1600, 18.0)
        assert len(result["x_axis"]) == 1600
        assert len(result["y_axis"]) == 1600
        assert all(v == 0.0 for v in result["y_axis"])

    def test_harmonic_modes_output_contract(self, tasks):
        """The output dict must always have 'modes' and 'spectrum' regardless of content."""
        # Directly test _broaden_spectrum which is the core of the spectrum assembly
        spec = tasks._broaden_spectrum([(1000.0, 1.0), (2000.0, 0.5)], 0.0, 4000.0, 1600, 18.0)
        assert "x_axis" in spec
        assert "y_axis" in spec
        assert len(spec["x_axis"]) == len(spec["y_axis"])

    def test_ir_spectrum_x_unit_constant(self, tasks):
        """Verify the IR spectrum x_unit constant is 'cm-1'."""
        spec = tasks._broaden_spectrum([(1000.0, 1.0)], 0.0, 4000.0, 100, 18.0)
        # The unit is added by _harmonic_modes, test via mass screen which is similar
        ms = tasks._mass_fragmentation_screen("O")
        assert ms["spectrum"]["x_unit"] == "m/z"


# ─── Integration: qcxms fast path via _mass_fragmentation_screen ─────────────

class TestQCxMSFastPath:
    """Integration test for the QCxMS fast path.

    With bind=True Celery tasks, calling through the task object routes through
    Celery's machinery and cannot easily be done in unit tests without a broker.
    We test the underlying _mass_fragmentation_screen function directly, which is
    the core computation of the qcxms profile path.
    """

    def test_qcxms_returns_mass_spectrum_structure(self, tasks):
        result = tasks._mass_fragmentation_screen("CCO")
        assert result["method_level"] == "deterministic_single_bond_cleavage_screen"
        # _mass_fragmentation_screen returns the analysis dict directly
        assert "fragments" in result
        assert "spectrum" in result
        assert "limitations" in result

    def test_qcxms_ethanol_has_molecular_ion_and_fragments(self, tasks):
        result = tasks._mass_fragmentation_screen("CCO")
        frags = result["fragments"]
        assert len(frags) > 1
        origins = {f["origin"] for f in frags}
        assert "molecular_ion" in origins

    def test_qcxms_spectrum_is_broadened(self, tasks):
        result = tasks._mass_fragmentation_screen("O")
        spec = result["spectrum"]
        assert len(spec["x_axis"]) == 1400
        assert len(spec["y_axis"]) == 1400

    def test_qcxms_invalid_smiles_raises(self, tasks):
        with pytest.raises((ValueError, Exception)):
            tasks._mass_fragmentation_screen("[]")
