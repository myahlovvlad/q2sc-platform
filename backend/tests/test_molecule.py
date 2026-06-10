import pytest

from app.chemistry.molecule import prepare_molecule
from app.schemas import MoleculePreparationRequest


def test_prepare_molecule_builds_chemical_3d_structure():
    result = prepare_molecule(
        MoleculePreparationRequest(name="Ethanol", smiles="CCO", num_conformers=3)
    )

    assert result.formula == "C2H6O"
    assert result.canonical_smiles == "CCO"
    assert len(result.atoms) == 9
    assert {atom.element for atom in result.atoms} == {"C", "H", "O"}
    assert result.mol_block
    assert "<svg" in result.svg_2d
    assert result.preparation_method.startswith("ETKDGv3/")


def test_prepare_molecule_rejects_invalid_smiles():
    with pytest.raises(ValueError, match="could not parse"):
        prepare_molecule(MoleculePreparationRequest(name="Invalid", smiles="not-a-smiles"))
