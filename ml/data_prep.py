"""Step 1-2: clean the raw workbook tables and build the patient-level model table.

Point-in-time rule: every feature uses only records dated on or before the
patient's first Disease X diagnosis (DISEASEX_DT), i.e. what an EMR alert could
actually see when the diagnosis is made. Records after that date are never used
as features (they would leak the outcome).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HIGH_RISK_CONDITIONS = ["DIABETES", "HEART_DISEASE", "IMMUNOCOMPROMISED", "OBESITY"]
OTHER_CONDITIONS = ["HYPERTENSION", "MENTAL_HEALTH_DISORDERS"]
SYMPTOMS = [
    "FATIGUE", "SORE_THROAT", "COUGH", "MUSCLE_ACHE", "DIFFICULTY_BREATHING", "ACUTE_URI",
    "ACUTE_PHARYNGITIS", "FEVER", "HEADACHE", "NAUSEA_AND_VOMITING", "CONGESTION",
    "DIARRHEA", "CHILLS", "LOSS_OF_TASTE_OR_SMELL",
]
CONTRA_RANK = {"LOW_CONTRAINDICATION": 1, "MEDIUM_CONTRAINDICATION": 2, "HIGH_CONTRAINDICATION": 3}

LOCATION_SYNONYMS = {
    "CLINIC  - FEDERALLY QUALIFIED HEALTH CENTER (FQHC)": "FEDERALLY QUALIFIED HEALTH CENTER",
    "CLINIC - FEDERALLY QUALIFIED HEALTH CENTER (FQHC)": "FEDERALLY QUALIFIED HEALTH CENTER",
    "CLINIC - RURAL HEALTH": "RURAL HEALTH CLINIC",
    "AMBULATORY SURGICAL CENTER": "AMBULATORY SURGERY CENTER",
    "HOSPITAL INPATIENT (INCLUDING MEDICARE PART A)": "INPATIENT HOSPITAL",
    "HOSPITAL INPATIENT (MEDICARE PART B ONLY)": "INPATIENT HOSPITAL",
    "ON CAMPUS-OUTPATIENT HOSPITAL": "HOSPITAL OUTPATIENT",
    "CLINIC - COMMUNITY MENTAL HEALTH CENTER": "COMMUNITY MENTAL HEALTH CENTER",
    "UNASSIGNED": "UNKNOWN",
    "HOME HEALTH SERVICES UNDER A PLAN OF TREATMENT (EFFECTIVE ON 10/13)]": "HOME HEALTH SERVICES",
    "TELEHEALTH PROVIDED IN PATIENT'S HOME": "TELEHEALTH",
    "TELEHEALTH PROVIDED OTHER THAN IN PATIENT'S HOME": "TELEHEALTH",
}

PRIMARY_CARE = {"FAMILY MEDICINE", "INTERNAL MEDICINE", "GENERAL PRACTICE", "PEDIATRICS",
                "INTERNAL MEDICINE/PEDIATRICS", "GERIATRIC MEDICINE (INTERNAL MEDICINE)"}
APP = {"NURSE PRACTITIONER", "PHYSICIAN ASSISTANT"}
ACUTE = {"EMERGENCY MEDICINE", "HOSPITALIST", "PEDIATRIC EMERGENCY MEDICINE (PEDIATRICS)"}

MODEL_TABLE_CORE = [
    "PATIENT_ID", "TARGET", "DISEASEX_DT", "PATIENT_AGE", "PATIENT_GENDER", "NUM_CONDITIONS",
    "PHYSICIAN_TYPE", "PHYSICIAN_STATE", "LOCATION_TYPE",
]


def load_raw(xlsx: Path) -> dict[str, pd.DataFrame]:
    return {s: pd.read_excel(xlsx, sheet_name=s) for s in ("fact_txn", "dim_patient", "dim_physician")}


def clean(raw: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict]:
    """Return cleaned tables plus a data-quality log (every number is reproducible)."""
    log: dict = {}
    f = raw["fact_txn"].copy()
    p = raw["dim_patient"].copy()
    d = raw["dim_physician"].copy()
    log["rows_fact_raw"] = len(f)

    for c in ("TXN_LOCATION_TYPE", "INSURANCE_TYPE", "TXN_TYPE", "TXN_DESC"):
        f[c] = f[c].astype("string").str.strip().str.upper().str.replace(r"\s+", " ", regex=True)
    f["TXN_DT"] = pd.to_datetime(f["TXN_DT"], errors="coerce")
    log["unparseable_dates"] = int(f["TXN_DT"].isna().sum())
    f = f.dropna(subset=["TXN_DT"])

    log["txn_desc_distinct_raw"] = int(raw["fact_txn"]["TXN_DESC"].nunique())
    log["txn_desc_distinct_clean"] = int(f["TXN_DESC"].nunique())
    log["exact_duplicate_rows_raw"] = int(raw["fact_txn"].duplicated().sum())
    before = len(f)
    f = f.drop_duplicates()
    log["duplicate_rows_removed_after_normalisation"] = before - len(f)

    log["physician_id_missing_txn"] = int(f["PHYSICIAN_ID"].isna().sum())
    log["location_missing_txn"] = int(f["TXN_LOCATION_TYPE"].isna().sum())
    f["TXN_LOCATION_TYPE"] = (
        f["TXN_LOCATION_TYPE"].replace(LOCATION_SYNONYMS).fillna("UNKNOWN").astype(str)
    )
    log["location_types_clean"] = int(f["TXN_LOCATION_TYPE"].nunique())
    log["orphan_patient_ids"] = int((~f["PATIENT_ID"].isin(p["PATIENT_ID"])).sum())
    known = f["PHYSICIAN_ID"].dropna()
    log["orphan_physician_ids"] = int((~known.isin(d["PHYSICIAN_ID"])).sum())
    log["dim_patient_duplicate_ids"] = int(p["PATIENT_ID"].duplicated().sum())
    log["dim_physician_duplicate_ids"] = int(d["PHYSICIAN_ID"].duplicated().sum())

    p["GENDER"] = p["GENDER"].astype("string").str.strip().str.upper()
    d["PHYSICIAN_TYPE"] = d["PHYSICIAN_TYPE"].astype("string").str.strip().str.upper()
    d["STATE"] = d["STATE"].astype("string").str.strip().str.upper()
    log["physician_state_missing"] = int(d["STATE"].isna().sum())
    log["physician_birth_year_missing"] = int(d["BIRTH_YEAR"].isna().sum())
    log["physician_birth_year_implausible_<1930"] = int((d["BIRTH_YEAR"] < 1930).sum())
    d.loc[d["BIRTH_YEAR"] < 1930, "BIRTH_YEAR"] = np.nan
    log["rows_fact_clean"] = len(f)
    return {"fact_txn": f, "dim_patient": p, "dim_physician": d}, log


def build_model_table(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    f, p, d = tables["fact_txn"], tables["dim_patient"], tables["dim_physician"]
    log: dict = {}

    dx = f[f["TXN_DESC"] == "DISEASE_X"]
    first_dx = dx.groupby("PATIENT_ID")["TXN_DT"].min().rename("DISEASEX_DT")
    log["patients_total"] = int(len(p))
    log["patients_with_diseasex"] = int(first_dx.size)
    log["patients_with_multiple_dx_records"] = int((dx.groupby("PATIENT_ID").size() > 1).sum())

    treated = set(f.loc[f["TXN_TYPE"] == "TREATMENTS", "PATIENT_ID"])
    base = p.set_index("PATIENT_ID").join(first_dx, how="inner")
    base["TARGET"] = base.index.isin(treated).astype(int)
    base["PATIENT_AGE"] = base["DISEASEX_DT"].dt.year - base["BIRTH_YEAR"]
    base["PATIENT_GENDER"] = base["GENDER"].where(base["GENDER"].isin(["M", "F"]), "U")

    # Diagnosing encounter = the earliest-day Disease X record(s); prefer rows that name a physician.
    fdx = dx.merge(first_dx.reset_index(), on="PATIENT_ID")
    fdx = fdx[fdx["TXN_DT"] == fdx["DISEASEX_DT"]].copy()
    fdx["_has_phys"] = fdx["PHYSICIAN_ID"].notna().astype(int)
    fdx = fdx.sort_values(["PATIENT_ID", "_has_phys", "PHYSICIAN_ID", "TXN_LOCATION_TYPE"],
                          ascending=[True, False, True, True])
    enc = fdx.drop_duplicates("PATIENT_ID").set_index("PATIENT_ID")
    enc = enc.join(d.set_index("PHYSICIAN_ID"), on="PHYSICIAN_ID")
    base["PHYSICIAN_ID"] = enc["PHYSICIAN_ID"]
    base["PHYSICIAN_TYPE"] = enc["PHYSICIAN_TYPE"].fillna("UNKNOWN")
    base["PHYSICIAN_STATE"] = enc["STATE"].fillna("UNKNOWN")
    base["LOCATION_TYPE"] = enc["TXN_LOCATION_TYPE"].fillna("UNKNOWN")
    base["INSURANCE_TYPE"] = enc["INSURANCE_TYPE"].fillna("UNSPECIFIED")
    base["PHYSICIAN_AGE"] = base["DISEASEX_DT"].dt.year - enc["BIRTH_YEAR"]
    base["PHYSICIAN_GENDER"] = enc["GENDER"].fillna("U")
    log["patients_no_physician_on_dx_day"] = int(base["PHYSICIAN_ID"].isna().sum())

    # Point-in-time history: records dated <= DISEASEX_DT
    h = f.merge(first_dx.reset_index(), on="PATIENT_ID")
    h["days_before"] = (h["DISEASEX_DT"] - h["TXN_DT"]).dt.days
    log["records_after_dx_excluded_from_features"] = int((h["days_before"] < 0).sum())
    hist = h[h["days_before"] >= 0]

    cond = hist[hist["TXN_TYPE"] == "CONDITIONS"]
    cflags = pd.crosstab(cond["PATIENT_ID"], cond["TXN_DESC"]).clip(upper=1)
    for c in HIGH_RISK_CONDITIONS + OTHER_CONDITIONS:
        base[f"HAS_{c}"] = cflags[c].reindex(base.index).fillna(0).astype(int) if c in cflags else 0
    base["NUM_CONDITIONS"] = base[[f"HAS_{c}" for c in HIGH_RISK_CONDITIONS]].sum(axis=1)

    sym = hist[hist["TXN_TYPE"] == "SYMPTOMS"]
    base["NUM_SYMPTOMS"] = sym.groupby("PATIENT_ID")["TXN_DESC"].nunique().reindex(base.index).fillna(0).astype(int)
    base["HAS_RESP_SYMPTOM"] = (
        sym[sym["TXN_DESC"].isin(["DIFFICULTY_BREATHING", "COUGH"])]
        .groupby("PATIENT_ID").size().reindex(base.index).fillna(0).gt(0).astype(int)
    )
    recent = sym[sym["days_before"] <= 5]
    base["SYMPTOMS_LAST_5D"] = recent.groupby("PATIENT_ID")["TXN_DESC"].nunique().reindex(base.index).fillna(0).astype(int)

    contra = hist[hist["TXN_TYPE"] == "CONTRAINDICATIONS"].copy()
    contra["rank"] = contra["TXN_DESC"].map(CONTRA_RANK)
    base["CONTRAINDICATION_LEVEL"] = contra.groupby("PATIENT_ID")["rank"].max().reindex(base.index).fillna(0).astype(int)

    base["NUM_PRIOR_ENCOUNTER_DAYS"] = hist.groupby("PATIENT_ID")["TXN_DT"].nunique().reindex(base.index).fillna(0).astype(int)
    base["NUM_DX_VISITS_TO_DATE"] = dx.merge(first_dx.reset_index(), on="PATIENT_ID").query("TXN_DT <= DISEASEX_DT") \
        .groupby("PATIENT_ID")["TXN_DT"].size().reindex(base.index).fillna(1).astype(int)

    base["IS_AGE_65_PLUS"] = (base["PATIENT_AGE"] >= 65).astype(int)
    base["IS_TELEHEALTH"] = (base["LOCATION_TYPE"] == "TELEHEALTH").astype(int)
    base["PHYSICIAN_GROUP"] = base["PHYSICIAN_TYPE"].map(
        lambda t: "UNKNOWN" if t == "UNKNOWN" else "PRIMARY_CARE" if t in PRIMARY_CARE
        else "APP" if t in APP else "ACUTE_CARE" if t in ACUTE else "SPECIALIST")
    base["ELIGIBLE"] = ((base["PATIENT_AGE"] > 12) & ((base["PATIENT_AGE"] >= 65) | (base["NUM_CONDITIONS"] >= 1))).astype(int)

    out = base.reset_index().rename(columns={"index": "PATIENT_ID"})
    out["DISEASEX_DT"] = out["DISEASEX_DT"].dt.strftime("%Y-%m-%d")
    extra = [c for c in out.columns if c not in MODEL_TABLE_CORE and c not in ("BIRTH_YEAR", "GENDER", "PHYSICIAN_ID")]
    out = out[MODEL_TABLE_CORE + extra]
    log["model_table_rows"] = len(out)
    log["model_table_unique_patients"] = int(out["PATIENT_ID"].nunique())
    log["target_rate"] = round(float(out["TARGET"].mean()), 4)
    log["eligible_patients"] = int(out["ELIGIBLE"].sum())
    log["eligible_target_rate"] = round(float(out.loc[out["ELIGIBLE"] == 1, "TARGET"].mean()), 4)
    return out, log


def main(xlsx: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tables, dq = clean(load_raw(Path(xlsx)))
    mt, mlog = build_model_table(tables)
    mt.to_csv(out / "model_table.csv", index=False)
    (out / "data_quality_log.json").write_text(json.dumps({**dq, **mlog}, indent=2))
    print(json.dumps({**dq, **mlog}, indent=2))


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2])
