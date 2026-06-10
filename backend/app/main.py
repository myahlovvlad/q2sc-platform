from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, Response

from app.core.config import get_settings
from app.schemas import (
    DirectPredictionRequest,
    DirectPredictionResponse,
    McpToolCall,
    ReverseAnalysisRequest,
    ReverseAnalysisResponse,
    ScreeningRequest,
    ScreeningResponse,
    MoleculePreparationRequest,
    MoleculePreparationResponse,
    QuantumJobRequest,
    QuantumJobStatus,
    QuantumJobSubmission,
    QuantumInterpretationRequest,
    QuantumReportRequest,
)
from app.chemistry.interpretation import interpret_quantum_result
from app.core.resources import adaptive_worker_count, resource_snapshot
from app.reporting import build_quantum_report
from app.chemistry.molecule import prepare_molecule
from app.chemistry.library import search_reference_compounds, upsert_reference_compound
from app.chemistry.references import (
    ReferenceLookupError,
    lookup_chembl,
    lookup_pdb,
    lookup_pubchem,
)
from app.qsar.service import ENGINE
from app.tasks import celery_app, submit_quantum_job

settings = get_settings()
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(
    max_workers=adaptive_worker_count(requested=8, memory_gib_per_worker=0.5)
)

app = FastAPI(
    title="Q2SC SaaS API",
    version="0.1.0-alpha",
    default_response_class=ORJSONResponse,
    description="FastAPI orchestrator for Quantum-QSAR Spectroscopy Core.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "q2sc-api",
        "env": settings.q2sc_env,
        "resources": resource_snapshot(),
    }


@app.get("/api/v1/workers/status")
async def workers_status() -> dict[str, Any]:
    """Ping all registered Celery workers and report their state.

    Returns within ~3 s because we use a short timeout for the inspect ping.
    The frontend can call this endpoint to show a meaningful error instead of
    waiting indefinitely on a task that will never be picked up.
    """
    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        active = inspect.active() or {}
        ping = inspect.ping() or {}
        stats = inspect.stats() or {}
        heavy_dft_workers = [
            name for name in active
            if "dft" in name.lower() or any(
                q.get("name") == "heavy_dft"
                for q in (stats.get(name) or {}).get("total", {}).values()
                if isinstance(q, dict)
            )
        ]
        return {
            "broker_reachable": True,
            "online_workers": list(ping.keys()),
            "heavy_dft_workers": heavy_dft_workers,
            "heavy_dft_available": len(heavy_dft_workers) > 0 or len(active) > 0,
            "active_tasks": {
                name: len(tasks) for name, tasks in active.items()
            },
        }
    except Exception as exc:
        return {
            "broker_reachable": False,
            "online_workers": [],
            "heavy_dft_workers": [],
            "heavy_dft_available": False,
            "error": str(exc),
        }


