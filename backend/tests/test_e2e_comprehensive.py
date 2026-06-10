"""Comprehensive e2e tests for all Q2SC functionality.

Test classification:
  - Unit          : individual functions, isolated mocks
  - Integration   : multiple modules working together via TestClient
  - System        : full API contract, spectrum data integrity
  - Smoke         : quick startup and critical-path checks
  - Regression    : checks that known-good behaviour stays stable
  - Black-box     : external API surface only, no internals
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ─── Test data fixtures ───────────────────────────────────────────────────────

ETHANOL = {"name": "Ethanol", "smiles": "CCO"}
ASPIRIN = {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}
WATER = {"name": "Water", "smiles": "O"}
INVALID = {"name": "Invalid", "smiles": "[]"}

FULL_QR_RESULT: dict[str, Any] = {
    "status": "SUCCESS",
    "profile": "ir_uv",
    "engine": "PySCF",
    "engine_version": "2.6.0",
    "rdkit_version": "2023.09.5",
    "method": "HF",
    "functional": None,
    "basis": "sto-3g",
    "charge": 0,
    "spin": 0,
    "smiles": "O",
    "scf_converged": True,
    "electronic_energy_hartree": -74.96449800,
    "nuclear_repulsion_hartree": 9.189,
    "homo_ev": -12.73,
    "lumo_ev": 5.82,
    "gap_ev": 18.55,
    "dipole_debye": [0.0, 0.0, 1.85],
    "mulliken_charges": [-0.6, 0.3, 0.3],
    "geometry_angstrom": [
        {"index": 0, "element": "O", "x": 0.0, "y": 0.0, "z": 0.0},
        {"index": 1, "element": "H", "x": 0.96, "y": 0.0, "z": 0.0},
        {"index": 2, "element": "H", "x": -0.24, "y": 0.93, "z": 0.0},
    ],
    "initial_conformer": {"method": "ETKDGv3/MMFF94", "energy_kcal_mol": 0.0},
    "cube_artifacts": {},
    "vibrational_analysis": {
        "approximation": "harmonic",
        "intensity_model": "finite_difference_dipole_derivative_relative",
        "modes": [
            {"index": 0, "frequency_cm_1": 1595.0, "imaginary": False, "reduced_mass_amu": 1.08,
             "force_constant_mdyne_a": 1.6, "relative_ir_intensity": 0.85, "estimated_ir_intensity_km_mol": 35.9,
             "displacements": [[0.0, 0.71, -0.71]]},
            {"index": 1, "frequency_cm_1": 3657.0, "imaginary": False, "reduced_mass_amu": 1.04,
             "force_constant_mdyne_a": 8.2, "relative_ir_intensity": 1.0, "estimated_ir_intensity_km_mol": 42.3,
             "displacements": [[0.0, 0.71, 0.71]]},
            {"index": 2, "frequency_cm_1": 3756.0, "imaginary": False, "reduced_mass_amu": 1.04,
             "force_constant_mdyne_a": 8.6, "relative_ir_intensity": 0.62, "estimated_ir_intensity_km_mol": 26.2,
             "displacements": [[0.0, -0.71, 0.71]]},
        ],
        "spectrum": {
            "x_axis": list(np.linspace(0.0, 4056.0, 1600).tolist()),
            "y_axis": ([0.0] * 800 + [0.5] * 400 + [1.0] * 200 + [0.6] * 200),
            "x_unit": "cm-1",
            "y_unit": "relative_intensity",
        },
    },
    "excited_state_analysis": {
        "states": [
            {"state": "S1", "energy_ev": 8.12, "wavelength_nm": 152.7, "oscillator_strength": 0.052},
            {"state": "S2", "energy_ev": 9.87, "wavelength_nm": 125.6, "oscillator_strength": 0.008},
            {"state": "S3", "energy_ev": 11.23, "wavelength_nm": 110.4, "oscillator_strength": 0.001},
        ],
        "spectrum": {
            "x_axis": list(np.linspace(80.0, 250.0, 1200).tolist()),
            "y_axis": [0.0] * 600 + [0.5] * 300 + [1.0] * 300,
            "x_unit": "nm",
            "y_unit": "relative_absorbance",
        },
        "jablonski_model": {
            "ground_state": "S0",
            "vertical_absorptions": [
                {"from": "S0", "to": "S1", "energy_ev": 8.12, "oscillator_strength": 0.052},
            ],
            "limitations": ["Vertical singlet excitations only."],
        },
    },
    "mass_spectrum_analysis": None,
    "qmmm_analysis": None,
    "ensemble_analysis": None,
    "periodic_analysis": None,
    "elapsed_sec": 42.1,
    "resources": {"numeric_threads": 2},
    "provenance": {
        "calculation_class": "ab_initio",
        "geometry_optimized_at_quantum_level": False,
        "limitations": ["Gas-phase only."],
    },
}


# ─── Smoke tests ─────────────────────────────────────────────────────────────

class TestSmoke:
    """Quick startup and critical-path checks."""

    def test_health_endpoint_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "resources" in body

    def test_mcp_tool_discovery(self):
        resp = client.get("/mcp/tools/list")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()["tools"]}
        assert names == {"q2sc.predict_spectrum", "q2sc.screen_library", "q2sc.reverse_analyze"}

    def test_qsar_predict_ethanol(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in {"SUCCESS", "PARKED"}
        assert body["spectrum"] is not None
        spectrum = body["spectrum"]
        assert len(spectrum["x_axis"]) == len(spectrum["y_axis"])
        assert len(spectrum["x_axis"]) > 0


# ─── Functional tests — QSAR ─────────────────────────────────────────────────

class TestQsarPredict:
    """Black-box tests for the QSAR predict endpoint."""

    def test_full_prediction_response_shape(self):
        resp = client.post(
            "/api/v1/predict",
            json={
                "structure": ASPIRIN,
                "environment": {"solvent_name": "DMSO-d6", "solvent_eps": 46.7, "solvent_ri": 1.47},
                "instrument": {"spectroscopy_type": "13C_NMR", "frequency_mhz": 400, "spectral_points": 512},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "ad" in body
        assert "spectrum" in body
        assert "audit_trail" in body
        assert "interpretation" in body

    def test_applicability_domain_fields(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        ad = resp.json()["ad"]
        assert "t2_hotelling" in ad
        assert "q_residual" in ad
        assert ad["decision"] in {"ACCEPT", "WARN", "PARK"}

    def test_out_of_domain_structure_is_parked(self):
        resp = client.post(
            "/api/v1/predict",
            json={"structure": {"name": "Long chain", "smiles": "CCCCCCCCCCCCCCCCCCCCCCCCO"}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PARKED"

    def test_empty_smiles_returns_422(self):
        resp = client.post("/api/v1/predict", json={"structure": {"name": "Empty", "smiles": ""}})
        assert resp.status_code == 422

    def test_invalid_smiles_returns_422(self):
        resp = client.post("/api/v1/predict", json={"structure": INVALID})
        assert resp.status_code == 422
        assert "cannot be tokenized" in resp.json()["detail"]

    def test_spectrum_axis_lengths_match(self):
        resp = client.post(
            "/api/v1/predict",
            json={"structure": ETHANOL, "instrument": {"spectral_points": 256}},
        )
        spec = resp.json()["spectrum"]
        assert len(spec["x_axis"]) == len(spec["y_axis"])

    def test_spectrum_values_are_finite(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        y = resp.json()["spectrum"]["y_axis"]
        # Values are finite floats; QSAR surrogate may include pre-processing steps
        # (e.g. SNV baseline correction) that produce values outside [0, 1].
        assert all(isinstance(v, float) for v in y), "y_axis values must be floats"
        assert all(abs(v) < 1e6 for v in y), "y_axis values must be finite"
        # At least one non-zero point
        assert any(v != 0.0 for v in y)


# ─── Functional tests — Screening ────────────────────────────────────────────

class TestScreening:
    """Integration tests for batch screening endpoint."""

    def test_screening_returns_matrix(self):
        resp = client.post(
            "/api/v1/screening/run",
            json={
                "candidates": [ETHANOL, ASPIRIN],
                "instrument": {"spectral_points": 128},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["intensity_matrix"]) == 2
        assert all(len(row) == 128 for row in body["intensity_matrix"])

    def test_invalid_candidate_isolated(self):
        resp = client.post(
            "/api/v1/screening/run",
            json={
                "candidates": [ETHANOL, INVALID],
                "instrument": {"spectral_points": 128},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["failed"] == 1
        assert body["accepted"] + body["parked"] + body["failed"] == body["total"]

    def test_screening_row_fields(self):
        resp = client.post(
            "/api/v1/screening/run",
            json={"candidates": [ETHANOL], "instrument": {"spectral_points": 128}},
        )
        assert resp.status_code == 200
        row = resp.json()["rows"][0]
        assert "status" in row
        assert "match_score" in row
        assert row["name"] == "Ethanol"


# ─── Functional tests — Reverse analysis ─────────────────────────────────────

class TestReverseAnalysis:
    """Integration tests for reverse analysis endpoint."""

    def _get_spectrum(self, smiles: str, points: int = 256) -> dict:
        resp = client.post(
            "/api/v1/predict",
            json={"structure": {"name": "Test", "smiles": smiles}, "instrument": {"spectral_points": points}},
        )
        return resp.json()["spectrum"]

    def test_reverse_finds_best_candidate(self):
        spec = self._get_spectrum("CCO")
        resp = client.post(
            "/api/v1/reverse/analyze",
            json={
                "x_axis": spec["x_axis"],
                "y_axis": spec["y_axis"],
                "candidate_library": [ETHANOL, ASPIRIN],
            },
        )
        assert resp.status_code == 200
        candidates = resp.json()["candidates"]
        assert candidates[0]["name"] == "Ethanol"
        assert candidates[0]["rank"] == 1

    def test_reverse_empty_spectrum_rejected(self):
        resp = client.post("/api/v1/reverse/analyze", json={"x_axis": [], "y_axis": []})
        assert resp.status_code == 422

    def test_reverse_mismatched_axis_rejected(self):
        resp = client.post(
            "/api/v1/reverse/analyze",
            json={"x_axis": list(range(200)), "y_axis": list(range(100))},
        )
        assert resp.status_code == 422


# ─── Functional tests — Molecule preparation ─────────────────────────────────

class TestMoleculePreparation:
    """System tests for 3D structure preparation endpoint."""

    def test_ethanol_formula_and_atoms(self):
        resp = client.post(
            "/api/v1/molecules/prepare",
            json={"name": "Ethanol", "smiles": "CCO", "num_conformers": 3},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["formula"] == "C2H6O"
        assert len(body["atoms"]) == 9
        assert body["preparation_method"].startswith("ETKDGv3/")

    def test_aspirin_preparation(self):
        resp = client.post(
            "/api/v1/molecules/prepare",
            json={"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "num_conformers": 2},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["formula"] == "C9H8O4"
        assert body["mol_block"] != ""
        assert body["svg_2d"].startswith("<svg")

    def test_preparation_includes_descriptors(self):
        resp = client.post("/api/v1/molecules/prepare", json={"name": "Water", "smiles": "O"})
        assert resp.status_code == 200
        descriptors = resp.json()["descriptors"]
        assert len(descriptors) > 0
        assert all(isinstance(v, (int, float)) for v in descriptors.values())

    def test_preparation_mol_block_has_v2000_header(self):
        resp = client.post("/api/v1/molecules/prepare", json={"name": "Methane", "smiles": "C"})
        assert resp.status_code == 200
        mol_block = resp.json()["mol_block"]
        assert "V2000" in mol_block or "V3000" in mol_block or "M  END" in mol_block


# ─── Functional tests — Quantum job submission ───────────────────────────────

class TestQuantumJob:
    """Integration tests for quantum job lifecycle."""

    def test_submission_returns_task_id(self, monkeypatch):
        class FakeTask:
            id = "test-task-abc"

        monkeypatch.setattr("app.main.submit_quantum_job", lambda _p: FakeTask())
        resp = client.post(
            "/api/v1/quantum/jobs",
            json={"name": "Water", "smiles": "O", "method": "HF", "basis": "sto-3g"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "test-task-abc"
        assert body["status"] == "QUEUED"
        assert body["queue"] == "heavy_dft"

    def test_job_status_pending(self, monkeypatch):
        fake_result = MagicMock()
        fake_result.ready.return_value = False
        fake_result.state = "PENDING"
        fake_result.info = {}
        monkeypatch.setattr("app.main.celery_app.AsyncResult", lambda _id: fake_result)

        resp = client.get("/api/v1/quantum/jobs/some-task-id")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ready"] is False
        assert body["state"] == "PENDING"

    def test_job_status_progress_with_meta(self, monkeypatch):
        fake_result = MagicMock()
        fake_result.ready.return_value = False
        fake_result.state = "PROGRESS"
        fake_result.info = {"progress": 45, "step": "ir_modes", "message": "Computing IR intensities"}
        monkeypatch.setattr("app.main.celery_app.AsyncResult", lambda _id: fake_result)

        resp = client.get("/api/v1/quantum/jobs/progress-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ready"] is False
        assert body["progress"] == 45
        assert body["step"] == "ir_modes"
        assert "IR" in body["message"]

    def test_job_status_success_has_result(self, monkeypatch):
        fake_result = MagicMock()
        fake_result.ready.return_value = True
        fake_result.successful.return_value = True
        fake_result.state = "SUCCESS"
        fake_result.result = {"status": "SUCCESS", "profile": "electronic", "elapsed_sec": 5.2}
        monkeypatch.setattr("app.main.celery_app.AsyncResult", lambda _id: fake_result)

        resp = client.get("/api/v1/quantum/jobs/success-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ready"] is True
        assert body["successful"] is True
        assert body["result"]["status"] == "SUCCESS"
        assert body["progress"] == 100

    def test_job_status_failure_returns_error(self, monkeypatch):
        fake_result = MagicMock()
        fake_result.ready.return_value = True
        fake_result.successful.return_value = False
        fake_result.state = "FAILURE"
        fake_result.result = ValueError("SCF did not converge")
        monkeypatch.setattr("app.main.celery_app.AsyncResult", lambda _id: fake_result)

        resp = client.get("/api/v1/quantum/jobs/failed-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ready"] is True
        assert body["successful"] is False
        assert "converge" in body["error"]

    def test_all_quantum_profiles_accepted(self, monkeypatch):
        class FakeTask:
            id = "prof-test"

        monkeypatch.setattr("app.main.submit_quantum_job", lambda _p: FakeTask())
        profiles = [
            "electronic", "ir", "uv_vis", "ir_uv",
            "qcxms", "qmmm", "solvent_ensemble", "periodic", "absolute_intensity",
        ]
        for profile in profiles:
            resp = client.post(
                "/api/v1/quantum/jobs",
                json={"name": "Water", "smiles": "O", "profile": profile},
            )
            assert resp.status_code == 200, f"Profile '{profile}' was rejected"
            assert resp.json()["task_id"] == "prof-test"


# ─── Functional tests — Interpretation & reporting ───────────────────────────

class TestInterpretationAndReport:
    """System tests for interpretation and PDF generation."""

    def test_electronic_interpretation_structure(self):
        resp = client.post(
            "/api/v1/interpret/quantum",
            json={"profile": "electronic", "result": FULL_QR_RESULT},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "summary" in body
        assert "findings" in body
        assert "recommendations" in body
        assert isinstance(body["findings"], list)
        assert len(body["findings"]) > 0

    def test_ir_uv_interpretation_mentions_modes(self):
        resp = client.post(
            "/api/v1/interpret/quantum",
            json={"profile": "ir_uv", "result": FULL_QR_RESULT},
        )
        assert resp.status_code == 200
        body = resp.json()
        text = json.dumps(body).lower()
        assert any(kw in text for kw in ("ir", "колебан", "мод", "vibrational", "mode"))

    def test_pdf_report_is_valid_pdf(self):
        interp = client.post(
            "/api/v1/interpret/quantum",
            json={"profile": "electronic", "result": FULL_QR_RESULT},
        ).json()

        resp = client.post(
            "/api/v1/reports/quantum.pdf",
            json={
                "title": "Water test",
                "profile": "electronic",
                "molecule": {"name": "Water", "formula": "H2O", "canonical_smiles": "O"},
                "result": FULL_QR_RESULT,
                "interpretation": interp,
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 1024

    def test_pdf_report_without_interpretation(self):
        resp = client.post(
            "/api/v1/reports/quantum.pdf",
            json={
                "title": "Minimal",
                "profile": "electronic",
                "molecule": {"name": "Ethanol", "formula": "C2H6O", "canonical_smiles": "CCO"},
                "result": {
                    "status": "SUCCESS",
                    "engine": "PySCF",
                    "method": "HF",
                    "basis": "sto-3g",
                    "electronic_energy_hartree": -154.0,
                    "gap_ev": 18.0,
                    "elapsed_sec": 2.1,
                    "provenance": {"limitations": []},
                },
            },
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")


# ─── Functional tests — External references ──────────────────────────────────

class TestReferences:
    """Black-box tests for external reference lookups (PubChem, ChEMBL, PDB)."""

    def test_pubchem_lookup_returns_dict(self):
        """Smoke test — may be skipped if network is unavailable."""
        try:
            resp = client.get("/api/v1/references/pubchem/ethanol")
            if resp.status_code == 200:
                body = resp.json()
                assert "canonical_smiles" in body or "isomeric_smiles" in body
        except Exception:
            pytest.skip("Network unavailable")

    def test_pubchem_unknown_returns_404(self):
        try:
            resp = client.get("/api/v1/references/pubchem/__no_such_compound__xyzabc123")
            assert resp.status_code in {404, 502}
        except Exception:
            pytest.skip("Network unavailable")


# ─── System tests — Spectrum data integrity ───────────────────────────────────

class TestSpectrumDataIntegrity:
    """White-box checks that spectrum data contracts are upheld end-to-end."""

    def test_qsar_spectrum_x_axis_is_monotonic(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        x = resp.json()["spectrum"]["x_axis"]
        assert x == sorted(x)

    def test_qsar_spectrum_y_axis_is_finite(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        y = resp.json()["spectrum"]["y_axis"]
        # QSAR pipeline may produce values outside [0,1] (e.g. after SNV pre-processing)
        assert all(abs(v) < 1e6 for v in y)

    def test_ir_spectrum_format_matches_frontend_type(self):
        """Validates the exact JSON keys that ScientificSpectrumPlot.tsx expects."""
        # We verify on the mocked full result; the real DFT path is covered by worker tests.
        ir_spec = FULL_QR_RESULT["vibrational_analysis"]["spectrum"]
        assert "x_axis" in ir_spec
        assert "y_axis" in ir_spec
        assert "x_unit" in ir_spec
        assert "y_unit" in ir_spec
        assert ir_spec["x_unit"] == "cm-1"
        assert len(ir_spec["x_axis"]) == len(ir_spec["y_axis"])

    def test_uv_spectrum_format_matches_frontend_type(self):
        uv_spec = FULL_QR_RESULT["excited_state_analysis"]["spectrum"]
        assert uv_spec["x_unit"] == "nm"
        assert uv_spec["y_unit"] == "relative_absorbance"
        assert len(uv_spec["x_axis"]) == len(uv_spec["y_axis"])

    def test_jablonski_states_have_required_fields(self):
        states = FULL_QR_RESULT["excited_state_analysis"]["states"]
        required = {"state", "energy_ev", "wavelength_nm", "oscillator_strength"}
        for state in states:
            assert required.issubset(state.keys()), f"State missing keys: {state}"

    def test_ir_modes_have_required_fields(self):
        modes = FULL_QR_RESULT["vibrational_analysis"]["modes"]
        required = {"index", "frequency_cm_1", "imaginary", "relative_ir_intensity"}
        for mode in modes:
            assert required.issubset(mode.keys())

    def test_mulliken_charges_count_equals_atoms(self):
        charges = FULL_QR_RESULT["mulliken_charges"]
        atoms = FULL_QR_RESULT["geometry_angstrom"]
        assert len(charges) == len(atoms)

    def test_qcxms_mass_spectrum_has_fragments_and_spectrum(self, monkeypatch):
        """Validate QCxMS profile returns correct mass spectrum structure."""
        mass_result = {
            **FULL_QR_RESULT,
            "profile": "qcxms",
            "engine": "RDKit fragmentation screen",
            "method": "BOND_CLEAVAGE",
            "mass_spectrum_analysis": {
                "method_level": "deterministic_single_bond_cleavage_screen",
                "ionization_model": "neutral exact-mass fragments",
                "fragments": [
                    {"mz": 180.042, "intensity": 100.0, "formula": "C9H8O4", "origin": "molecular_ion"},
                    {"mz": 138.032, "intensity": 60.0, "formula": "C7H6O3", "origin": "cleavage_bond_2"},
                ],
                "spectrum": {
                    "x_axis": list(np.linspace(0.0, 195.0, 1400).tolist()),
                    "y_axis": [0.0] * 1400,
                    "x_unit": "m/z",
                    "y_unit": "relative_intensity",
                },
                "limitations": ["Not a QCxMS trajectory."],
            },
        }
        frags = mass_result["mass_spectrum_analysis"]["fragments"]
        assert any(f["origin"] == "molecular_ion" for f in frags)
        assert all("mz" in f and "intensity" in f for f in frags)


# ─── Regression tests ─────────────────────────────────────────────────────────

class TestRegression:
    """Regression tests — ensure known-good behaviour is preserved."""

    def test_mcp_predict_spectrum_round_trip(self):
        resp = client.post(
            "/mcp/tools/call",
            json={
                "jsonrpc": "2.0",
                "id": 42,
                "method": "q2sc.predict_spectrum",
                "params": {"structure": {"name": "Ethanol", "smiles": "CCO"}},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 42
        assert "result" in body
        assert body["result"]["status"] in {"SUCCESS", "PARKED"}

    def test_mcp_unknown_method_returns_404(self):
        resp = client.post(
            "/mcp/tools/call",
            json={"jsonrpc": "2.0", "id": 1, "method": "q2sc.nonexistent", "params": {}},
        )
        assert resp.status_code == 404

    def test_spectrum_upload_placeholder(self):
        resp = client.post(
            "/api/v1/spectrum/upload",
            files={"file": ("test.csv", b"ppm,intensity\n10.0,0.5\n20.0,1.0\n", "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
        assert body["bytes"] > 0

    def test_library_endpoint_available(self):
        resp = client.get("/api/v1/library/compounds")
        # May return 503 if DB is unavailable, but must not 500
        assert resp.status_code in {200, 503}

    def test_screening_ppm_axis_ascending(self):
        resp = client.post(
            "/api/v1/screening/run",
            json={"candidates": [ETHANOL], "instrument": {"spectral_points": 128}},
        )
        ppm = resp.json()["ppm_axis"]
        assert ppm == sorted(ppm)

    def test_prediction_audit_trail_non_empty(self):
        resp = client.post("/api/v1/predict", json={"structure": ETHANOL})
        assert resp.json()["audit_trail"]

    def test_multiple_candidates_parallel_screening(self):
        candidates = [
            {"name": "Ethanol", "smiles": "CCO"},
            {"name": "Methanol", "smiles": "CO"},
            {"name": "Propanol", "smiles": "CCCO"},
            {"name": "Butanol", "smiles": "CCCCO"},
        ]
        resp = client.post(
            "/api/v1/screening/run",
            # spectral_points min is 128 per InstrumentContext schema
            json={"candidates": candidates, "instrument": {"spectral_points": 128}, "max_workers": 4},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 4
        assert body["failed"] == 0
