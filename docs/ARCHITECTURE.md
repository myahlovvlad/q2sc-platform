# Q2SC architecture

## Layers

1. Client layer: Electron + React + shadcn-style UI.
2. API/orchestration layer: FastAPI, async endpoints, MCP-like tool adapter.
3. QSAR core: descriptors, PLS chemometrics, applicability domain, signal generation, interpretation.
4. Worker layer: Celery fast worker and heavy DFT placeholder worker.
5. Storage layer: PostgreSQL for metadata/audit trail, MinIO for large spectral vectors, Redis for broker/cache.

## Process principles

Every prediction follows the same traceable chain:

`input validation -> descriptor extraction -> AD verification -> spectrum prediction -> VIP interpretation -> response/audit export`

Every reverse analysis follows:

`experimental signal ingest -> baseline correction -> SNV -> peak detection -> candidate prediction -> spectral matching -> ranked decision`

## Scaling

For local development, FastAPI uses a ThreadPoolExecutor for CPU-bound surrogate tasks. In distributed mode, the same payloads can be sent to Celery queues:

- `fast_tasks`: QSAR/PLS/AD/screening.
- `heavy_dft`: DFT/xTB/ORCA-like long calculations.

Docker Compose is deliberately aligned with Kubernetes migration: each service has isolated environment variables, storage, ports and command boundaries.
