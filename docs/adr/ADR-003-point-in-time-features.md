# ADR-003: Point-in-time feature construction anchored on first Disease X diagnosis

- **Status:** Accepted
## Context
`fact_txn` mixes history and post-diagnosis events (7,811 cleaned records are dated after the patient's first Disease X record, up to 90 days later). Using them would leak the outcome (Drug A is itself a record in the same table).
## Decision
- `DISEASEX_DT` = the **earliest** Disease X record per patient (all fall in Apr-Jun 2022).
- Every feature uses records dated **on or before** `DISEASEX_DT`.
- Diagnosing encounter = the first-day Disease X record, preferring rows that name a physician; physician/location/insurance come from it. 579 patients have no physician on that day -> `UNKNOWN` (kept as a signal: lab-only diagnoses, no prescriber).
- `TARGET` = any Drug A treatment record for the patient (as specified). 65 patients have a Drug A record up to 50 days *before* their first Disease X record; they remain `TARGET=1` and are flagged as a data-quality question for the data owner.
## Consequences
Serving-time features match what the EMR can know at diagnosis time. Offline metrics are therefore honest estimates of alert-time performance (but still from one 3-month window; see limitations).
