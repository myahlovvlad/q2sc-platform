from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_mcp_tool_discovery():
    health = client.get("/health")
    tools = client.get("/mcp/tools/list")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert tools.status_code == 200
    assert {tool["name"] for tool in tools.json()["tools"]} == {
        "q2sc.predict_spectrum",
        "q2sc.screen_library",
        "q2sc.reverse_analyze",
    }


def test_prediction_and_upload_critical_path():
    prediction = client.post(
        "/api/v1/predict",
        json={"structure": {"name": "Ethanol", "smiles": "CCO"}},
    )
    upload = client.post(
        "/api/v1/spectrum/upload",
        files={"file": ("spectrum.csv", b"ppm,intensity\n10,1\n", "text/csv")},
    )

    assert prediction.status_code == 200
    assert prediction.json()["status"] in {"SUCCESS", "PARKED"}
    assert upload.status_code == 200
    assert upload.json()["bytes"] == 19


def test_invalid_prediction_is_reported_as_validation_error():
    empty = client.post(
        "/api/v1/predict",
        json={"structure": {"name": "Empty", "smiles": ""}},
    )
    untokenizable = client.post(
        "/api/v1/predict",
        json={"structure": {"name": "Invalid", "smiles": "[]"}},
    )

    assert empty.status_code == 422
    assert untokenizable.status_code == 422
    assert "cannot be tokenized" in untokenizable.json()["detail"]


def test_screening_isolates_invalid_candidate():
    response = client.post(
        "/api/v1/screening/run",
        json={
            "candidates": [
                {"name": "Ethanol", "smiles": "CCO"},
                {"name": "Invalid", "smiles": "[]"},
            ],
            "instrument": {"spectral_points": 128},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["failed"] == 1
    assert all(len(row) == 128 for row in payload["intensity_matrix"])


def test_reverse_analysis_validates_signal_and_ranks_candidates():
    invalid = client.post(
        "/api/v1/reverse/analyze",
        json={"x_axis": [], "y_axis": []},
    )
    prediction = client.post(
        "/api/v1/predict",
        json={
            "structure": {"name": "Ethanol", "smiles": "CCO"},
            "instrument": {"spectral_points": 128},
        },
    ).json()
    assert prediction["spectrum"] is not None

    spectrum = prediction["spectrum"]
    valid = client.post(
        "/api/v1/reverse/analyze",
        json={
            "x_axis": spectrum["x_axis"],
            "y_axis": spectrum["y_axis"],
            "candidate_library": [
                {"name": "Ethanol", "smiles": "CCO"},
                {"name": "Invalid", "smiles": "[]"},
            ],
        },
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    candidates = valid.json()["candidates"]
    assert candidates[0]["name"] == "Ethanol"
    assert any(candidate["status"] == "PARKED" for candidate in candidates)


def test_mcp_call_and_unknown_method():
    success = client.post(
        "/mcp/tools/call",
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "q2sc.predict_spectrum",
            "params": {"structure": {"name": "Ethanol", "smiles": "CCO"}},
        },
    )
    missing = client.post(
        "/mcp/tools/call",
        json={"jsonrpc": "2.0", "id": 8, "method": "q2sc.missing", "params": {}},
    )

    assert success.status_code == 200
    assert success.json()["id"] == 7
    assert missing.status_code == 404


def test_molecule_preparation_endpoint():
    response = client.post(
        "/api/v1/molecules/prepare",
        json={"name": "Ethanol", "smiles": "CCO", "num_conformers": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["formula"] == "C2H6O"
    assert payload["preparation_method"].startswith("ETKDGv3/")
    assert len(payload["atoms"]) == 9


def test_quantum_job_submission(monkeypatch):
    class FakeTask:
        id = "quantum-test-task"

    monkeypatch.setattr("app.main.submit_quantum_job", lambda _payload: FakeTask())
    response = client.post(
        "/api/v1/quantum/jobs",
        json={"name": "Water", "smiles": "O", "method": "HF", "basis": "sto-3g"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "quantum-test-task",
        "status": "QUEUED",
        "queue": "heavy_dft",
    }


def test_quantum_interpretation_and_pdf_report():
    result = {
        "status": "SUCCESS",
        "engine": "PySCF",
        "engine_version": "test",
        "method": "HF",
        "basis": "sto-3g",
        "scf_converged": True,
        "electronic_energy_hartree": -74.9,
        "gap_ev": 12.5,
        "elapsed_sec": 1.2,
        "provenance": {"limitations": ["Test limitation"]},
    }
    interpretation = client.post(
        "/api/v1/interpret/quantum",
        json={"profile": "electronic", "result": result},
    )
    report = client.post(
        "/api/v1/reports/quantum.pdf",
        json={
            "title": "Water",
            "profile": "electronic",
            "molecule": {"name": "Water", "formula": "H2O", "canonical_smiles": "O"},
            "result": result,
            "interpretation": interpretation.json(),
        },
    )

    assert interpretation.status_code == 200
    assert "Самосогласованное поле" in interpretation.json()["findings"][0]
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")
