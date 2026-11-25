# Disclosure: use of AI assistants

An AI coding/writing assistant (Cursor agent, Claude-family model) was used extensively to prepare this submission, as permitted by the instructions.

**How it was used**
- Exploratory data analysis, drafting the cleaning/feature/training scripts, FastAPI service, vanilla-JS UI, tests, Dockerfiles and CI.
- Drafting documents: ADRs, model report, strategy deck, decision memo, ROI workbook structure.
- Running and checking things: tests, Docker build and compose run, browser test of the UI, recalculating the ROI workbook.

**What stayed human-accountable (to be defended in the interview)**
- All modelling and product judgements (point-in-time anchoring, eligibility rule, model-selection rule, alert threshold, what *not* to claim).
- Business-case assumptions are explicit placeholders, not sourced facts; regulatory points need review by Pfizer Legal/Compliance.

**Verification performed:** every number in the documents is produced by the scripts or workbook in this package; code was executed (20 backend tests, ML pipeline tests, Docker Compose end-to-end, UI walk-through); outputs were read and sanity-checked rather than trusted.
