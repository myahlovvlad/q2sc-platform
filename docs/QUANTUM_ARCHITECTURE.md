# Quantum calculation architecture

## Calculation tiers

| Tier | Purpose | Engines | Typical output |
|---|---|---|---|
| Reference | Experimental and curated evidence | PubChem, ChEMBL, RCSB PDB, MassBank | identity, properties, structures, spectra |
| Cheminformatics | Fast structure preparation | RDKit | 2D depiction, conformers, descriptors |
| Semiempirical | Conformer/PES prescreening | xTB, CREST, DFTB+ | optimized ensembles, frequencies, rough energies |
| Quantum | Ground-state electronic structure | PySCF, Psi4, ORCA adapter | energy, density, orbitals, charges, response properties |
| Excited state | Electronic spectroscopy | TDDFT, ADC, EOM-CC adapters | excitation energies, oscillator strengths, state characters |
| Dynamics | Fragmentation and reactions | QCxMS/QCEIMS, MD, NEB/IRC | fragments, pathways, rate information |
| Environment | Intermolecular and condensed phase | continuum, clusters, QM/MM, periodic models | solvent shifts, binding/interactions, ensemble averages |

## First implemented profile

`SMILES -> RDKit ETKDGv3 conformers -> MMFF94/UFF prescreen ->
PySCF HF or Kohn-Sham DFT -> energy, HOMO/LUMO, dipole, Mulliken charges,
electron-density/HOMO/LUMO cube artifacts`.

HF is an ab initio wave-function method. Kohn-Sham DFT is recorded separately
as DFT and is not mislabeled as HF or post-HF. The first profile is a
single-conformer gas-phase calculation unless quantum geometry optimization is
explicitly requested.

## Spectroscopy profiles to add

### IR and Raman

1. Optimize every populated conformer.
2. Verify the stationary point using a Hessian.
3. Compute harmonic frequencies and normal modes.
4. Obtain dipole derivatives for IR and polarizability derivatives for Raman.
5. Apply documented scaling, line broadening, temperature, and conformer
   Boltzmann weights.
6. Add anharmonic/VPT2 or hindered-rotor treatment where justified.

### UV-Vis and Jablonski model

1. Run ground-state optimization and an excited-state method such as TDDFT.
2. Store excitation energy, oscillator strength, multiplicity, and dominant
   orbital/configuration contributions.
3. Optimize selected excited states for fluorescence estimates.
4. Add spin-orbit and nonradiative-rate models before presenting intersystem
   crossing or phosphorescence.
5. Build the Jablonski diagram from computed states and transitions.

### Mass spectrometry

Mass spectra are not obtained from normal modes alone. The production workflow
must combine ionization state preparation, bond-breaking energetics, molecular
dynamics or statistical fragmentation, instrument/ionization conditions, and
comparison to MassBank records. QCxMS/QCEIMS is the preferred adapter class.

### Intermolecular effects

The state model must support complexes and ensembles, not only isolated
molecules. Planned profiles include counterpoise-corrected dimers, SAPT energy
decomposition, explicit solvent clusters, periodic boxes, and QM/MM regions for
PDB structures.

## Data and execution

- PostgreSQL stores identities, molecular states, job metadata, methods, and
  normalized reference records.
- MinIO stores SDF/PDB inputs, logs, cube files, trajectories, Hessians, and
  spectra.
- Redis/Celery routes short cheminformatics work separately from quantum,
  excited-state, dynamics, and QM/MM queues.
- Every worker runs in an engine-specific immutable image.
- Resource limits include atom count, basis-function estimate, memory, CPU,
  wall time, and artifact size.

## Scientific validation

Validation is property- and method-specific. It includes geometry RMSD,
frequency errors, spectral peak matching, excitation-energy error, conformer
population sensitivity, basis/method convergence, solvent-model sensitivity,
and comparison with curated experimental conditions. A generic application
domain score is insufficient for quantum results.

See `METHOD_GAP_ANALYSIS.md` for the implementation matrix, method-selection
rules, approximation boundaries, and recommended engine adapters.
