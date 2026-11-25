"""Model loading, validation and inference (the only module that touches scikit-learn)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.errors import InvalidInputError, ModelUnavailableError
from app.schemas import Driver, PatientFeatures

log = logging.getLogger("emralert.model")

FIELD_TO_COLUMN = {
    "patient_age": "PATIENT_AGE", "patient_gender": "PATIENT_GENDER", "num_conditions": "NUM_CONDITIONS",
    "physician_type": "PHYSICIAN_TYPE", "physician_state": "PHYSICIAN_STATE", "location_type": "LOCATION_TYPE",
}
COLUMN_LABEL = {
    "PATIENT_AGE": "Patient age", "PATIENT_GENDER": "Patient gender", "NUM_CONDITIONS": "High-risk conditions",
    "PHYSICIAN_TYPE": "Physician specialty", "PHYSICIAN_STATE": "Physician state", "LOCATION_TYPE": "Care setting",
}


class ModelService:
    def __init__(self, model_path: Path, metadata_path: Path):
        self.model_path, self.metadata_path = model_path, metadata_path
        self.pipeline = None
        self.meta: dict = {}
        self.reference: pd.DataFrame | None = None

    def load(self) -> None:
        try:
            self.pipeline = joblib.load(self.model_path)
            self.meta = json.loads(self.metadata_path.read_text())
        except Exception as exc:  # noqa: BLE001 - surface any artefact problem as a readiness failure
            log.error("could not load model artefact: %s", exc)
            self.pipeline = None
            raise
        self.columns: list[str] = self.meta["categorical"] + self.meta["numeric"]
        log.info("loaded model %s v%s", self.meta["model_name"], self.meta["version"])

    @property
    def ready(self) -> bool:
        return self.pipeline is not None

    @property
    def version(self) -> str:
        return self.meta.get("version", "unknown")

    def set_reference(self, frame: pd.DataFrame, n: int = 150) -> None:
        self.reference = frame[self.columns].sample(min(n, len(frame)), random_state=7).reset_index(drop=True)

    def _frame(self, items: list[PatientFeatures]) -> pd.DataFrame:
        rows = [{FIELD_TO_COLUMN[k]: v for k, v in it.model_dump().items()} for it in items]
        return pd.DataFrame(rows)[self.columns]

    def unseen(self, item: PatientFeatures) -> list[str]:
        out = []
        for col in self.meta["categorical"]:
            val = getattr(item, next(k for k, v in FIELD_TO_COLUMN.items() if v == col))
            if val not in self.meta["categories"].get(col, []):
                out.append(f"{COLUMN_LABEL[col]}: '{val}'")
        return out

    def predict_proba(self, items: list[PatientFeatures]) -> np.ndarray:
        if not self.ready:
            raise ModelUnavailableError("Model artefact is not loaded")
        try:
            return self.pipeline.predict_proba(self._frame(items))[:, 1]
        except Exception as exc:  # noqa: BLE001
            log.exception("inference failed")
            raise InvalidInputError("Model could not score the supplied features", str(exc)) from exc

    @staticmethod
    def _display(col: str, v) -> str:
        if col in ("PATIENT_AGE", "NUM_CONDITIONS", "PHYSICIAN_STATE", "PATIENT_GENDER"):
            return str(v)
        return str(v).title()

    def drivers(self, item: PatientFeatures, p: float, top: int = 3) -> list[Driver]:
        """Occlusion explanation: swap one feature for values seen in a reference sample and measure the shift."""
        if self.reference is None or not self.ready:
            return []
        base = self._frame([item])
        out = []
        for col in self.columns:
            if col not in COLUMN_LABEL:
                continue
            rep = pd.concat([base] * len(self.reference), ignore_index=True)
            rep[col] = self.reference[col].values
            effect = p - float(self.pipeline.predict_proba(rep)[:, 1].mean())
            out.append((col, effect))
        out.sort(key=lambda t: -abs(t[1]))
        drivers = []
        for col, eff in out[:top]:
            if abs(eff) < 0.005:
                continue
            drivers.append(Driver(feature=COLUMN_LABEL[col], value=self._display(col, base.iloc[0][col]),
                                  effect=round(eff * 100, 1), direction="raises" if eff > 0 else "lowers"))
        return drivers
