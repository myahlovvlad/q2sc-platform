from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator


class SpectroscopyType(str, Enum):
    C13_NMR = "13C_NMR"
    H1_NMR = "1H_NMR"
    FTIR = "FTIR"
    UV_VIS = "UV_VIS"
    RAMAN = "RAMAN"


class EnvironmentContext(BaseModel):
    solvent_name: str = Field(default="DMSO-d6")
    solvent_model: Literal["PCM", "COSMO", "QM_MM_EXPLICIT", "EXPLICIT", "NONE"] = "PCM"
    solvent_eps: float = Field(default=46.7, ge=0.0)
    solvent_ri: float = Field(default=1.47, ge=1.0)
    temperature_k: float = Field(default=298.15, gt=0)
    ph: float | None = Field(default=None, ge=0, le=14)


class InstrumentContext(BaseModel):
    spectroscopy_type: SpectroscopyType = SpectroscopyType.C13_NMR
    frequency_mhz: float = Field(default=400.0, gt=0)
    spectral_points: int = Field(default=1400, ge=128, le=20000)


class StructureInput(BaseModel):
    name: str = "Untitled"
    smiles: str = Field(min_length=1)
    inchi: str | None = None
    source: Literal["manual", "pubchem", "sdf", "mcp", "screening"] = "manual"


class DirectPredictionRequest(BaseModel):
    project_id: UUID = Field(default_factory=uuid4)
    pipeline_id: UUID = Field(default_factory=uuid4)
    structure: StructureInput
    environment: EnvironmentContext = Field(default_factory=EnvironmentContext)
    instrument: InstrumentContext = Field(default_factory=InstrumentContext)
    compute_mode: Literal["fast_surrogate", "parallel_batch", "heavy_dft"] = "fast_surrogate"
    trace_enabled: bool = True


class Peak(BaseModel):
    position: float
    intensity: float
    assignment: list[int] = Field(default_factory=list)
    label: str | None = None


class ApplicabilityDomainResult(BaseModel):
    inside_ad: bool
    t2_hotelling: float
    t2_critical: float
    q_residual: float
    q_critical: float
    decision: Literal["ACCEPT", "WARN", "PARK"]


class SpectralData(BaseModel):
    x_axis: list[float]
    y_axis: list[float]
    x_unit: Literal["ppm", "cm-1", "nm"] = "ppm"
    y_unit: Literal["intensity", "absorbance", "transmittance"] = "intensity"
    peaks: list[Peak]


class InterpretationPayload(BaseModel):
    vip_scores: dict[str, float]
    key_drivers: list[str]
    expert_summary: str
    evidence: dict[str, Any]


class DirectPredictionResponse(BaseModel):
    status: Literal["SUCCESS", "PARKED", "FAILED"]
    project_id: UUID
    pipeline_id: UUID
    molecule_name: str
    smiles: str
    ad: ApplicabilityDomainResult
    spectrum: SpectralData | None
    interpretation: InterpretationPayload | None
    audit_trail: list[dict[str, Any]]


class ScreeningCandidate(BaseModel):
    name: str
    smiles: str = Field(min_length=1)
    r_group_label: str | None = None


class ScreeningRequest(BaseModel):
    project_id: UUID = Field(default_factory=uuid4)
    candidates: list[ScreeningCandidate] = Field(min_length=1)
    environment: EnvironmentContext = Field(default_factory=EnvironmentContext)
    instrument: InstrumentContext = Field(default_factory=InstrumentContext)
    max_workers: int = Field(default=4, ge=1, le=64)


class ScreeningRow(BaseModel):
    candidate_id: str
    name: str
    smiles: str
    status: Literal["SUCCESS", "PARKED", "FAILED"]
    match_score: float
    ad: ApplicabilityDomainResult | None = None
    spectrum: SpectralData | None = None


class ScreeningResponse(BaseModel):
    project_id: UUID
    total: int
    accepted: int
    parked: int
    failed: int
    ppm_axis: list[float]
    intensity_matrix: list[list[float]]
    rows: list[ScreeningRow]


