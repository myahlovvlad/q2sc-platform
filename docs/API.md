# API

## `POST /api/v1/predict`

Direct structure-to-spectrum prediction.

## `POST /api/v1/screening/run`

Parallel screening over a candidate library. Returns a matrix suitable for heatmap rendering.

## `POST /api/v1/reverse/analyze`

Experimental spectrum-to-candidate ranking.

## `POST /api/v1/molecules/prepare`

Builds a chemically typed 3D conformer ensemble with RDKit ETKDGv3, selects
the lowest MMFF94/UFF conformer, and returns:

- canonical SMILES, InChI, InChIKey and formula;
- atom and bond graph with 3D coordinates;
- SDF mol block and an indexed 2D SVG;
- 2D/3D molecular descriptors and conformer energy.

## `POST /api/v1/quantum/jobs`

Submits a PySCF quantum calculation to the `heavy_dft` Celery queue. Supported
first-profile options:

- restricted/unrestricted HF or Kohn-Sham DFT;
- basis set, charge and spin;
- optional geomeTRIC optimization;
- electron-density, HOMO and LUMO cube artifacts;
- optional harmonic Hessian/normal modes and relative IR spectrum;
- optional TDHF/TDDFT vertical states, UV-Vis spectrum and basic Jablonski
  state model.

## `GET /api/v1/quantum/jobs/{task_id}`

Returns Celery state and, after completion, the quantum result with full
method/version provenance.

## Reference data

- `GET /api/v1/references/pubchem/{identifier}`
- `GET /api/v1/references/chembl/{chembl_id}`
- `GET /api/v1/references/pdb/{pdb_id}`

These endpoints normalize records while retaining source IDs, URLs, and raw
payloads.

## Reference library

- `POST /api/v1/library/import/pubchem/{identifier}`
- `POST /api/v1/library/import/chembl/{chembl_id}`
- `GET /api/v1/library/compounds?q={query}&limit={limit}`

Imported records are persisted in PostgreSQL with uniqueness by source and
source identifier. The schema also contains `reference_spectra` for the
MassBank and other spectral adapters.

## `GET /mcp/tools/list`

Returns tool schemas for MCP-like clients.

## `POST /mcp/tools/call`

Executes one of:

- `q2sc.predict_spectrum`
- `q2sc.screen_library`
- `q2sc.reverse_analyze`
