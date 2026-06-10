const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function readJson(res: Response) {
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export type DirectPredictionPayload = {
  structure: { name: string; smiles: string; source?: string }
  environment: { solvent_name: string; solvent_model: string; solvent_eps: number; solvent_ri: number; temperature_k: number }
  instrument: { spectroscopy_type: string; frequency_mhz: number; spectral_points: number }
  compute_mode?: string
}

export async function predictSpectrum(payload: DirectPredictionPayload) {
  const res = await fetch(`${API_BASE}/api/v1/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson(res)
}

export async function runScreening(candidates: Array<{ name: string; smiles: string }>) {
  const res = await fetch(`${API_BASE}/api/v1/screening/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidates,
      environment: { solvent_name: 'DMSO-d6', solvent_model: 'PCM', solvent_eps: 46.7, solvent_ri: 1.47, temperature_k: 298.15 },
      instrument: { spectroscopy_type: '13C_NMR', frequency_mhz: 400, spectral_points: 420 },
      max_workers: 4,
    }),
  })
  return readJson(res)
}

export async function reverseAnalyze(x_axis: number[], y_axis: number[]) {
  const res = await fetch(`${API_BASE}/api/v1/reverse/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      x_axis,
      y_axis,
      environment: { solvent_name: 'DMSO-d6', solvent_model: 'PCM', solvent_eps: 46.7, solvent_ri: 1.47, temperature_k: 298.15 },
    }),
  })
  return readJson(res)
}

export type MoleculePreparation = {
  name: string
  input_smiles: string
  canonical_smiles: string
  inchi: string
  inchi_key: string
  formula: string
  mol_block: string
  svg_2d: string
  descriptors: Record<string, number>
  conformer_energy_kcal_mol: number
  preparation_method: string
  atoms: Array<{ index: number; element: string; x: number; y: number; z: number }>
}

export async function prepareMolecule(name: string, smiles: string): Promise<MoleculePreparation> {
  const res = await fetch(`${API_BASE}/api/v1/molecules/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, smiles, num_conformers: 12 }),
  })
  return readJson(res)
}

export async function lookupPubChem(identifier: string) {
  const res = await fetch(`${API_BASE}/api/v1/references/pubchem/${encodeURIComponent(identifier)}`)
  return readJson(res)
}

export type QuantumResult = {
  status: string
  engine: string
  engine_version: string
  method: string
  basis: string
  profile?: string
  electronic_energy_hartree: number | null
  homo_ev: number | null
  lumo_ev: number | null
  gap_ev: number | null
  dipole_debye: number[]
  mulliken_charges: number[]
  cube_artifacts?: {
    electron_density?: string
    homo?: string
    lumo?: string
  }
  vibrational_analysis?: {
    approximation: string
    intensity_model: string
    modes: Array<{
      index: number
      frequency_cm_1: number
      imaginary: boolean
      reduced_mass_amu: number
      relative_ir_intensity: number
      estimated_ir_intensity_km_mol?: number
      displacements: number[][]
    }>
    spectrum: { x_axis: number[]; y_axis: number[]; x_unit: string; y_unit: string }
  } | null
  mass_spectrum_analysis?: {
    method_level: string
    ionization_model: string
    fragments: Array<{ mz: number; intensity: number; formula: string; origin: string }>
    spectrum: { x_axis: number[]; y_axis: number[]; x_unit: string; y_unit: string }
    limitations: string[]
  } | null
  qmmm_analysis?: {
    method_level: string
    dielectric_reference: number
    point_charges: Array<{ x: number; y: number; z: number; charge_e: number }>
    limitations: string[]
  } | null
  ensemble_analysis?: {
    method_level: string
    temperature_k: number
    effective_conformer_count: number
    conformers: Array<{
      id: number
      energy_kcal_mol: number
      relative_energy_kcal_mol: number
      boltzmann_weight: number
      coordinates: number[][]
    }>
    limitations: string[]
  } | null
  periodic_analysis?: {
    method_level: string
    lattice_vectors_angstrom: number[][]
    replication: number[]
    atoms: Array<{ cell_index: number; element: string; x: number; y: number; z: number }>
    limitations: string[]
  } | null
  resources?: { numeric_threads: number }
  excited_state_analysis?: {
    states: Array<{
      state: string
      energy_ev: number
      wavelength_nm: number
      oscillator_strength: number
    }>
    spectrum: { x_axis: number[]; y_axis: number[]; x_unit: string; y_unit: string }
    jablonski_model: {
      limitations: string[]
    }
  } | null
  elapsed_sec: number
  provenance: {
    calculation_class: string
    geometry_optimized_at_quantum_level: boolean
    limitations: string[]
  }
}

