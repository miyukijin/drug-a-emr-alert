# model_table data dictionary

First nine columns follow the exercise `model_table` layout exactly. Extra columns are engineered features (point-in-time: only records dated on/before `DISEASEX_DT`).

| Column | Type | Description |
|---|---|---|
| PATIENT_ID | int | Unique patient id (one row per patient) |
| TARGET | 0/1 | 1 = patient has a Drug A treatment record |
| DISEASEX_DT | date YYYY-MM-DD | Earliest Disease X record |
| PATIENT_AGE | int | Years at diagnosis (diagnosis year - birth year) |
| PATIENT_GENDER | M/F/U | Patient gender |
| NUM_CONDITIONS | int 0-4 | Distinct high-risk conditions (diabetes, heart disease, immunocompromised, obesity) up to diagnosis |
| PHYSICIAN_TYPE | str | Specialty of diagnosing physician (`UNKNOWN` if none recorded) |
| PHYSICIAN_STATE | str | State of diagnosing physician (`UNKNOWN` if none) |
| LOCATION_TYPE | str | Care setting of the diagnosing encounter (cleaned; `UNKNOWN` if none) |
| INSURANCE_TYPE | str | Payer on the diagnosing encounter |
| PHYSICIAN_AGE / PHYSICIAN_GENDER | num / str | Diagnosing physician demographics (nullable) |
| HAS_DIABETES, HAS_HEART_DISEASE, HAS_IMMUNOCOMPROMISED, HAS_OBESITY | 0/1 | Individual qualifying conditions |
| HAS_HYPERTENSION, HAS_MENTAL_HEALTH_DISORDERS | 0/1 | Other recorded conditions (not on the brief's high-risk list; not counted in NUM_CONDITIONS) |
| NUM_SYMPTOMS | int | Distinct Disease X symptoms recorded up to diagnosis |
| HAS_RESP_SYMPTOM | 0/1 | Cough or difficulty breathing recorded |
| SYMPTOMS_LAST_5D | int | Distinct symptoms in the 5 days up to diagnosis (Drug A window) |
| CONTRAINDICATION_LEVEL | 0-3 | Highest recorded contraindicating-medication level (0 none, 1 low, 2 medium, 3 high) |
| NUM_PRIOR_ENCOUNTER_DAYS | int | Distinct record dates up to diagnosis (utilisation) |
| NUM_DX_VISITS_TO_DATE | int | Disease X records up to and including `DISEASEX_DT` |
| IS_AGE_65_PLUS, IS_TELEHEALTH | 0/1 | Convenience flags |
| PHYSICIAN_GROUP | str | PRIMARY_CARE / APP / ACUTE_CARE / SPECIALIST / UNKNOWN |
| ELIGIBLE | 0/1 | Age > 12 and (age >= 65 or NUM_CONDITIONS >= 1) |
