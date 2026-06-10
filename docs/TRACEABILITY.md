# Traceability and interpretability

The platform returns an `audit_trail` array for direct and reverse workflows. Each record includes:

- `pipeline_id`
- `project_id`
- `step_name`
- `timestamp_unix`
- `metadata`

Interpretability is provided by:

- Applicability domain: T² Hotelling and Q-residual.
- VIP scores from the PLS model.
- Explicit signal formation: predicted shifts are expanded into Lorentzian peaks and normalized with SNV.
- Parking orbit: out-of-domain structures are blocked from confident reporting and marked for heavy calculation.

Production hardening should persist audit entries in PostgreSQL and sign model artifacts with version hashes.
