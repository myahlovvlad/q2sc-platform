from __future__ import annotations

import os
from celery import Celery

from app.schemas import DirectPredictionRequest, ScreeningRequest
from app.qsar.service import ENGINE

celery_app = Celery(
    "q2sc_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    result_extended=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)


def submit_quantum_job(payload: dict):
    return celery_app.send_task(
        "tasks_dft.run_pyscf_quantum",
        args=[payload],
        queue="heavy_dft",
    )


@celery_app.task(name="tasks_ai.predict_nmr_fast", queue="fast_tasks")
def predict_nmr_fast(payload: dict) -> dict:
    request = DirectPredictionRequest.model_validate(payload)
    return ENGINE.predict(request).model_dump(mode="json")


@celery_app.task(name="tasks_ai.screening_batch", queue="fast_tasks")
def screening_batch(payload: dict) -> dict:
    request = ScreeningRequest.model_validate(payload)
    return ENGINE.run_screening(request).model_dump(mode="json")
