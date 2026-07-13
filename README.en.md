# Q2SC Platform

[Русская версия](README.md)

Q2SC is an alpha-stage research platform for computational chemistry, predictive spectroscopy, chemometrics, and traceable scientific workflows. It combines molecular preparation, quantum-chemical jobs, QSAR/QSPR models, reference data, screening, and an Electron/React interface.

## Why this project exists

Scientific modelling tools are often split across isolated scripts, desktop applications, databases, and undocumented manual steps. Q2SC explores a unified environment in which a molecular hypothesis can be prepared, calculated, compared with experimental spectra, reviewed, and reproduced through one traceable workflow.

## Core capabilities

- Molecular preparation with RDKit and external scientific data adapters.
- HF/DFT calculations through a PySCF worker.
- QSAR/QSPR and chemometric workflows with applicability-domain controls.
- Reference-data library for spectra, structures, and calculation metadata.
- Direct spectral prediction and reverse interpretation scenarios.
- FastAPI orchestration, distributed workers, PostgreSQL, Redis, and S3-compatible storage.
- Electron + Vite + React + TypeScript user interface.
- Audit-oriented data structures for scientific traceability.

## Architecture

- `backend/` — FastAPI orchestrator, molecule preparation, scientific-data adapters, reference library, QSAR core, and Celery routing.
- `frontend/` — Electron/React interface, 3D molecular visualisation, and spectral dashboards.
- `worker_dft/` — PySCF worker for HF/DFT, cube fields, harmonic modes, and excited-state calculations.
- `infra/` — PostgreSQL, Redis, MinIO, Nginx, and Docker Compose configuration.
- `docs/` — scientific architecture, domain graph, APIs, scaling, and traceability notes.

## Main research scenarios

1. **Design / direct prediction:** molecular structure + environment + instrument context → predicted spectrum, interpretation, applicability-domain assessment, and audit trail.
2. **Analytics / reverse interpretation:** experimental spectrum + constraints → preprocessing, candidate search, match scoring, and structured handling of unresolved hypotheses.
3. **Molecule / quantum:** SMILES or PubChem input → 2D/3D structure → HF/DFT calculation → energies, orbitals, density, dipole, charges, and IR/UV profiles.

## Scientific status

Q2SC is a research prototype, not validated production software. The repository includes a real PySCF calculation profile, while the bundled QSAR calibration matrix remains demonstrational. Every computational method, spectral profile, and prediction scenario requires independent scientific validation before use in research conclusions, regulated work, or operational decision-making.

The default quantum workflow represents a single gas-phase conformer. Claims about solutions, proteins, crystals, absolute intensities, kinetics, or mass spectra require appropriate solvent, QM/MM, periodic, ensemble, or fragmentation models and comparison with experimental data.

## Project leadership and authorship

Q2SC is designed and directed by **Vlad Myahlov**, Scientific Systems Engineer. The domain model, product concept, system architecture, requirements, scientific workflows, acceptance criteria, and validation logic are human-defined. Software implementation is developed through an AI-assisted engineering workflow and is subject to architectural and domain review.

## Quick start

### Linux or macOS

```bash
bash scripts/setup.sh
bash scripts/dev.sh
```

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

### Docker

```bash
cp .env.example .env
docker compose up --build
```

After startup, the backend API documentation is available at `http://127.0.0.1:8000/docs`. The desktop interface starts through Vite/Electron.

## Intended portfolio value

This repository demonstrates domain architecture for scientific software, integration of computational chemistry and laboratory data, traceability-by-design, and the translation of multidisciplinary research requirements into a testable software system.
