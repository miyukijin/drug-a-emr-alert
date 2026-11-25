# Managing versions of code, data and models (Step 6)

Principle: **a release is the triple (code commit, dataset hash, model version)**, recorded in one manifest, so any prediction or alert can be traced and reproduced, and any release can be rolled back in minutes.

## 1. Code - Git with trunk-based development
- `main` is always releasable and protected: PR required, 1-2 reviewers (CODEOWNERS: ML for `ml/`, platform for `backend/`, product for `frontend/`), CI green, linear history (squash merge).
- Short-lived branches (< 3 days): `feat/<ticket>-...`, `fix/...`, `model/<experiment>`, `docs/...`. Conventional-commit messages; semantic version tags `vMAJOR.MINOR.PATCH` cut from `main`. A `release/x.y` branch exists only for hotfixes to a version still in the field (cherry-pick, never merge back wholesale).
- **CI gates** (`.github/workflows/ci.yml`): unit + API tests, data-contract tests on `model_table`, image build, container smoke test (`/health` and `/predict`), and for model PRs an evaluation job that must not regress the champion's hold-out metrics beyond an agreed tolerance.
- **Merging and conflict resolution:** rebase the feature branch on `main` at least daily; resolve conflicts locally on the feature branch (never on `main`, never force-push shared branches); re-run the full test suite after every resolution because textually clean merges can still be semantically wrong; for semantic conflicts (two people changing alert policy) pair on the resolution and record the decision in an ADR. Reduce conflict surface by design: generated files (lock files, OpenAPI snapshots) are regenerated not hand-merged; notebooks are stripped (nbstripout) or converted to scripts; binary artefacts never live in Git.

## 2. Data - immutable, content-addressed, in-region
- Raw extracts are write-once. **DVC** (or lakeFS) tracks datasets by content hash in Git while the bytes live in an in-region object store; no patient-level data in Git.
- `model_table` is a *derived* dataset: identified by (raw-data hash, `ml/data_prep.py` commit, config). Re-running the pipeline on the same inputs must produce the same hash (tested here: deterministic ordering, fixed seeds).
- **Data contracts** (schema, ranges, uniqueness of `PATIENT_ID`, allowed categories, no post-diagnosis leakage) run as tests on every build; failures block training.
- Retention, access and lineage follow the governance model (PIPL: purpose limitation, minimisation).

## 3. Models - registry with promotion gates
- Each training run logs parameters, metrics, data hash and git SHA to an experiment tracker (MLflow, self-hosted in-region). Artefact = `model.joblib` + `model_metadata.json` (this repo's lightweight stand-in) + model card.
- Registry stages: `Experiment -> Candidate -> Staging (shadow scoring) -> Production`. **Promotion to Production requires** (a) CI evaluation vs. champion, (b) subgroup/fairness check, (c) sign-off from the AI Governance Board (medical + compliance), recorded in the registry.
- Serving pins an exact model version; the API returns `model_version` on every call; rollback = repoint to the previous version (no rebuild if loaded from registry, or redeploy the previous image tag as in this demo).
- Post-release: monitor drift/performance; a breach triggers the retrain-or-rollback runbook.

## 4. Linking it all
A `release.json` per tag: `{git_tag, git_sha, dataset_hash, model_version, image_digests, approver, date}`. API versioning (`/api/v1`) is independent of model versioning, so model refreshes do not break clients.
