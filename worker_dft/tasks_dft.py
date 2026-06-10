from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from celery import Celery
import numpy as np

celery_app = Celery(
    "q2sc_tasks_dft",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_track_started=True,          # emit STARTED state when worker picks up task
    result_extended=True,             # preserve PROGRESS meta in Redis result backend
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

# Profiles that need cubes (electron density, HOMO, LUMO visualization)
_CUBE_PROFILES = {"electronic", "qmmm"}


def _simulate_quantum_point(seed: int) -> float:
    rng = np.random.default_rng(seed)
    matrix = rng.normal(size=(128, 128))
    return float(np.linalg.svd(matrix, compute_uv=False)[0])


def _parallel_job_count(payload: dict) -> int:
    requested = int(payload.get("parallel_jobs", 0))
    logical_cpus = os.cpu_count() or 1
    memory_gib = 4.0
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                memory_gib = float(line.split()[1]) / (1024.0 * 1024.0)
                break
    except OSError:
        pass
    adaptive = min(max(1, logical_cpus - 2), max(1, int(memory_gib // 2.5)), 16)
    return max(1, min(requested if requested > 0 else adaptive, 32))


def _configure_numeric_threads(payload: dict) -> int:
    thread_count = _parallel_job_count(payload)
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[variable] = str(thread_count)
    return thread_count


def _prepare_geometry(smiles: str, max_heavy_atoms: int) -> tuple[object, int, float, str]:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    base = Chem.MolFromSmiles(smiles)
    if base is None:
        raise ValueError("RDKit could not parse the supplied SMILES")
    if base.GetNumAtoms() > max_heavy_atoms:
        raise ValueError(f"Molecule exceeds the {max_heavy_atoms}-heavy-atom quantum job limit")

    molecule = Chem.AddHs(base)
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = 61453
    conformer_ids = list(AllChem.EmbedMultipleConfs(molecule, numConfs=8, params=parameters))
    if not conformer_ids:
        raise ValueError("RDKit ETKDG failed to generate an initial geometry")

    properties = AllChem.MMFFGetMoleculeProperties(molecule, mmffVariant="MMFF94")
    if properties is not None:
        results = AllChem.MMFFOptimizeMoleculeConfs(
            molecule, numThreads=0, maxIters=500, mmffVariant="MMFF94"
        )
        force_field = "MMFF94"
    else:
        results = AllChem.UFFOptimizeMoleculeConfs(molecule, numThreads=0, maxIters=500)
        force_field = "UFF"
    best = min(range(len(results)), key=lambda index: results[index][1])
    return molecule, conformer_ids[best], float(results[best][1]), force_field


def _pyscf_geometry(molecule, conformer_id: int) -> list[tuple[str, tuple[float, float, float]]]:
    conformer = molecule.GetConformer(conformer_id)
    return [
        (
            atom.GetSymbol(),
            (
                float(conformer.GetAtomPosition(atom.GetIdx()).x),
                float(conformer.GetAtomPosition(atom.GetIdx()).y),
                float(conformer.GetAtomPosition(atom.GetIdx()).z),
            ),
        )
        for atom in molecule.GetAtoms()
    ]


def _cube_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 3_000_000:
        raise ValueError("Generated cube artifact is too large for the task result backend")
    return text


def _mean_field_for(molecule, method: str, functional: str):
    from pyscf import dft, scf

    restricted = molecule.spin == 0
    if method == "DFT":
        mean_field = dft.RKS(molecule) if restricted else dft.UKS(molecule)
        mean_field.xc = functional
    elif method == "HF":
        mean_field = scf.RHF(molecule) if restricted else scf.UHF(molecule)
    else:
        raise ValueError(f"Unsupported quantum method: {method}")
    mean_field.conv_tol = 1e-9
    mean_field.max_cycle = 100
    return mean_field


def _total_density_matrix(mean_field) -> np.ndarray:
    density_matrix = np.asarray(mean_field.make_rdm1())
    return np.sum(density_matrix, axis=0) if density_matrix.ndim == 3 else density_matrix


def _dipole_for_geometry(
    atom_geometry: list[tuple[str, tuple[float, float, float]]],
    basis: str,
    charge: int,
    spin: int,
    method: str,
    functional: str,
) -> np.ndarray:
    from pyscf import gto

    molecule = gto.M(
        atom=atom_geometry,
        basis=basis,
        charge=charge,
        spin=spin,
        unit="Angstrom",
        verbose=0,
    )
    mean_field = _mean_field_for(molecule, method, functional)
    mean_field.kernel()
    if not mean_field.converged:
        raise RuntimeError("Displaced-geometry SCF did not converge during IR intensity calculation")
    return np.asarray(
        mean_field.dip_moment(
            molecule,
            _total_density_matrix(mean_field),
            unit="Debye",
            verbose=0,
        ),
        dtype=float,
    )


def _dipole_geometry_task(args: tuple) -> list[float]:
    """Module-level picklable wrapper for parallel finite-difference dipole derivatives."""
    geometry, basis, charge, spin, method, functional = args
    dipole = _dipole_for_geometry(geometry, basis, charge, spin, method, functional)
    return dipole.tolist()


def _broaden_spectrum(
    transitions: list[tuple[float, float]],
    lower: float,
    upper: float,
    points: int,
    sigma: float,
) -> dict:
    axis = np.linspace(lower, upper, points)
    signal = np.zeros_like(axis)
    for position, intensity in transitions:
        signal += intensity * np.exp(-0.5 * ((axis - position) / sigma) ** 2)
    maximum = float(np.max(signal)) if signal.size else 0.0
    if maximum > 0:
        signal = signal / maximum
    return {
        "x_axis": [round(float(value), 6) for value in axis],
        "y_axis": [round(float(value), 8) for value in signal],
    }


def _mass_fragmentation_screen(smiles: str) -> dict:
    """Generate a deterministic bond-cleavage screen.

    This is an executable fragmentation model for UI/data-flow validation, not a
    replacement for QCxMS molecular dynamics.
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError("RDKit could not parse the supplied SMILES")
    candidates: list[dict] = [
        {
            "mz": float(Descriptors.ExactMolWt(molecule)),
            "intensity": 35.0,
            "formula": Chem.rdMolDescriptors.CalcMolFormula(molecule),
            "origin": "molecular_ion",
        }
    ]
    for bond in molecule.GetBonds():
        if bond.IsInRing():
            continue
        fragmented = Chem.FragmentOnBonds(molecule, [bond.GetIdx()], addDummies=False)
        fragments = Chem.GetMolFrags(fragmented, asMols=True, sanitizeFrags=True)
        for fragment in fragments:
            if fragment.GetNumHeavyAtoms() == 0:
                continue
            hetero_atoms = sum(
                1 for atom in fragment.GetAtoms() if atom.GetAtomicNum() not in (1, 6)
            )
            intensity = 15.0 + fragment.GetNumHeavyAtoms() * 5.0 + hetero_atoms * 8.0
            candidates.append(
                {
                    "mz": float(Descriptors.ExactMolWt(fragment)),
                    "intensity": intensity,
                    "formula": Chem.rdMolDescriptors.CalcMolFormula(fragment),
                    "origin": f"cleavage_bond_{bond.GetIdx()}",
                }
            )

    merged: dict[float, dict] = {}
    for candidate in candidates:
        key = round(candidate["mz"], 3)
        if key not in merged or candidate["intensity"] > merged[key]["intensity"]:
            merged[key] = {**candidate, "mz": key}
    fragments = sorted(merged.values(), key=lambda item: item["mz"])
    maximum = max(fragment["intensity"] for fragment in fragments)
    for fragment in fragments:
        fragment["intensity"] = round(100.0 * fragment["intensity"] / maximum, 4)
    transitions = [(fragment["mz"], fragment["intensity"]) for fragment in fragments]
    upper = max(fragment["mz"] for fragment in fragments) + 15.0
    return {
        "method_level": "deterministic_single_bond_cleavage_screen",
        "ionization_model": "neutral exact-mass fragments; no ion dynamics",
        "fragments": fragments,
        "spectrum": {
            **_broaden_spectrum(transitions, 0.0, upper, 1400, 0.18),
            "x_unit": "m/z",
            "y_unit": "relative_intensity",
        },
        "limitations": [
            "This is not a QCxMS/QCEIMS trajectory calculation.",
            "Ionization energetics, rearrangements, collision energy, charge localization, and instrument response are not modeled.",
        ],
    }


def _conformer_ensemble(smiles: str, temperature_k: float, count: int = 16) -> dict:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = 61453
    conformer_ids = list(AllChem.EmbedMultipleConfs(molecule, numConfs=count, params=parameters))
    properties = AllChem.MMFFGetMoleculeProperties(molecule, mmffVariant="MMFF94")
    if properties is not None:
        optimized = AllChem.MMFFOptimizeMoleculeConfs(
            molecule, numThreads=0, maxIters=500, mmffVariant="MMFF94"
        )
        force_field = "MMFF94"
    else:
        optimized = AllChem.UFFOptimizeMoleculeConfs(molecule, numThreads=0, maxIters=500)
        force_field = "UFF"
    energies = np.asarray([float(item[1]) for item in optimized], dtype=float)
    relative = energies - float(np.min(energies))
    gas_constant_kcal = 0.00198720425864083
    weights = np.exp(-relative / (gas_constant_kcal * temperature_k))
    weights = weights / np.sum(weights)
    conformers = []
    for conformer_id, energy, relative_energy, weight in zip(
        conformer_ids, energies, relative, weights
    ):
        conformer = molecule.GetConformer(int(conformer_id))
        conformers.append(
            {
                "id": int(conformer_id),
                "energy_kcal_mol": round(float(energy), 6),
                "relative_energy_kcal_mol": round(float(relative_energy), 6),
                "boltzmann_weight": round(float(weight), 8),
                "coordinates": [
                    [
                        round(float(conformer.GetAtomPosition(index).x), 5),
                        round(float(conformer.GetAtomPosition(index).y), 5),
                        round(float(conformer.GetAtomPosition(index).z), 5),
                    ]
                    for index in range(molecule.GetNumAtoms())
                ],
            }
        )
    conformers.sort(key=lambda item: item["relative_energy_kcal_mol"])
    return {
        "method_level": f"ETKDGv3/{force_field}_boltzmann_ensemble",
        "temperature_k": temperature_k,
        "conformers": conformers,
        "effective_conformer_count": round(
            float(1.0 / np.sum(np.square(weights))), 6
        ),
        "limitations": [
            "The ensemble is sampled and weighted at a molecular-mechanics level.",
            "Explicit solvent molecules and quantum free-energy corrections are not included.",
        ],
    }


def _periodic_supercell_preview(geometry: list[dict], cell_angstrom: float = 18.0) -> dict:
    replicas = []
    for cell_index, translation in enumerate(
        ((0.0, 0.0, 0.0), (cell_angstrom, 0.0, 0.0), (0.0, cell_angstrom, 0.0), (cell_angstrom, cell_angstrom, 0.0))
    ):
        for atom in geometry:
            replicas.append(
                {
                    "cell_index": cell_index,
                    "element": atom["element"],
                    "x": round(atom["x"] + translation[0], 6),
                    "y": round(atom["y"] + translation[1], 6),
                    "z": round(atom["z"] + translation[2], 6),
                }
            )
    return {
        "method_level": "periodic_geometry_supercell_preview",
        "lattice_vectors_angstrom": [
            [cell_angstrom, 0.0, 0.0],
            [0.0, cell_angstrom, 0.0],
            [0.0, 0.0, cell_angstrom],
        ],
        "replication": [2, 2, 1],
        "atoms": replicas,
        "limitations": [
            "The displayed supercell is periodic geometry preparation, not a periodic electronic-structure calculation.",
            "A crystal structure, k-point mesh, pseudopotentials, and a PySCF-PBC/plane-wave calculation are required for periodic energies and bands.",
        ],
    }


def _apply_embedding(mean_field, molecule, dielectric: float):
    from pyscf import qmmm

    center = np.mean(molecule.atom_coords(unit="Angstrom"), axis=0)
    radius = max(4.0, float(np.max(np.linalg.norm(molecule.atom_coords(unit="Angstrom") - center, axis=1))) + 2.5)
    coordinates = np.asarray(
        [
            center + [radius, 0, 0],
            center + [-radius, 0, 0],
            center + [0, radius, 0],
            center + [0, -radius, 0],
            center + [0, 0, radius],
            center + [0, 0, -radius],
        ]
    )
    magnitude = min(0.35, 0.08 + np.log10(max(dielectric, 1.0)) * 0.08)
    charges = np.asarray([magnitude, -magnitude, magnitude, -magnitude, magnitude, -magnitude])
    embedded = qmmm.mm_charge(mean_field, coordinates, charges, unit="Angstrom")
    analysis = {
        "method_level": "electrostatic_point_charge_embedding",
        "dielectric_reference": dielectric,
        "point_charges": [
            {
                "x": round(float(coordinate[0]), 6),
                "y": round(float(coordinate[1]), 6),
                "z": round(float(coordinate[2]), 6),
                "charge_e": round(float(charge), 6),
            }
            for coordinate, charge in zip(coordinates, charges)
        ],
        "limitations": [
            "This is an electrostatic embedding demonstration, not a complete bonded QM/MM model.",
            "No MM force field, link atoms, polarization, or molecular environment trajectory is included.",
        ],
    }
    return embedded, analysis


def _harmonic_modes(mean_field, method: str, functional: str, basis: str, n_workers: int = 1) -> dict:
    """Compute harmonic IR modes with parallelised finite-difference dipole derivatives.

    n_workers > 1 submits all (plus, minus) displacement SCF calls to a
    ProcessPoolExecutor so that the 2N serial calls become ~2N/n_workers rounds.
    """
    from pyscf.hessian import thermo

    molecule = mean_field.mol
    hessian = mean_field.Hessian().kernel()
    analysis = thermo.harmonic_analysis(molecule, hessian)
    raw_frequencies = np.asarray(analysis["freq_wavenumber"])
    frequencies = np.where(
        np.abs(np.imag(raw_frequencies)) > 1e-8,
        -np.abs(np.imag(raw_frequencies)),
        np.real(raw_frequencies),
    ).astype(float)
    normal_modes = np.real(np.asarray(analysis["norm_mode"])).astype(float)
    reduced_masses = np.asarray(analysis["reduced_mass"], dtype=float)
    force_constants = np.asarray(analysis["force_const_dyne"], dtype=float)

    base_coords = molecule.atom_coords(unit="Angstrom")
    symbols = [molecule.atom_symbol(index) for index in range(molecule.natm)]
    displacement = 0.005
    charge = molecule.charge
    spin = molecule.spin

    # Build displacement geometry task list: all plus then all minus
    tasks_plus: list[tuple] = []
    tasks_minus: list[tuple] = []
    valid_indices: list[int] = []

    for index, (frequency, mode) in enumerate(zip(frequencies, normal_modes)):
        if not np.isfinite(frequency):
            continue
        valid_indices.append(index)
        plus = [
            (sym, tuple(float(c) for c in coords + displacement * vec))
            for sym, coords, vec in zip(symbols, base_coords, mode)
        ]
        minus = [
            (sym, tuple(float(c) for c in coords - displacement * vec))
            for sym, coords, vec in zip(symbols, base_coords, mode)
        ]
        tasks_plus.append((plus, basis, charge, spin, method, functional))
        tasks_minus.append((minus, basis, charge, spin, method, functional))

    all_tasks = tasks_plus + tasks_minus
    n_valid = len(valid_indices)

    if n_valid == 0:
        return {
            "approximation": "harmonic",
            "intensity_model": "finite_difference_dipole_derivative_relative",
            "modes": [],
            "spectrum": {
                **_broaden_spectrum([], 0.0, 4000.0, 1600, 18.0),
                "x_unit": "cm-1",
                "y_unit": "relative_intensity",
            },
        }

    # Run dipole calculations: parallel when n_workers > 1
    if n_workers > 1 and len(all_tasks) > 2:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as pool:
            all_dipoles_raw = list(pool.map(_dipole_geometry_task, all_tasks))
    else:
        all_dipoles_raw = [_dipole_geometry_task(task) for task in all_tasks]

    dipoles_plus = [np.array(d) for d in all_dipoles_raw[:n_valid]]
    dipoles_minus = [np.array(d) for d in all_dipoles_raw[n_valid:]]

    mode_records: list[dict] = []
    transitions: list[tuple[float, float]] = []

    for i, index in enumerate(valid_indices):
        frequency = float(frequencies[index])
        mode = normal_modes[index]
        derivative = (dipoles_plus[i] - dipoles_minus[i]) / (2.0 * displacement)
        relative_intensity = float(np.dot(derivative, derivative))
        if frequency > 0:
            transitions.append((frequency, relative_intensity))
        estimated_absolute = relative_intensity * 42.255
        mode_records.append(
            {
                "index": index,
                "frequency_cm_1": round(frequency, 6),
                "imaginary": bool(frequency < 0),
                "reduced_mass_amu": round(float(reduced_masses[index]), 6),
                "force_constant_mdyne_a": round(float(force_constants[index]), 6),
                "relative_ir_intensity": round(relative_intensity, 8),
                "estimated_ir_intensity_km_mol": round(estimated_absolute, 8),
                "displacements": [
                    [round(float(component), 8) for component in atom_vector]
                    for atom_vector in mode
                ],
            }
        )

    upper = max([f for f, _ in transitions] or [4000.0]) + 300.0
    return {
        "approximation": "harmonic",
        "intensity_model": "finite_difference_dipole_derivative_relative",
        "modes": mode_records,
        "spectrum": {
            **_broaden_spectrum(transitions, 0.0, upper, 1600, 18.0),
            "x_unit": "cm-1",
            "y_unit": "relative_intensity",
        },
    }


def _excited_states(mean_field, count: int) -> dict:
    if mean_field.mol.spin != 0:
        raise ValueError("The first excited-state profile currently supports closed-shell systems only")

    td_method = mean_field.TDDFT() if mean_field.__class__.__module__.startswith("pyscf.dft") else mean_field.TDHF()
    td_method.nstates = count
    energies, _amplitudes = td_method.kernel()
    oscillator_strengths = np.asarray(td_method.oscillator_strength(), dtype=float)
    energies_ev = np.asarray(energies, dtype=float) * 27.211386245988
    transitions = []
    states = []
    for index, (energy_ev, oscillator_strength) in enumerate(
        zip(energies_ev, oscillator_strengths), start=1
    ):
        wavelength_nm = 1239.8419843320026 / float(energy_ev)
        transitions.append((wavelength_nm, float(oscillator_strength)))
        states.append(
            {
                "state": f"S{index}",
                "energy_ev": round(float(energy_ev), 8),
                "wavelength_nm": round(wavelength_nm, 6),
                "oscillator_strength": round(float(oscillator_strength), 8),
            }
        )
    wavelengths = [position for position, _intensity in transitions]
    lower = max(80.0, min(wavelengths) - 50.0)
    upper = min(1200.0, max(wavelengths) + 100.0)
    return {
        "states": states,
        "spectrum": {
            **_broaden_spectrum(transitions, lower, upper, 1200, 12.0),
            "x_unit": "nm",
            "y_unit": "relative_absorbance",
        },
        "jablonski_model": {
            "ground_state": "S0",
            "vertical_absorptions": [
                {
                    "from": "S0",
                    "to": state["state"],
                    "energy_ev": state["energy_ev"],
                    "oscillator_strength": state["oscillator_strength"],
                }
                for state in states
            ],
            "limitations": [
                "Vertical singlet excitations only.",
                "No excited-state geometry relaxation, triplet manifold, spin-orbit coupling, or rate constants.",
            ],
        },
    }


def _update_progress(task_self, progress: int, step: str, message: str = "") -> None:
    """Emit a Celery PROGRESS state so the API can stream it to the UI."""
    try:
        task_self.update_state(
            state="PROGRESS",
            meta={"progress": progress, "step": step, "message": message},
        )
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="tasks_dft.run_pyscf_quantum",
    queue="heavy_dft",
    soft_time_limit=1800,
    time_limit=1860,
)
def run_pyscf_quantum(self, payload: dict) -> dict:
    """Run an actual ab initio HF or Kohn-Sham DFT calculation with PySCF.

    Parallel finite-difference IR intensities reduce wall time by ~n_workers×.
    Progress states are emitted via Celery so the polling UI can show a live bar.
    """
    from rdkit import __version__ as rdkit_version

    started = time.time()
    _update_progress(self, 2, "init", "Запуск задачи")
    numeric_threads = _configure_numeric_threads(payload)
    profile = str(payload.get("profile", "electronic"))
    smiles = str(payload["smiles"])

    # ── Fast path: QCxMS bond-cleavage screen (no PySCF needed) ─────────────
    if profile == "qcxms":
        _update_progress(self, 40, "qcxms", "Фрагментационный скрининг")
        mass_analysis = _mass_fragmentation_screen(smiles)
        _update_progress(self, 95, "done", "Масс-спектр рассчитан")
        return {
            "status": "SUCCESS",
            "profile": profile,
            "engine": "RDKit fragmentation screen",
            "engine_version": rdkit_version,
            "method": "BOND_CLEAVAGE",
            "basis": "not_applicable",
            "scf_converged": False,
            "electronic_energy_hartree": None,
            "homo_ev": None,
            "lumo_ev": None,
            "gap_ev": None,
            "dipole_debye": [],
            "mulliken_charges": [],
            "cube_artifacts": {},
            "vibrational_analysis": None,
            "excited_state_analysis": None,
            "mass_spectrum_analysis": mass_analysis,
            "elapsed_sec": round(time.time() - started, 4),
            "resources": {"numeric_threads": numeric_threads},
            "provenance": {
                "calculation_class": mass_analysis["method_level"],
                "geometry_optimized_at_quantum_level": False,
                "limitations": mass_analysis["limitations"],
            },
        }

    from pyscf import __version__ as pyscf_version
    from pyscf import gto
    from pyscf.tools import cubegen

    # ── Geometry ─────────────────────────────────────────────────────────────
    _update_progress(self, 8, "geometry", "Подготовка 3D-геометрии (RDKit ETKDG)")
    molecule, conformer_id, conformer_energy, force_field = _prepare_geometry(
        smiles,
        int(payload.get("max_heavy_atoms", 80)),
    )
    geometry = _pyscf_geometry(molecule, conformer_id)

    # ── PySCF molecule ────────────────────────────────────────────────────────
    _update_progress(self, 15, "scf_init", "Инициализация базисного набора")
    quantum_molecule = gto.M(
        atom=geometry,
        basis=str(payload.get("basis", "sto-3g")),
        charge=int(payload.get("charge", 0)),
        spin=int(payload.get("spin", 0)),
        unit="Angstrom",
        verbose=0,
    )
    method = str(payload.get("method", "HF")).upper()
    functional = str(payload.get("functional", "b3lyp"))
    basis = str(payload.get("basis", "sto-3g"))
    mean_field = _mean_field_for(quantum_molecule, method, functional)

    qmmm_analysis = None
    if profile == "qmmm":
        _update_progress(self, 18, "qmmm_embed", "Настройка QM/MM-окружения")
        mean_field, qmmm_analysis = _apply_embedding(
            mean_field,
            quantum_molecule,
            float(payload.get("solvent_eps", 78.4)),
        )

    # ── SCF convergence ───────────────────────────────────────────────────────
    _update_progress(self, 22, "scf_run", "Итерации самосогласованного поля (SCF)")
    energy_hartree = float(mean_field.kernel())
    if not mean_field.converged:
        raise RuntimeError("PySCF SCF procedure did not converge")
    _update_progress(self, 38, "scf_done", "SCF сошёлся, анализ МО")

    if bool(payload.get("optimize_geometry", False)):
        _update_progress(self, 40, "geom_opt", "Оптимизация геометрии")
        from pyscf.geomopt.geometric_solver import optimize
        quantum_molecule = optimize(mean_field, maxsteps=80)
        mean_field = _mean_field_for(quantum_molecule, method, functional)
        energy_hartree = float(mean_field.kernel())
        if not mean_field.converged:
            raise RuntimeError("PySCF SCF did not converge after geometry optimization")

    # ── MO energies, charges, dipole ─────────────────────────────────────────
    mo_energy = np.asarray(mean_field.mo_energy)
    mo_occupation = np.asarray(mean_field.mo_occ)
    if mo_energy.ndim != 1:
        mo_energy = mo_energy[0]
        mo_occupation = mo_occupation[0]
    occupied = np.flatnonzero(mo_occupation > 0)
    virtual = np.flatnonzero(mo_occupation == 0)
    homo_index = int(occupied[-1])
    lumo_index = int(virtual[0])
    hartree_to_ev = 27.211386245988
    homo_ev = float(mo_energy[homo_index] * hartree_to_ev)
    lumo_ev = float(mo_energy[lumo_index] * hartree_to_ev)

    density_for_population = _total_density_matrix(mean_field)
    _populations, charges = mean_field.mulliken_pop(
        quantum_molecule,
        density_for_population,
        verbose=0,
    )
    dipole = mean_field.dip_moment(
        quantum_molecule,
        density_for_population,
        unit="Debye",
        verbose=0,
    )

    # ── Cube files (only for profiles that visualise electron density) ────────
    cube_artifacts: dict[str, str] = {}
    should_generate_cubes = (
        bool(payload.get("generate_cubes", True))
        and profile in _CUBE_PROFILES
    )
    if should_generate_cubes:
        _update_progress(self, 45, "cubes", "Генерация кубических файлов (плотность, HOMO, LUMO)")
        grid = int(payload.get("cube_grid", 24))
        coefficients = np.asarray(mean_field.mo_coeff)
        if coefficients.ndim == 3:
            coefficients = coefficients[0]
        with TemporaryDirectory(prefix="q2sc-pyscf-") as directory:
            root = Path(directory)
            density_path = root / "density.cube"
            homo_path = root / "homo.cube"
            lumo_path = root / "lumo.cube"
            cubegen.density(
                quantum_molecule,
                str(density_path),
                density_for_population,
                nx=grid,
                ny=grid,
                nz=grid,
            )
            cubegen.orbital(
                quantum_molecule,
                str(homo_path),
                coefficients[:, homo_index],
                nx=grid,
                ny=grid,
                nz=grid,
            )
            cubegen.orbital(
                quantum_molecule,
                str(lumo_path),
                coefficients[:, lumo_index],
                nx=grid,
                ny=grid,
                nz=grid,
            )
            cube_artifacts = {
                "electron_density": _cube_text(density_path),
                "homo": _cube_text(homo_path),
                "lumo": _cube_text(lumo_path),
            }
        _update_progress(self, 55, "cubes_done", "Кубические файлы готовы")

    # ── Harmonic IR modes (parallel finite-difference dipole derivatives) ─────
    vibrational_analysis = None
    compute_ir = bool(payload.get("compute_harmonic_modes", False)) or profile in {
        "ir",
        "ir_uv",
        "absolute_intensity",
    }
    if compute_ir:
        n_ir_workers = max(1, numeric_threads)
        _update_progress(
            self,
            50 if not should_generate_cubes else 58,
            "ir_modes",
            f"Нормальные моды и ИК-интенсивности (параллельно, {n_ir_workers} ядер)",
        )
        vibrational_analysis = _harmonic_modes(
            mean_field, method, functional, basis, n_workers=n_ir_workers
        )
        _update_progress(self, 78, "ir_done", f"ИК-спектр: {len(vibrational_analysis['modes'])} мод")

    # ── Excited states (UV-Vis / Jablonski) ───────────────────────────────────
    excited_state_analysis = None
    compute_uv = bool(payload.get("compute_excited_states", False)) or profile in {
        "uv_vis",
        "ir_uv",
    }
    if compute_uv:
        _update_progress(self, 80, "uv_vis", "Возбуждённые состояния TDHF/TDDFT")
        excited_state_analysis = _excited_states(
            mean_field,
            int(payload.get("excited_states", 8)),
        )
        _update_progress(
            self,
            90,
            "uv_done",
            f"UV-Vis: {len(excited_state_analysis['states'])} состояний",
        )

    # ── Profile-specific analyses ─────────────────────────────────────────────
    optimized_geometry = [
        {
            "index": index,
            "element": quantum_molecule.atom_symbol(index),
            "x": round(float(coords[0]), 8),
            "y": round(float(coords[1]), 8),
            "z": round(float(coords[2]), 8),
        }
        for index, coords in enumerate(quantum_molecule.atom_coords(unit="Angstrom"))
    ]
    ensemble_analysis = (
        _conformer_ensemble(
            smiles,
            float(payload.get("temperature_k", 298.15)),
            count=max(8, min(24, numeric_threads * 2)),
        )
        if profile == "solvent_ensemble"
        else None
    )
    periodic_analysis = (
        _periodic_supercell_preview(optimized_geometry)
        if profile == "periodic"
        else None
    )

    profile_limitations: list[str] = []
    for analysis in (qmmm_analysis, ensemble_analysis, periodic_analysis):
        if analysis:
            profile_limitations.extend(analysis.get("limitations", []))

    _update_progress(self, 97, "finalizing", "Формирование результата")
    return {
        "status": "SUCCESS",
        "profile": profile,
        "engine": "PySCF",
        "engine_version": pyscf_version,
        "rdkit_version": rdkit_version,
        "method": method,
        "functional": functional if method == "DFT" else None,
        "basis": basis,
        "charge": quantum_molecule.charge,
        "spin": quantum_molecule.spin,
        "smiles": smiles,
        "scf_converged": bool(mean_field.converged),
        "electronic_energy_hartree": round(energy_hartree, 12),
        "nuclear_repulsion_hartree": round(float(quantum_molecule.energy_nuc()), 12),
        "homo_ev": round(homo_ev, 8),
        "lumo_ev": round(lumo_ev, 8),
        "gap_ev": round(lumo_ev - homo_ev, 8),
        "dipole_debye": [round(float(value), 8) for value in dipole],
        "mulliken_charges": [round(float(value), 8) for value in charges],
        "geometry_angstrom": optimized_geometry,
        "initial_conformer": {
            "method": f"ETKDGv3/{force_field}",
            "energy_kcal_mol": round(conformer_energy, 8),
        },
        "cube_artifacts": cube_artifacts,
        "vibrational_analysis": vibrational_analysis,
        "excited_state_analysis": excited_state_analysis,
        "mass_spectrum_analysis": None,
        "qmmm_analysis": qmmm_analysis,
        "ensemble_analysis": ensemble_analysis,
        "periodic_analysis": periodic_analysis,
        "elapsed_sec": round(time.time() - started, 4),
        "resources": {"numeric_threads": numeric_threads},
        "provenance": {
            "calculation_class": "ab_initio" if method == "HF" else "kohn_sham_dft",
            "geometry_optimized_at_quantum_level": bool(payload.get("optimize_geometry", False)),
            "limitations": [
                "The result describes one gas-phase conformer unless a solvent/ensemble workflow is used.",
                "Harmonic IR intensities are relative finite-difference dipole derivatives, not calibrated absolute intensities.",
                "The UV-Vis profile contains vertical singlet excitations unless a larger excited-state workflow is selected.",
                *profile_limitations,
            ],
        },
    }


@celery_app.task(name="tasks_dft.run_heavy_dft", queue="heavy_dft")
def run_heavy_dft(payload: dict) -> dict:
    """Placeholder heavy task.

    Replace this with ORCA/xTB/NWChem subprocess orchestration. The current code
    demonstrates process-level parallelism and produces a deterministic audit payload.
    """
    start = time.time()
    seeds = list(range(_parallel_job_count(payload)))
    with ProcessPoolExecutor(max_workers=min(len(seeds), os.cpu_count() or 1)) as pool:
        values = list(pool.map(_simulate_quantum_point, seeds))
    return {
        "status": "SUCCESS",
        "engine": "DFT_PLACEHOLDER",
        "molecule": payload.get("smiles"),
        "parallel_jobs": len(seeds),
        "surrogate_energy": round(float(np.mean(values)), 6),
        "elapsed_sec": round(time.time() - start, 4),
        "note": "Replace with validated quantum-chemical binary call.",
    }
