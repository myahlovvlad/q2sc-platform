from app.schemas import DirectPredictionRequest, ScreeningRequest
from app.qsar.service import ENGINE


def test_predict_ethanol_success():
    request = DirectPredictionRequest(structure={"name": "Ethanol", "smiles": "CCO"})
    response = ENGINE.predict(request)
    assert response.status in {"SUCCESS", "PARKED"}
    assert response.project_id == request.project_id
    if response.status == "SUCCESS":
        assert response.spectrum is not None
        assert len(response.spectrum.x_axis) == request.instrument.spectral_points
        assert len(response.spectrum.x_axis) == len(response.spectrum.y_axis)
        assert [record["step_name"] for record in response.audit_trail] == [
            "Input_Validated",
            "Descriptor_Extraction",
            "Applicability_Domain",
            "Spectrum_Prediction",
            "VIP_Interpretation",
        ]


def test_screening_counts_and_matrix_shape():
    request = ScreeningRequest(
        candidates=[
            {"name": "Ethanol", "smiles": "CCO"},
            {"name": "Invalid", "smiles": "[]"},
        ],
        instrument={"spectral_points": 128},
    )

    response = ENGINE.run_screening(request)

    assert response.total == 2
    assert response.failed == 1
    assert response.accepted + response.parked + response.failed == response.total
    assert len(response.intensity_matrix) == response.total
    assert all(len(row) == 128 for row in response.intensity_matrix)
