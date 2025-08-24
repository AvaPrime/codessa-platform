# Deployment

## Local (Docker Compose)
```bash
docker compose up -d
make api
make agents
```

## Kubernetes (Helm)
```bash
helm upgrade --install maf ./helm/maf -f helm/maf/values.yaml
```

### Secrets
- Use external secret store (AWS Secrets Manager / HashiCorp Vault).
- Only `.env.example` is committed; never commit real `.env`.
