"""Read-only patient store backed by model_table.csv (stand-in for an EMR / feature-store lookup)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.schemas import PatientFeatures

CONTEXT_COLUMNS = {
    "INSURANCE_TYPE": "Insurance", "CONTRAINDICATION_LEVEL": "Contraindication level (0-3)",
    "NUM_SYMPTOMS": "Distinct symptoms recorded", "HAS_HYPERTENSION": "Hypertension",
    "HAS_DIABETES": "Diabetes", "HAS_HEART_DISEASE": "Heart disease", "HAS_IMMUNOCOMPROMISED": "Immunocompromised",
    "HAS_OBESITY": "Obesity", "HAS_MENTAL_HEALTH_DISORDERS": "Mental-health disorder",
}


class PatientRepo:
    def __init__(self, path: Path):
        self.df = pd.read_csv(path).set_index("PATIENT_ID", drop=False)
        self.df.index.name = None

    def __len__(self) -> int:
        return len(self.df)

    def get(self, pid: int) -> pd.Series | None:
        return self.df.loc[pid] if pid in self.df.index else None

    @staticmethod
    def features(row: pd.Series) -> PatientFeatures:
        return PatientFeatures(
            patient_age=int(row.PATIENT_AGE), patient_gender=row.PATIENT_GENDER, num_conditions=int(row.NUM_CONDITIONS),
            physician_type=row.PHYSICIAN_TYPE, physician_state=row.PHYSICIAN_STATE, location_type=row.LOCATION_TYPE)

    @staticmethod
    def context(row: pd.Series) -> dict:
        out: dict = {}
        for col, label in CONTEXT_COLUMNS.items():
            v = row[col]
            out[label] = ("Yes" if v == 1 else "No") if col.startswith("HAS_") else (v if isinstance(v, str) else int(v))
        return out
