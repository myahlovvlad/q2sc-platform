from worker_dft.tasks_dft import (
    _mass_fragmentation_screen,
    _parallel_job_count,
    _simulate_quantum_point,
)


def test_dft_worker_normalizes_parallelism_and_is_deterministic():
    assert 1 <= _parallel_job_count({"parallel_jobs": 0}) <= 16
    assert 1 <= _parallel_job_count({"parallel_jobs": 100}) <= 32
    assert _simulate_quantum_point(7) == _simulate_quantum_point(7)


def test_mass_fragmentation_screen_produces_traceable_spectrum():
    result = _mass_fragmentation_screen("CCO")

    assert result["method_level"] == "deterministic_single_bond_cleavage_screen"
    assert result["fragments"]
    assert len(result["spectrum"]["x_axis"]) == 1400
    assert "not a QCxMS" in result["limitations"][0]
