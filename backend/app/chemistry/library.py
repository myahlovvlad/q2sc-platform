from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings


_engine: AsyncEngine | None = None


def _database_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


async def ensure_reference_schema() -> None:
    statements = [
        "CREATE SCHEMA IF NOT EXISTS q2sc_core",
        """
        CREATE TABLE IF NOT EXISTS q2sc_core.reference_compounds (
            reference_compound_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(64) NOT NULL,
            source_id VARCHAR(255) NOT NULL,
            name TEXT,
            canonical_smiles TEXT,
            inchi TEXT,
            inchi_key VARCHAR(64),
            formula VARCHAR(255),
            properties JSONB NOT NULL DEFAULT '{}'::jsonb,
            provenance_url TEXT,
            raw_record JSONB NOT NULL DEFAULT '{}'::jsonb,
            imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, source_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS q2sc_core.reference_spectra (
            reference_spectrum_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            reference_compound_id UUID REFERENCES q2sc_core.reference_compounds(reference_compound_id)
                ON DELETE CASCADE,
            spectrum_type VARCHAR(32) NOT NULL,
            source VARCHAR(64) NOT NULL,
            source_id VARCHAR(255) NOT NULL,
            conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
            x_unit VARCHAR(32),
            y_unit VARCHAR(32),
            x_axis JSONB NOT NULL DEFAULT '[]'::jsonb,
            y_axis JSONB NOT NULL DEFAULT '[]'::jsonb,
            provenance_url TEXT,
            raw_record JSONB NOT NULL DEFAULT '{}'::jsonb,
            imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, source_id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_reference_compounds_inchi_key
        ON q2sc_core.reference_compounds(inchi_key)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_reference_spectra_type
        ON q2sc_core.reference_spectra(spectrum_type)
        """,
    ]
    async with _database_engine().begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))


async def upsert_reference_compound(record: dict[str, Any]) -> dict[str, Any]:
    await ensure_reference_schema()
    statement = text(
        """
        INSERT INTO q2sc_core.reference_compounds (
            source, source_id, name, canonical_smiles, inchi, inchi_key, formula,
            properties, provenance_url, raw_record
        ) VALUES (
            :source, :source_id, :name, :canonical_smiles, :inchi, :inchi_key, :formula,
            CAST(:properties AS JSONB), :provenance_url, CAST(:raw_record AS JSONB)
        )
        ON CONFLICT (source, source_id) DO UPDATE SET
            name = EXCLUDED.name,
            canonical_smiles = EXCLUDED.canonical_smiles,
            inchi = EXCLUDED.inchi,
            inchi_key = EXCLUDED.inchi_key,
            formula = EXCLUDED.formula,
            properties = EXCLUDED.properties,
            provenance_url = EXCLUDED.provenance_url,
            raw_record = EXCLUDED.raw_record,
            imported_at = CURRENT_TIMESTAMP
        RETURNING
            reference_compound_id, source, source_id, name, canonical_smiles,
            inchi_key, formula, properties, provenance_url, imported_at
        """
    )
    parameters = {
        "source": record.get("source"),
        "source_id": str(record.get("source_id") or ""),
        "name": record.get("name"),
        "canonical_smiles": record.get("canonical_smiles"),
        "inchi": record.get("inchi"),
        "inchi_key": record.get("inchi_key"),
        "formula": record.get("formula"),
        "properties": json.dumps(record.get("properties") or {}),
        "provenance_url": record.get("provenance_url"),
        "raw_record": json.dumps(record.get("raw") or {}),
    }
    async with _database_engine().begin() as connection:
        result = await connection.execute(statement, parameters)
        row = result.mappings().one()
    return {key: value.isoformat() if hasattr(value, "isoformat") else str(value) if key == "reference_compound_id" else value for key, value in row.items()}


async def search_reference_compounds(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    await ensure_reference_schema()
    statement = text(
        """
        SELECT
            reference_compound_id, source, source_id, name, canonical_smiles,
            inchi_key, formula, properties, provenance_url, imported_at
        FROM q2sc_core.reference_compounds
        WHERE (
            :query = ''
            OR name ILIKE :pattern
            OR formula ILIKE :pattern
            OR inchi_key ILIKE :pattern
            OR canonical_smiles ILIKE :pattern
        )
        ORDER BY imported_at DESC
        LIMIT :limit
        """
    )
    async with _database_engine().connect() as connection:
        result = await connection.execute(
            statement,
            {"query": query, "pattern": f"%{query}%", "limit": limit},
        )
        rows = result.mappings().all()
    return [
        {
            key: value.isoformat()
            if hasattr(value, "isoformat")
            else str(value)
            if key == "reference_compound_id"
            else value
            for key, value in row.items()
        }
        for row in rows
    ]
