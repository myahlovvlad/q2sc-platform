# User ways

## Scenario 1. Design / Direct prediction

User goal: predict a spectrum for a molecule before or after synthesis.

1. Select Design mode.
2. Enter molecule name and SMILES.
3. Configure solvent, model, temperature and instrument frequency.
4. Run prediction.
5. Review AD status. If outside domain, the molecule is parked for heavy DFT.
6. Review predicted peaks, spectrum curve and VIP drivers.
7. Export audit trail or send result to MCP-enabled assistant.

Parameter combinations:

- Solvent model: NONE, PCM, COSMO, explicit, QM/MM explicit.
- Compute mode: fast surrogate, parallel batch, heavy DFT.
- Spectroscopy type: 13C NMR, 1H NMR, FTIR, UV-Vis, Raman.
- Environment: solvent, dielectric constant, refractive index, temperature, pH.

## Scenario 2. Analytics / Reverse interpretation

User goal: identify or explain an unknown/experimental spectrum.

1. Select Analytics mode.
2. Upload or paste spectral data.
3. Configure known experiment conditions.
4. Optionally add constraints: formula, mass range, allowed atoms, candidate library.
5. Run reverse analysis.
6. Review detected peaks and ranked candidates.
7. Confirm, reject, or park unresolved candidates for DFT.

Decision logic:

- Match: candidate spectrum sufficiently close to processed signal.
- Weak: candidate requires additional evidence.
- Parked: candidate or spectrum is outside current applicability domain.
