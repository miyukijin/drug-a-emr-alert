# ADR-004: Alert = eligible AND P(treated) below a configurable threshold

- **Status:** Accepted
## Source of the rule
The exercise workbook, sheet `Instructions`, cell B12: Drug A is for "patients over the age of 12 who are at high risk of progressing to severe Disease X". Cell B13: "A patient is considered as high risk if their age is 65 or older **or** if they have underlying medical conditions, such as: chronic lung disease, cardiovascular disease, cancer, weakened immune system, obesity, diabetes, smoking". The Word brief does not define high risk. So eligible = age > 12 AND (age >= 65 OR >= 1 high-risk condition): the AND joins the age floor to the high-risk test, and the OR is inside the high-risk test.

## Decision
- **Eligible:** age > 12 (configured as `min_eligible_age=13`; only birth year is available so age = diagnosis year - birth year) AND (age >= 65 OR >= 1 qualifying condition).
- **Qualifying conditions** = diabetes, heart disease, immunocompromised, obesity (those present in the data and in the brief's high-risk list). Hypertension and mental-health disorders are *not* named in B13 (a non-exhaustive "such as" list), so they do not count towards `NUM_CONDITIONS` or eligibility. **Open point:** the data dictionary describes every `CONDITIONS` row as a condition that raises risk, so counting them is a defensible alternative; it would raise eligible patients from 2,507 to 2,693 (+186, only 8% of them treated) and the eligible treated rate from 21.2% to 20.3%. Medical to confirm. Chronic lung disease, cancer and smoking are in the brief but absent from the data.
- **Alert:** eligible AND `P(treated) < 0.15` (env `EMRALERT_ALERT_THRESHOLD`). At this threshold, on the eligible hold-out: 34% of patients are alerted; 93.6% of alerted patients were in fact untreated; 11 of 171 alerted were treated anyway.
- Threshold rationale: an alert-burden budget (about one in three eligible diagnoses) rather than max accuracy. It is a product dial, set per market with Medical.
## Consequences
Eligibility is rules (transparent, auditable, label-aligned); the model only ranks *likelihood of treatment*. High contraindication is shown to the prescriber as context rather than suppressing the alert (clinical call; to confirm with Medical).
