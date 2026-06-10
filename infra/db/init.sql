CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS q2sc_core;

CREATE TABLE IF NOT EXISTS q2sc_core.projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS q2sc_core.molecules (
    molecule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES q2sc_core.projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    smiles TEXT NOT NULL,
    inchi TEXT,
    pubchem_id INT,
    molecular_weight NUMERIC(12, 6),
    logp NUMERIC(10, 6),
    tpsa NUMERIC(12, 6),
    num_atoms INT,
    mean_charge NUMERIC(12, 8),
    structure_hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_molecules_project ON q2sc_core.molecules(project_id);
CREATE INDEX IF NOT EXISTS idx_molecules_smiles_hash ON q2sc_core.molecules USING hash(smiles);

CREATE TABLE IF NOT EXISTS q2sc_core.spectral_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    molecule_id UUID REFERENCES q2sc_core.molecules(molecule_id) ON DELETE CASCADE,
    pipeline_id UUID NOT NULL,
    spectroscopy_type VARCHAR(50) NOT NULL,
    solvent_name VARCHAR(100) NOT NULL,
    solvent_model VARCHAR(50) NOT NULL,
    instrument_frequency_mhz NUMERIC(8, 2),
    t2_hotelling NUMERIC(14, 6) NOT NULL,
    q_residual NUMERIC(14, 6),
    is_inside_ad BOOLEAN NOT NULL,
    s3_spectrum_vector_path TEXT,
    predicted_peaks JSONB,
    vip_scores JSONB,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS q2sc_core.audit_trails (
    log_id BIGSERIAL PRIMARY KEY,
    pipeline_id UUID NOT NULL,
    project_id UUID REFERENCES q2sc_core.projects(project_id) ON DELETE SET NULL,
    step_name VARCHAR(100) NOT NULL,
    operator_metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_pipeline ON q2sc_core.audit_trails(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_predictions_molecule ON q2sc_core.spectral_predictions(molecule_id);

CREATE TABLE IF NOT EXISTS q2sc_core.parking_orbit (
    parking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES q2sc_core.projects(project_id) ON DELETE SET NULL,
    payload JSONB NOT NULL,
    reason TEXT NOT NULL,
    recommended_action VARCHAR(100) DEFAULT 'heavy_dft',
    status VARCHAR(50) DEFAULT 'PARKED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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
);

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
);

CREATE INDEX IF NOT EXISTS idx_reference_compounds_inchi_key
ON q2sc_core.reference_compounds(inchi_key);

CREATE INDEX IF NOT EXISTS idx_reference_spectra_type
ON q2sc_core.reference_spectra(spectrum_type);