export type QuantumJobOptions = {
  profile?: string
  harmonicModes?: boolean
  excitedStates?: boolean
  solventName?: string
  solventEps?: number
  temperatureK?: number
  parallelJobs?: number
}

export async function submitQuantumJob(name: string, smiles: string, options: QuantumJobOptions = {}) {
  const res = await fetch(`${API_BASE}/api/v1/quantum/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      smiles,
      profile: options.profile ?? 'electronic',
      method: 'HF',
      basis: 'sto-3g',
      optimize_geometry: false,
      generate_cubes: true,
      cube_grid: 24,
      compute_harmonic_modes: options.harmonicModes ?? false,
      compute_excited_states: options.excitedStates ?? false,
      excited_states: 8,
      solvent_name: options.solventName ?? 'water',
      solvent_eps: options.solventEps ?? 78.4,
      temperature_k: options.temperatureK ?? 298.15,
      parallel_jobs: options.parallelJobs ?? 0,
    }),
  })
  return readJson(res) as Promise<{ task_id: string; status: string }>
}

export type QuantumInterpretation = {
  profile: string
  profile_name: string
  summary: string
  findings: string[]
  evidence: Array<Record<string, unknown>>
  recommendations: string[]
  limitations: string[]
  confidence: string
}

export async function interpretQuantumResult(profile: string, result: QuantumResult): Promise<QuantumInterpretation> {
  const res = await fetch(`${API_BASE}/api/v1/interpret/quantum`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile, result }),
  })
  return readJson(res)
}

export async function downloadQuantumReport(payload: {
  title: string
  profile: string
  molecule: MoleculePreparation
  result: QuantumResult
  interpretation?: QuantumInterpretation | null
}) {
  const res = await fetch(`${API_BASE}/api/v1/reports/quantum.pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'q2sc-report.pdf'
  anchor.click()
  URL.revokeObjectURL(url)
}

export type QuantumJobProgress = {
  progress: number   // 0-100
  step: string       // machine-readable step name
  message: string    // human-readable description
  state: string      // Celery task state
}

export async function waitForQuantumJob(
  taskId: string,
  onProgress?: (p: QuantumJobProgress) => void,
): Promise<QuantumResult> {
  // 900 polls × 2 s = 30 min maximum wait
  const WORKER_TIMEOUT_MS = 90_000   // warn after 90 s in PENDING/STARTED
  let pendingStartMs: number | null = null

  for (let attempt = 0; attempt < 900; attempt += 1) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/jobs/${taskId}`)
    const status = await readJson(res) as {
      ready: boolean
      successful: boolean
      result: QuantumResult
      error: string
      state: string
      progress?: number
      step?: string
      message?: string
    }
    if (status.ready && status.successful) return status.result
    if (status.ready && !status.successful) throw new Error(status.error || 'Quantum job failed')

    if (onProgress) {
      const isPending = status.state === 'PENDING' || status.state === 'STARTED'

      // Track how long we've been in pre-execution states
      if (isPending) {
        if (pendingStartMs === null) pendingStartMs = Date.now()
      } else {
        pendingStartMs = null
      }

      const pendingTooLong =
        pendingStartMs !== null && Date.now() - pendingStartMs > WORKER_TIMEOUT_MS

      // Use server-provided message; fall back to state-appropriate defaults.
      // Never pass empty strings - they cause the UI to show the generic fallback.
      const message = status.message
        || (pendingTooLong
          ? 'Воркер не отвечает — проверьте Docker (docker compose ps)'
          : isPending
            ? 'Задача в очереди, ожидание воркера…'
            : '')

      onProgress({
        progress: status.progress ?? 0,
        step: status.step || status.state.toLowerCase(),
        message,
        state: status.state,
      })
    }
    await new Promise(resolve => window.setTimeout(resolve, 2000))
  }
  throw new Error('Quantum job exceeded the 30 minute UI wait limit')
}
