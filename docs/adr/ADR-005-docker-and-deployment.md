# ADR-005: Containers, artefacts baked into the image, configuration by environment

- **Status:** Accepted
## Decision
- Two images: `api` (python:3.12-slim, non-root user, health check, pinned requirements) and `web` (nginx-alpine). `docker-compose.yml` wires them; `web` waits for `api` to be healthy.
- Model artefact + metadata are copied into the API image at build time: an image tag therefore identifies code **and** model together, rollback = redeploy the previous tag.
- All runtime knobs are `EMRALERT_*` env vars (12-factor). No secrets are needed in this demo; real deployments inject them from the platform secret store.
- Graceful degradation: if the model or data cannot load, the API still starts, `/health` reports `degraded`, and prediction endpoints return `503 model_unavailable` with a request id (tested).
## Consequences
Reproducible, immutable releases; larger images on every model change (acceptable at 200 KB). For production, move artefacts to a registry and load at start-up by version pin.
