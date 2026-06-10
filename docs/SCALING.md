# Scaling plan

## Local scaling

Run additional fast workers:

```bash
docker compose up --build --scale worker-ai=4
```

Run additional heavy workers only when the host has enough CPU/RAM:

```bash
docker compose up --build --scale worker-dft=2
```

## Runtime model

- API remains stateless and can be horizontally replicated behind an ingress/proxy.
- Fast tasks are idempotent payload transformations and can be distributed across `fast_tasks` workers.
- Heavy DFT tasks are isolated in `heavy_dft` to prevent long quantum jobs from blocking interactive predictions.
- Large vectors should be moved to MinIO/S3. PostgreSQL stores metadata and audit trail only.

## Production migration

1. Replace Compose with Kubernetes manifests or Helm chart.
2. Move `.env` secrets to Vault, AWS Secrets Manager, Doppler, SOPS or equivalent.
3. Add OpenTelemetry traces for pipeline-level observability.
4. Add model registry with artifact hashes for PLS/GNN/DFT parameters.
5. Add GPU node pool for future GNN inference.
