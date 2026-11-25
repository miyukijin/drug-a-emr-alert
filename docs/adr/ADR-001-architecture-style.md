# ADR-001: Modular monolith API + separate static UI container

- **Status:** Accepted  - **Date:** 2026-11
- **Decision makers:** Head of AI (owner), tech leads

## Context
We must ship a working full-stack solution quickly (UI, REST API, model inference, Docker), and be able to scale it to many markets later. The model is small (200 KB), inference is ~1 ms/row, and there is one bounded domain (score a Disease X patient, decide an alert).

## Options
1. **Microservices** (separate model-serving, patient, alert-policy, auth services).
2. **Modular monolith** API (one deployable, clear internal module boundaries) + static UI served by nginx.
3. Single process serving both UI and API.

## Decision
Option 2. One FastAPI deployable with strict layering (`api/` routers -> `services/` -> `core/`), a separate nginx container for the UI that reverse-proxies `/api`.

## Rationale
- One team, one domain, tiny model: network hops between services would add latency, failure modes and operational cost with no scaling benefit.
- Module boundaries (`ModelService` is the *only* module importing scikit-learn; `decision.py` is pure functions; `PatientRepo` is the only data-access code) make later extraction cheap.
- Separating UI from API keeps the API consumable by the EMR vendor directly (the real production client is an EMR, not our UI).
- Stateless API -> horizontal scaling behind a load balancer needs no redesign.

## Consequences
- (+) Fastest path to a reliable demo and a simple on-call story. (-) A single deploy unit: a bad API release affects all endpoints.
- **Revisit triggers:** a second model/use case with a different release cadence; independent scaling needs for batch scoring; separate team ownership of the alert-policy engine. Then extract `ModelService` into a model-serving service first.
