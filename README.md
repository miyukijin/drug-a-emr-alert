# Drug A EMR Alert - full-stack ML solution

An EMR decision-support alert for Disease X: it flags patients who are **eligible for Drug A but unlikely to receive it**, so the prescriber (or a care coordinator) can review them. Includes the data pipeline, model, REST API, web UI, Docker packaging, tests and design records.

| What | Where |
|---|---|
| Web UI (worklist, lookup, scorer) | http://localhost:8080 |
| REST API + interactive docs | http://localhost:8000/docs |
| Model dataset (`model_table`) | `data/model_table.csv` |
| Model report (Steps 1-3) | `docs/model_report.md` |
| Architecture, ADRs, versioning | `docs/architecture.md`, `docs/adr/`, `docs/versioning.md` |
| AI-assistant disclosure | `docs/ai_usage.md` |

## Run it (Docker - recommended)
```bash
docker compose up --build        # or: make up
# UI  -> http://localhost:8080     API docs -> http://localhost:8000/docs
curl -s http://localhost:8080/health
curl -s -X POST http://localhost:8080/api/v1/predict -H 'content-type: application/json' -d '{
  "patient_age": 71, "patient_gender": "F", "num_conditions": 2,
  "physician_type": "FAMILY MEDICINE", "physician_state": "CA", "location_type": "TELEHEALTH"}'
docker compose down
```
The `web` container serves the UI and proxies `/api/*` to the `api` container, so the browser only talks to port 8080. Verified: both containers become healthy, the UI loads the worklist, and predictions return through the proxy.

## Run it without Docker
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt -r ml/requirements.txt
cd backend && uvicorn app.main:app --port 8000          # API
cd ../frontend && python -m http.server 8080             # UI; open http://localhost:8080/?api=http://localhost:8000
```

## API (see `/docs` for the full OpenAPI)
| Method / path | Purpose |
|---|---|
| `POST /api/v1/predict` | JSON features -> `likelihood_treated`, tier, eligibility, alert flag, top drivers, model version |
| `POST /api/v1/predict/batch` | up to 1,000 patients (no drivers) |
| `GET /api/v1/patients?alerts_only=&tier=&min_age=&q=&sort=&page=` | worklist |
| `GET /api/v1/patients/{id}` | patient context + prediction |
| `GET /api/v1/model`, `GET /health` | model card data, readiness |

Errors always look like `{"error": {"code", "message", "request_id", "details"}}`. Config via env vars: `EMRALERT_ALERT_THRESHOLD` (default 0.15 from model metadata), `EMRALERT_MIN_ELIGIBLE_AGE` (13), `EMRALERT_LOG_LEVEL`.

## Reproduce the data and model
```bash
# put the exercise workbook in data/raw/ (not committed)
python ml/data_prep.py data/raw/LT_Interview_Exercise_Head_of_AI.xlsx data   # cleaning log + model_table.csv
python ml/train.py data/model_table.csv models reports                      # CV comparison, hold-out metrics, figures, model artefact
```

## Tests
```bash
make test      # 20 API/unit tests (backend/tests) + 6 pipeline/contract tests (ml/tests)
```
CI (`.github/workflows/ci.yml`) runs the tests, builds both images and smoke-tests `/health` and `/predict` through the proxy.

## Results at a glance (20% hold-out, n=804)
ROC-AUC 0.77 (all) / 0.72 (eligible); PR-AUC 0.34 / 0.36 (prevalence 16% / 21%). At the 15% alert threshold, 34% of eligible patients are alerted and 94% of those were untreated. Moderate discrimination: a prioritisation aid, not a verdict. Limitations (single-quarter sample, behaviour not appropriateness, US-style data) are in `docs/model_report.md`.

## Design in brief
- **Modular monolith + static UI** (ADR-001): one deployable API with enforced layering; model access isolated in `ModelService`; pure-function alert policy; read-only patient store.
- **Point-in-time features** (ADR-003): no post-diagnosis information is used, so offline metrics reflect alert-time performance.
- **Parsimonious model chosen by 1-SE rule** (ADR-002); engineered extras are kept in the dataset but did not beat noise.
- **Explainability** per patient via occlusion drivers; transparency page in the UI.
- **Failure handling:** typed errors, degraded start-up, request ids, UI error states.

## Layout
```
backend/   FastAPI app (api/ services/ core/), tests, Dockerfile
frontend/  static SPA (js modules, css), nginx.conf, Dockerfile
ml/        data_prep.py, train.py, features.py, tests
data/      model_table.csv, data_quality_log.json  (raw/ is git-ignored)
models/    model.joblib, model_metadata.json
reports/   metrics, CV table, lift/subgroup tables, figures
docs/      architecture, ADRs, versioning, model report, screenshots
```

## Hand-off and extension
- **Owners:** ML lead owns `ml/` + model promotion; platform lead owns `backend/` + deployment; product owns `frontend/` + alert policy (`decision.py`, ADR-004).
- **First 30 days for a new engineer:** run `make up`, read ADRs 001-006, run `make test`, retrain with `make train` and diff `reports/metrics.json`.
- **Extend:** new feature -> add to `ml/data_prep.py` + `ml/features.py`, ablate in `train.py`; new market -> new model artefact + `EMRALERT_*` config, no code fork; EMR integration -> replace `PatientRepo` with a FHIR/CDS-Hooks adapter, keep `Predictor` untouched.
- **Known gaps before production:** authN/Z, audit log, in-China hosting, model registry + drift monitoring, severity features, SaMD/clinical-safety review (see `docs/architecture.md`).

## Data note and disclaimer
The exercise data is a de-identified US-style sample (states, Medicare/Medicaid). Models trained on it are for demonstration only and must be retrained on local EMR data for any real market. Decision support only; the prescriber decides.
