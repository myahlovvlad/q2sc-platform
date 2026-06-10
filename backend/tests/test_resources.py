from app.core.resources import adaptive_worker_count, resource_snapshot


def test_adaptive_worker_count_is_bounded():
    assert adaptive_worker_count(requested=1, item_count=100) == 1
    assert adaptive_worker_count(requested=64, item_count=2) <= 2
    assert adaptive_worker_count(item_count=0) == 1


def test_resource_snapshot_reports_capacity():
    snapshot = resource_snapshot()
    assert snapshot["logical_cpus"] >= 1
    assert snapshot["recommended_fast_workers"] >= 1
