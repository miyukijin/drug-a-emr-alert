"""Feature sets shared by training and serving (single source of truth)."""

CORE_CAT = ["PATIENT_GENDER", "PHYSICIAN_TYPE", "PHYSICIAN_STATE", "LOCATION_TYPE"]
CORE_NUM = ["PATIENT_AGE", "NUM_CONDITIONS"]

# Engineered features beyond the model_table spec (Step 2 "at least 2 additional features").
EXTRA_CAT = ["PHYSICIAN_GROUP"]
EXTRA_NUM = [
    "HAS_HYPERTENSION", "HAS_MENTAL_HEALTH_DISORDERS",
    "CONTRAINDICATION_LEVEL", "NUM_SYMPTOMS", "SYMPTOMS_LAST_5D", "HAS_RESP_SYMPTOM",
    "NUM_PRIOR_ENCOUNTER_DAYS", "NUM_DX_VISITS_TO_DATE", "IS_TELEHEALTH",
]

FEATURE_GROUPS = {
    "core (model_table spec)": (CORE_CAT, CORE_NUM),
    "core + clinical extras": (CORE_CAT, CORE_NUM + [
        "HAS_HYPERTENSION", "HAS_MENTAL_HEALTH_DISORDERS", "CONTRAINDICATION_LEVEL",
        "NUM_SYMPTOMS", "SYMPTOMS_LAST_5D", "HAS_RESP_SYMPTOM"]),
    "core + care-setting extras": (CORE_CAT + EXTRA_CAT, CORE_NUM + [
        "NUM_PRIOR_ENCOUNTER_DAYS", "NUM_DX_VISITS_TO_DATE", "IS_TELEHEALTH"]),
    "core + all extras": (CORE_CAT + EXTRA_CAT, CORE_NUM + EXTRA_NUM),
}