class ReverseAnalysisRequest(BaseModel):
    project_id: UUID = Field(default_factory=uuid4)
    x_axis: list[float] = Field(min_length=128, max_length=20000)
    y_axis: list[float] = Field(min_length=128, max_length=20000)
    environment: EnvironmentContext = Field(default_factory=EnvironmentContext)
    constraints: dict[str, Any] = Field(default_factory=dict)
    candidate_library: list[ScreeningCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_spectrum(self) -> "ReverseAnalysisRequest":
        if len(self.x_axis) != len(self.y_axis):
            raise ValueError("x_axis and y_axis must contain the same number of points")
        return self


class ReverseCandidate(BaseModel):
    rank: int
    name: str
    smiles: str
    match_score: float
    delta_peak: float
    status: Literal["MATCH", "WEAK", "PARKED"]
    explanation: str


class ReverseAnalysisResponse(BaseModel):
    project_id: UUID
    detected_peaks: list[Peak]
    candidates: list[ReverseCandidate]
    audit_trail: list[dict[str, Any]]


class McpToolCall(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class MoleculePreparationRequest(BaseModel):
    name: str = "Untitled"
    smiles: str = Field(min_length=1)
    num_conformers: int = Field(default=12, ge=1, le=100)
    random_seed: int = 61453
    max_heavy_atoms: int = Field(default=200, ge=1, le=500)


class MoleculeAtom(BaseModel):
    index: int
    element: str
    atomic_number: int
    formal_charge: int
    x: float
    y: float
    z: float


class MoleculeBond(BaseModel):
    index: int
    atom_a: int
    atom_b: int
    order: float
    aromatic: bool


class MoleculePreparationResponse(BaseModel):
    name: str
    input_smiles: str
    canonical_smiles: str
    inchi: str
    inchi_key: str
    formula: str
    atoms: list[MoleculeAtom]
    bonds: list[MoleculeBond]
    mol_block: str
    svg_2d: str
    descriptors: dict[str, float]
    conformer_energy_kcal_mol: float
    preparation_method: str


class QuantumJobRequest(BaseModel):
    name: str = "Untitled"
    smiles: str = Field(min_length=1)
    method: Literal["HF", "DFT"] = "HF"
    basis: str = Field(default="sto-3g", min_length=1, max_length=64)
    functional: str = Field(default="b3lyp", min_length=1, max_length=64)
    charge: int = Field(default=0, ge=-10, le=10)
    spin: int = Field(default=0, ge=0, le=20)
    optimize_geometry: bool = False
    generate_cubes: bool = True
    cube_grid: int = Field(default=24, ge=16, le=60)
    compute_harmonic_modes: bool = False
    compute_excited_states: bool = False
    excited_states: int = Field(default=8, ge=1, le=30)
    max_heavy_atoms: int = Field(default=80, ge=1, le=200)
    profile: Literal[
        "electronic",
        "ir",
        "uv_vis",
        "ir_uv",
        "qcxms",
        "qmmm",
        "solvent_ensemble",
        "periodic",
        "absolute_intensity",
    ] = "electronic"
    solvent_name: str = "water"
    solvent_eps: float = Field(default=78.4, ge=1.0, le=200.0)
    temperature_k: float = Field(default=298.15, gt=0.0, le=2000.0)
    parallel_jobs: int = Field(default=0, ge=0, le=32)


class QuantumJobSubmission(BaseModel):
    task_id: str
    status: Literal["QUEUED"]
    queue: str = "heavy_dft"


class QuantumJobStatus(BaseModel):
    task_id: str
    state: str
    ready: bool
    successful: bool | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: int | None = None   # 0-100 during PROGRESS state
    step: str | None = None       # machine-readable step name
    message: str | None = None    # human-readable description


class QuantumInterpretationRequest(BaseModel):
    profile: str
    result: dict[str, Any]


class QuantumReportRequest(BaseModel):
    title: str = "Отчёт Q2SC"
    profile: str
    molecule: dict[str, Any]
    result: dict[str, Any]
    interpretation: dict[str, Any] = Field(default_factory=dict)
