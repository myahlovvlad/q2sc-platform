from __future__ import annotations

from dataclasses import dataclass
from html import escape

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Descriptors3D, Lipinski, rdMolDescriptors

from app.schemas import (
    MoleculeAtom,
    MoleculeBond,
    MoleculePreparationRequest,
    MoleculePreparationResponse,
)


@dataclass(frozen=True)
class ConformerSelection:
    conformer_id: int
    energy_kcal_mol: float
    force_field: str


def _select_conformer(molecule: Chem.Mol, conformer_ids: list[int]) -> ConformerSelection:
    mmff_properties = AllChem.MMFFGetMoleculeProperties(molecule, mmffVariant="MMFF94")
    if mmff_properties is not None:
        results = AllChem.MMFFOptimizeMoleculeConfs(
            molecule,
            numThreads=0,
            maxIters=500,
            mmffVariant="MMFF94",
        )
        energies = [float(energy) for _status, energy in results]
        force_field = "MMFF94"
    else:
        results = AllChem.UFFOptimizeMoleculeConfs(molecule, numThreads=0, maxIters=500)
        energies = [float(energy) for _status, energy in results]
        force_field = "UFF"

    if not energies:
        raise ValueError("No conformer could be optimized")
    best_position = min(range(len(energies)), key=energies.__getitem__)
    return ConformerSelection(
        conformer_id=conformer_ids[best_position],
        energy_kcal_mol=energies[best_position],
        force_field=force_field,
    )


def _draw_svg(molecule: Chem.Mol) -> str:
    drawing_molecule = Chem.RemoveHs(Chem.Mol(molecule))
    AllChem.Compute2DCoords(drawing_molecule)
    conformer = drawing_molecule.GetConformer()
    points = [conformer.GetAtomPosition(index) for index in range(drawing_molecule.GetNumAtoms())]
    min_x = min(point.x for point in points)
    max_x = max(point.x for point in points)
    min_y = min(point.y for point in points)
    max_y = max(point.y for point in points)
    width, height, padding = 640.0, 420.0, 44.0
    scale = min(
        (width - 2 * padding) / max(max_x - min_x, 1.0),
        (height - 2 * padding) / max(max_y - min_y, 1.0),
    )

    def project(index: int) -> tuple[float, float]:
        point = points[index]
        return (
            padding + (point.x - min_x) * scale,
            height - padding - (point.y - min_y) * scale,
        )

    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 420" role="img">',
        '<rect width="640" height="420" fill="white"/>',
    ]
    for bond in drawing_molecule.GetBonds():
        x1, y1 = project(bond.GetBeginAtomIdx())
        x2, y2 = project(bond.GetEndAtomIdx())
        stroke_width = 3.0 if bond.GetBondTypeAsDouble() >= 2 else 2.0
        elements.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#334155" stroke-width="{stroke_width:.1f}" stroke-linecap="round"/>'
        )
    atom_colors = {
        "C": "#1e293b",
        "N": "#2563eb",
        "O": "#dc2626",
        "S": "#ca8a04",
        "P": "#ea580c",
        "F": "#16a34a",
        "Cl": "#16a34a",
        "Br": "#92400e",
        "I": "#7e22ce",
    }
    for atom in drawing_molecule.GetAtoms():
        x, y = project(atom.GetIdx())
        symbol = escape(atom.GetSymbol())
        color = atom_colors.get(symbol, "#475569")
        elements.extend(
            [
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="15" fill="white" stroke="{color}" stroke-width="2"/>',
                f'<text x="{x:.2f}" y="{y + 4:.2f}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="13" font-weight="700" fill="{color}">{symbol}</text>',
                f'<text x="{x + 17:.2f}" y="{y - 12:.2f}" font-family="sans-serif" '
                f'font-size="10" fill="#64748b">{atom.GetIdx()}</text>',
            ]
        )
    elements.append("</svg>")
    return "".join(elements)


def prepare_molecule(request: MoleculePreparationRequest) -> MoleculePreparationResponse:
    base = Chem.MolFromSmiles(request.smiles)
    if base is None:
        raise ValueError("RDKit could not parse the supplied SMILES")
    if base.GetNumAtoms() > request.max_heavy_atoms:
        raise ValueError(
            f"Molecule contains {base.GetNumAtoms()} heavy atoms; limit is {request.max_heavy_atoms}"
        )

    canonical_smiles = Chem.MolToSmiles(base, canonical=True, isomericSmiles=True)
    molecule = Chem.AddHs(base)
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = request.random_seed
    parameters.pruneRmsThresh = 0.25
    parameters.useSmallRingTorsions = True
    conformer_ids = list(
        AllChem.EmbedMultipleConfs(
            molecule,
            numConfs=request.num_conformers,
            params=parameters,
        )
    )
    if not conformer_ids:
        raise ValueError("RDKit ETKDG failed to generate a 3D conformer")

    selected = _select_conformer(molecule, conformer_ids)
    conformer = molecule.GetConformer(selected.conformer_id)
    atoms = [
        MoleculeAtom(
            index=atom.GetIdx(),
            element=atom.GetSymbol(),
            atomic_number=atom.GetAtomicNum(),
            formal_charge=atom.GetFormalCharge(),
            x=round(conformer.GetAtomPosition(atom.GetIdx()).x, 6),
            y=round(conformer.GetAtomPosition(atom.GetIdx()).y, 6),
            z=round(conformer.GetAtomPosition(atom.GetIdx()).z, 6),
        )
        for atom in molecule.GetAtoms()
    ]
    bonds = [
        MoleculeBond(
            index=bond.GetIdx(),
            atom_a=bond.GetBeginAtomIdx(),
            atom_b=bond.GetEndAtomIdx(),
            order=float(bond.GetBondTypeAsDouble()),
            aromatic=bond.GetIsAromatic(),
        )
        for bond in molecule.GetBonds()
    ]

    descriptors = {
        "molecular_weight": Descriptors.MolWt(base),
        "exact_mass": Descriptors.ExactMolWt(base),
        "logp": Descriptors.MolLogP(base),
        "tpsa": rdMolDescriptors.CalcTPSA(base, includeSandP=True),
        "h_bond_donors": float(Lipinski.NumHDonors(base)),
        "h_bond_acceptors": float(Lipinski.NumHAcceptors(base)),
        "rotatable_bonds": float(Lipinski.NumRotatableBonds(base)),
        "ring_count": float(Lipinski.RingCount(base)),
        "fraction_csp3": rdMolDescriptors.CalcFractionCSP3(base),
        "radius_of_gyration": Descriptors3D.RadiusOfGyration(molecule, confId=selected.conformer_id),
        "asphericity": Descriptors3D.Asphericity(molecule, confId=selected.conformer_id),
    }
    mol_block = Chem.MolToMolBlock(molecule, confId=selected.conformer_id)

    return MoleculePreparationResponse(
        name=request.name,
        input_smiles=request.smiles,
        canonical_smiles=canonical_smiles,
        inchi=Chem.MolToInchi(base),
        inchi_key=Chem.MolToInchiKey(base),
        formula=rdMolDescriptors.CalcMolFormula(base),
        atoms=atoms,
        bonds=bonds,
        mol_block=mol_block,
        svg_2d=_draw_svg(molecule),
        descriptors={key: round(float(value), 6) for key, value in descriptors.items()},
        conformer_energy_kcal_mol=round(selected.energy_kcal_mol, 6),
        preparation_method=f"ETKDGv3/{selected.force_field}",
    )