@app.post("/api/v1/predict", response_model=DirectPredictionResponse)
async def predict(request: DirectPredictionRequest) -> DirectPredictionResponse:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(executor, ENGINE.predict, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/screening/run", response_model=ScreeningResponse)
async def run_screening(request: ScreeningRequest) -> ScreeningResponse:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(executor, ENGINE.run_screening, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/reverse/analyze", response_model=ReverseAnalysisResponse)
async def reverse_analyze(request: ReverseAnalysisRequest) -> ReverseAnalysisResponse:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(executor, ENGINE.reverse_analyze, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/spectrum/upload")
async def upload_spectrum(file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read()
    # Minimal placeholder parser: production should parse JCAMP-DX/Bruker/Agilent.
    return {"filename": file.filename, "bytes": len(raw), "status": "received", "parser": "placeholder"}


@app.post("/api/v1/molecules/prepare", response_model=MoleculePreparationResponse)
async def prepare_molecule_endpoint(request: MoleculePreparationRequest) -> MoleculePreparationResponse:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(executor, prepare_molecule, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/references/pubchem/{identifier}")
async def pubchem_reference(identifier: str) -> dict[str, Any]:
    try:
        return await lookup_pubchem(identifier)
    except ReferenceLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PubChem lookup failed: {exc}") from exc


@app.get("/api/v1/references/chembl/{chembl_id}")
async def chembl_reference(chembl_id: str) -> dict[str, Any]:
    try:
        return await lookup_chembl(chembl_id)
    except ReferenceLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ChEMBL lookup failed: {exc}") from exc


@app.get("/api/v1/references/pdb/{pdb_id}")
async def pdb_reference(pdb_id: str) -> dict[str, Any]:
    try:
        return await lookup_pdb(pdb_id)
    except ReferenceLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RCSB PDB lookup failed: {exc}") from exc


@app.post("/api/v1/library/import/pubchem/{identifier}")
async def import_pubchem_reference(identifier: str) -> dict[str, Any]:
    try:
        record = await lookup_pubchem(identifier)
        return await upsert_reference_compound(record)
    except ReferenceLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PubChem import failed: {exc}") from exc


@app.post("/api/v1/library/import/chembl/{chembl_id}")
async def import_chembl_reference(chembl_id: str) -> dict[str, Any]:
    try:
        record = await lookup_chembl(chembl_id)
        return await upsert_reference_compound(record)
    except ReferenceLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ChEMBL import failed: {exc}") from exc


@app.get("/api/v1/library/compounds")
async def reference_compound_library(q: str = "", limit: int = 50) -> dict[str, Any]:
    bounded_limit = max(1, min(limit, 200))
    try:
        records = await search_reference_compounds(q, bounded_limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Reference library is unavailable: {exc}") from exc
    return {"total": len(records), "records": records}


@app.post("/api/v1/quantum/jobs", response_model=QuantumJobSubmission)
async def create_quantum_job(request: QuantumJobRequest) -> QuantumJobSubmission:
    task = submit_quantum_job(request.model_dump())
    return QuantumJobSubmission(task_id=task.id, status="QUEUED")


@app.post("/api/v1/interpret/quantum")
async def interpret_quantum(request: QuantumInterpretationRequest) -> dict[str, Any]:
    return interpret_quantum_result(request.result, request.profile)


@app.post("/api/v1/reports/quantum.pdf")
async def quantum_report(request: QuantumReportRequest) -> Response:
    pdf = build_quantum_report(request.model_dump())
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="q2sc-report.pdf"'},
    )


@app.get("/api/v1/quantum/jobs/{task_id}", response_model=QuantumJobStatus)
async def quantum_job_status(task_id: str) -> QuantumJobStatus:
    task = celery_app.AsyncResult(task_id)
    if not task.ready():
        state = task.state
        meta: dict = task.info if isinstance(task.info, dict) else {}
        # Provide meaningful messages for pre-execution states so the UI
        # never shows a blank progress line while the task is queued/starting.
        if state == "PENDING":
            progress = meta.get("progress", 0)
            step = meta.get("step", "queued")
            message = meta.get("message", "Задача в очереди, ожидание воркера…")
        elif state == "STARTED":
            progress = meta.get("progress", 1)
            step = meta.get("step", "started")
            message = meta.get("message", "Воркер принял задачу, инициализация…")
        else:
            progress = meta.get("progress")
            step = meta.get("step")
            message = meta.get("message")
        return QuantumJobStatus(
            task_id=task_id,
            state=state,
            ready=False,
            progress=progress,
            step=step,
            message=message,
        )
    if task.successful():
        return QuantumJobStatus(
            task_id=task_id,
            state=task.state,
            ready=True,
            successful=True,
            result=task.result,
            progress=100,
        )
    return QuantumJobStatus(
        task_id=task_id,
        state=task.state,
        ready=True,
        successful=False,
        error=str(task.result),
    )


@app.get("/mcp/tools/list")
async def mcp_tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "q2sc.predict_spectrum",
                "description": "Predict a spectroscopy signal from structure and environment.",
                "input_schema": DirectPredictionRequest.model_json_schema(),
            },
            {
                "name": "q2sc.screen_library",
                "description": "Run parallel screening over a candidate library.",
                "input_schema": ScreeningRequest.model_json_schema(),
            },
            {
                "name": "q2sc.reverse_analyze",
                "description": "Analyze experimental spectrum and rank candidate structures.",
                "input_schema": ReverseAnalysisRequest.model_json_schema(),
            },
        ]
    }


@app.post("/mcp/tools/call")
async def mcp_tools_call(call: McpToolCall) -> dict[str, Any]:
    if call.method == "q2sc.predict_spectrum":
        request = DirectPredictionRequest.model_validate(call.params)
        result = await predict(request)
    elif call.method == "q2sc.screen_library":
        request = ScreeningRequest.model_validate(call.params)
        result = await run_screening(request)
    elif call.method == "q2sc.reverse_analyze":
        request = ReverseAnalysisRequest.model_validate(call.params)
        result = await reverse_analyze(request)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {call.method}")
    return {"jsonrpc": "2.0", "id": call.id, "result": result.model_dump(mode="json")}
