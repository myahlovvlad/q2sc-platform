# Method and functionality gap analysis

This matrix is derived from the converted Cramer, Jensen, and reaction-rate
texts in `docs/books/`, the two supplied product notes, and the current code.

| Domain | Current executable capability | Scientific level | Required production extension |
|---|---|---|---|
| Molecular structure | RDKit parsing, descriptors, ETKDGv3 conformers, MMFF/UFF minimization | Cheminformatics / molecular mechanics | Protonation, tautomer, stereoisomer and conformer-state management |
| Ground-state quantum chemistry | PySCF HF and Kohn-Sham DFT, optional geometry optimization | Ab initio / DFT | Basis and functional presets, convergence recovery, correlated post-HF methods |
| IR | Hessian, harmonic modes, finite-difference dipole derivatives, line broadening | Harmonic single-conformer model | Validated km/mol conversion, scaling factors, VPT2/anharmonicity, Raman polarizability |
| UV-Vis | TDHF/TDDFT vertical singlet states, oscillator strengths | Vertical excitation model | State character, excited-state optimization, triplets, SOC, fluorescence and rates |
| Jablonski diagram | Diagram from computed singlet vertical transitions | Evidence-backed partial diagram | Relaxed states, non-radiative channels, intersystem crossing and kinetic constants |
| Mass spectra | Deterministic single-bond cleavage screen and exact fragment masses | Fast fragmentation hypothesis generator | QCxMS/QCEIMS trajectories, ionization and collision conditions, rearrangements, MassBank validation |
| QM/MM | PySCF electronic state embedded in deterministic external point charges | Electrostatic embedding demonstration | MM topology/force field, link atoms, polarizable embedding, PDB region selection and MD snapshots |
| Solvent ensemble | ETKDG/MMFF conformer ensemble and Boltzmann populations | Molecular-mechanics conformer model | Explicit solvent boxes, MD sampling, cluster extraction, quantum free energies and spectrum averaging |
| Periodic systems | Lattice/supercell preparation and visualization | Geometry preparation | Crystal input, PySCF-PBC/plane-wave engine, k-points, pseudopotentials, bands and phonons |
| Potential energy surfaces | Single-state optimization and Hessian | Local stationary-point analysis | Coordinate scans, TS search, IRC/NEB, free-energy corrections and reaction networks |
| Thermochemistry and kinetics | Not yet exposed as a product workflow | — | Partition functions, hindered rotors, TST/VTST, tunnelling and solvent-dependent rates |
| Intermolecular interactions | External charges and future complex state model | Partial | Counterpoise correction, SAPT/EDA, binding ensembles and many-body effects |
| Spectral data processing | AsLS, SNV, peak detection, PLS, VIP, T² and Q residuals | Chemometric pipeline | EMSC, instrument-response models, uncertainty calibration and external validation |
| Interpretation | Deterministic profile-aware findings, evidence and limitations | Rule/evidence layer | Atom-to-peak assignments, method-selection rules, reference-spectrum comparison and calibrated confidence |
| Reporting | Server-generated PDF summary | Reproducible report scaffold | Embedded plots, signed provenance, raw artifacts, references and validation certificate |

## Method-selection concept

The product should choose a workflow from the requested property, system size,
environment, required uncertainty, and available resources:

1. Use RDKit/MM or a validated ML surrogate for rapid screening.
2. Escalate out-of-domain structures to semiempirical or DFT calculations.
3. Sample conformers before reporting solution-phase spectra.
4. Use TD methods for electronic spectra and Hessian/response properties for
   vibrational spectra.
5. Use dynamics/statistical fragmentation for mass spectra rather than
   deriving them from vibrational modes.
6. Require a crystal or periodic cell before claiming a periodic electronic
   calculation.
7. Preserve the method, parameters, environment, artifacts, warnings, and
   comparison reference in every report.

## Framework adapters

The architecture should keep engine adapters independent:

- RDKit for structure and conformer preparation.
- xTB/CREST or DFTB+ for high-throughput prescreening.
- PySCF, Psi4, NWChem, or ORCA adapters for molecular quantum chemistry.
- QCxMS/QCEIMS for trajectory-based mass spectra.
- OpenMM plus a quantum adapter for production QM/MM and explicit solvent.
- PySCF-PBC, CP2K, Quantum ESPRESSO, or GPAW for periodic calculations.
- ASE as the common atoms/calculator and workflow boundary.
- PostgreSQL for normalized metadata and MinIO for trajectories, cubes,
  Hessians, spectra, logs, and generated reports.

The newly executable approximation profiles are intentionally labelled with
their method level. They validate orchestration and visualization but are not
substitutes for the production engines listed above.
