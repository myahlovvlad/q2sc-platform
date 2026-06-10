from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class ReferenceLookupError(ValueError):
    pass


async def _get_json(url: str) -> dict[str, Any]:
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Q2SC/0.2 research-client"})
    if response.status_code == 404:
        raise ReferenceLookupError("Reference record was not found")
    response.raise_for_status()
    return response.json()


async def lookup_pubchem(identifier: str) -> dict[str, Any]:
    properties = ",".join(
        [
            "Title",
            "CanonicalSMILES",
            "IsomericSMILES",
            "InChI",
            "InChIKey",
            "MolecularFormula",
            "MolecularWeight",
            "ExactMass",
            "XLogP",
            "TPSA",
        ]
    )
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{quote(identifier, safe='')}/property/{properties}/JSON"
    )
    payload = await _get_json(url)
    records = payload.get("PropertyTable", {}).get("Properties", [])
    if not records:
        raise ReferenceLookupError("PubChem returned no compound properties")
    record = records[0]
    return {
        "source": "PubChem",
        "source_id": str(record.get("CID", "")),
        "name": record.get("Title") or identifier,
        "canonical_smiles": record.get("ConnectivitySMILES") or record.get("CanonicalSMILES"),
        "isomeric_smiles": record.get("SMILES") or record.get("IsomericSMILES"),
        "inchi": record.get("InChI"),
        "inchi_key": record.get("InChIKey"),
        "formula": record.get("MolecularFormula"),
        "properties": {
            "molecular_weight": record.get("MolecularWeight"),
            "exact_mass": record.get("ExactMass"),
            "xlogp": record.get("XLogP"),
            "tpsa": record.get("TPSA"),
        },
        "provenance_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{record.get('CID', '')}",
        "raw": record,
    }


async def lookup_chembl(chembl_id: str) -> dict[str, Any]:
    normalized = chembl_id.upper()
    payload = await _get_json(f"https://www.ebi.ac.uk/chembl/api/data/molecule/{quote(normalized)}.json")
    structures = payload.get("molecule_structures") or {}
    properties = payload.get("molecule_properties") or {}
    return {
        "source": "ChEMBL",
        "source_id": payload.get("molecule_chembl_id", normalized),
        "name": payload.get("pref_name"),
        "canonical_smiles": structures.get("canonical_smiles"),
        "inchi": structures.get("standard_inchi"),
        "inchi_key": structures.get("standard_inchi_key"),
        "formula": properties.get("full_molformula"),
        "properties": properties,
        "provenance_url": f"https://www.ebi.ac.uk/chembl/explore/compound/{normalized}",
        "raw": payload,
    }


async def lookup_pdb(pdb_id: str) -> dict[str, Any]:
    normalized = pdb_id.upper()
    payload = await _get_json(f"https://data.rcsb.org/rest/v1/core/entry/{quote(normalized)}")
    info = payload.get("rcsb_entry_info") or {}
    citation = payload.get("rcsb_primary_citation") or {}
    return {
        "source": "RCSB PDB",
        "source_id": normalized,
        "name": (payload.get("struct") or {}).get("title"),
        "properties": {
            "experimental_method": (payload.get("exptl") or [{}])[0].get("method"),
            "resolution_combined": info.get("resolution_combined"),
            "molecular_weight": info.get("molecular_weight"),
            "polymer_entity_count": info.get("polymer_entity_count"),
            "nonpolymer_entity_count": info.get("nonpolymer_entity_count"),
            "citation_title": citation.get("title"),
        },
        "provenance_url": f"https://www.rcsb.org/structure/{normalized}",
        "raw": payload,
    }
