# Multi-Agent Factory — Helm Chart Skeleton

This repository contains a ready-to-use Helm chart for deploying the Multi-Agent Factory platform.

## Structure
- `charts/maf/Chart.yaml` – chart metadata
- `charts/maf/values*.yaml` – base and environment-specific values
- `charts/maf/templates/` – rendered manifests (Deployments, Services, ConfigMaps, etc.)
- `apps/maf.yaml` – optional Argo CD application definition

## Quickstart
```bash
# install in namespace maf
kubectl create ns maf || true
helm upgrade -i maf charts/maf -n maf -f charts/maf/values.yaml -f charts/maf/values-saas.yaml
```

## Notes
- Prometheus/Grafana/Loki are assumed to be managed outside this chart; ServiceMonitor and PrometheusRule are provided for integration.
- Secrets are sourced from Vault via External Secrets; update `values.yaml` → `api.externalSecrets.data` accordingly.
- For on‑prem/air‑gapped, enable `vllm.enabled=true` and empty the egress allowlist.
