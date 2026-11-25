# ADR-006: Versioned REST contract with a uniform error envelope

- **Status:** Accepted
## Decision
- Routes are under `/api/v1`; breaking changes require `/api/v2` and a deprecation window. OpenAPI is generated from Pydantic models (`/docs`).
- Inputs are validated at the edge (types, ranges, enums); category strings are trimmed and upper-cased; categories unseen in training are accepted and reported in `unseen_categories` (scored as "other") instead of failing the clinician workflow.
- Every error uses `{"error": {"code","message","request_id","details"}}`; every response carries `x-request-id` for log correlation.
- `/predict` returns probability, tier, eligibility, alert flag, threshold, drivers and model version, so every alert is explainable and attributable to a model version.
## Consequences
Client code (UI, EMR connector) can handle all failures generically. Request ids connect UI errors to server logs.
