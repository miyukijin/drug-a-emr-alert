from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parents[2] / "data" / "model_table.csv"
SPEC = ["PATIENT_ID", "TARGET", "DISEASEX_DT", "PATIENT_AGE", "PATIENT_GENDER", "NUM_CONDITIONS",
        "PHYSICIAN_TYPE", "PHYSICIAN_STATE", "LOCATION_TYPE"]


def test_model_table_matches_exercise_spec():
    df = pd.read_csv(CSV)
    assert list(df.columns[:9]) == SPEC
    assert df["PATIENT_ID"].is_unique and len(df) == 4020
    assert set(df["TARGET"]) == {0, 1}
    assert set(df["PATIENT_GENDER"]) <= {"M", "F", "U"}
    assert df["PATIENT_AGE"].between(0, 120).all() and df["NUM_CONDITIONS"].between(0, 4).all()
    assert pd.to_datetime(df["DISEASEX_DT"], format="%Y-%m-%d").notna().all()
    assert df[SPEC].notna().all().all()
    assert df.shape[1] - 9 >= 2  # at least two additional features
