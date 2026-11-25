import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import data_prep as dp  # noqa: E402

D = lambda s: pd.Timestamp(s)


def tables():
    rows = [
        # patient 1: diabetes + obesity before dx, hypertension before dx, treated same day, condition AFTER dx (must be ignored)
        ("2022-01-01", 1, None, None, "COMMERCIAL", "CONDITIONS", "diabetes"),
        ("2022-01-01", 1, None, None, "COMMERCIAL", "CONDITIONS", "DIABETES"),
        ("2022-02-01", 1, None, None, "COMMERCIAL", "CONDITIONS", "obesity"),
        ("2022-02-01", 1, None, None, "COMMERCIAL", "CONDITIONS", "hypertension"),
        ("2022-06-10", 1, 10, "OFFICE", "MEDICARE", "CONDITIONS", "disease_x"),
        ("2022-06-10", 1, 10, "OFFICE", "MEDICARE", "TREATMENTS", "drug a"),
        ("2022-06-20", 1, None, None, "MEDICARE", "CONDITIONS", "heart_disease"),
        # patient 2: child, untreated, no physician on dx day
        ("2022-06-05", 2, None, "unassigned", "COMMERCIAL", "CONDITIONS", "Disease_X"),
        ("2022-06-05", 2, None, "unassigned", "COMMERCIAL", "CONDITIONS", "Disease_X"),
        ("2022-06-05", 2, None, "unassigned", "COMMERCIAL", "CONDITIONS", "Disease_X"),
    ]
    f = pd.DataFrame(rows, columns=["TXN_DT", "PATIENT_ID", "PHYSICIAN_ID", "TXN_LOCATION_TYPE", "INSURANCE_TYPE", "TXN_TYPE", "TXN_DESC"])
    p = pd.DataFrame({"PATIENT_ID": [1, 2], "BIRTH_YEAR": [1950, 2018], "GENDER": ["F", "m"]})
    d = pd.DataFrame({"PHYSICIAN_ID": [10], "STATE": ["CA"], "PHYSICIAN_TYPE": ["family medicine"], "GENDER": ["M"], "BIRTH_YEAR": [1970]})
    return {"fact_txn": f, "dim_patient": p, "dim_physician": d}


def build():
    clean, log = dp.clean(tables())
    return dp.build_model_table(clean), log


def test_case_and_duplicates_normalised():
    clean, log = dp.clean(tables())
    assert log["duplicate_rows_removed_after_normalisation"] == 3  # two diabetes dup + two Disease_X dups
    assert set(clean["fact_txn"]["TXN_DESC"]) >= {"DIABETES", "DRUG A", "DISEASE_X"}


def test_one_row_per_patient_and_columns_in_spec_order():
    (mt, _), _ = build()
    assert mt["PATIENT_ID"].is_unique and len(mt) == 2
    assert list(mt.columns[:9]) == dp.MODEL_TABLE_CORE


def test_no_leakage_from_post_diagnosis_records():
    (mt, _), _ = build()
    p1 = mt.set_index("PATIENT_ID").loc[1]
    assert p1["HAS_HEART_DISEASE"] == 0  # recorded 10 days AFTER diagnosis
    assert p1["NUM_CONDITIONS"] == 2  # diabetes + obesity; hypertension excluded by definition
    assert p1["HAS_HYPERTENSION"] == 1


def test_target_age_and_eligibility():
    (mt, _), _ = build()
    m = mt.set_index("PATIENT_ID")
    assert m.loc[1, "TARGET"] == 1 and m.loc[2, "TARGET"] == 0
    assert m.loc[1, "PATIENT_AGE"] == 72 and m.loc[1, "ELIGIBLE"] == 1
    assert m.loc[2, "PATIENT_AGE"] == 4 and m.loc[2, "ELIGIBLE"] == 0


def test_missing_physician_and_location_become_unknown():
    (mt, _), _ = build()
    r = mt.set_index("PATIENT_ID").loc[2]
    assert r["PHYSICIAN_TYPE"] == "UNKNOWN" and r["PHYSICIAN_STATE"] == "UNKNOWN" and r["LOCATION_TYPE"] == "UNKNOWN"
    assert mt.set_index("PATIENT_ID").loc[1, "PHYSICIAN_TYPE"] == "FAMILY MEDICINE"
