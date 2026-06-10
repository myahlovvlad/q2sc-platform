# Review of `Potential surface molecule`

The notebook is useful as a requirements sketch and visualization prototype,
but its numerical results must not be used as quantum-chemical evidence.

## Useful ideas retained

- SMILES-to-conformer preparation;
- explicit distinction between molecular geometry, PES, stationary points,
  descriptors, solvent, temperature, and pressure;
- ASE-style optimizer and NEB workflow boundaries;
- 3D PES visualization and saddle-point artifact format;
- intent to compare HF, DFT, molecular mechanics, and reference values.

## Scientific and implementation defects

1. RDKit atoms are converted with `Atoms('C' * mol.GetNumAtoms())`, replacing
   oxygen and hydrogen with carbon. Energies no longer describe the input
   molecule.
2. ASE EMT is a metal-oriented effective-medium potential and is not a
   chemically valid force field for aspirin.
3. The SMILES labeled as aspirin is not the standard aspirin connectivity used
   elsewhere in the project.
4. The NEB endpoint is created by random coordinate noise rather than a known
   reactant/product transformation. It therefore has no defined reaction path.
5. The PES moves one atom over Cartesian X/Y while mutating a shared object
   across parallel jobs. This is both physically arbitrary and race-prone.
6. Saddle points are selected by an arbitrary energy interval instead of a
   first-order stationary-point Hessian test with exactly one imaginary mode.
7. Handwritten force-field components mix units and parameters, producing
   energies around `179065 eV`; comparison to an arbitrary `250 eV` reference
   has no validation meaning.
8. The `dftb_in.hsd` file only references `geo_end.gen`; it lacks Hamiltonian,
   Slater-Koster parameter, SCC, optimizer, and output configuration.
9. PySCF/PSI4 installation cells fail on the original Windows/Python setup and
   the notebook does not produce a reproducible quantum result.

## Replacement workflow

1. Normalize chemical identity and molecular state.
2. Generate a conformer ensemble with RDKit/CREST.
3. Prescreen with a suitable molecular or semiempirical method.
4. Optimize selected conformers at a recorded quantum level.
5. Verify minima or transition states using a Hessian.
6. Define reaction coordinates from chemistry, then run NEB/string/IRC.
7. Store every geometry, energy, gradient, Hessian, and engine log.
8. Build PES visualizations from immutable calculation points.

The first four infrastructure steps are now represented in Q2SC by RDKit
preparation and the PySCF heavy-worker profile. Reaction-path and DFTB+/xTB
adapters remain separate planned engine profiles.
