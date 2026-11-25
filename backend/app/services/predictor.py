from __future__ import annotations

from app.core.config import Settings
from app.schemas import PatientFeatures, Prediction
from app.services import decision
from app.services.model_service import ModelService


class Predictor:
    """Combines model probability with eligibility and alert policy."""

    def __init__(self, model: ModelService, settings: Settings):
        self.model, self.s = model, settings

    @property
    def threshold(self) -> float:
        return self.s.alert_threshold if self.s.alert_threshold is not None else float(self.model.meta["alert_threshold"])

    def predict(self, items: list[PatientFeatures], explain: bool = True) -> list[Prediction]:
        probs = self.model.predict_proba(items)
        thr = self.threshold
        out = []
        for it, p in zip(items, probs):
            p = float(p)
            ok, why = decision.eligibility(it.patient_age, it.num_conditions, self.s)
            out.append(Prediction(
                likelihood_treated=round(p, 4), likelihood_untreated=round(1 - p, 4),
                tier=decision.tier(p, thr), eligible=ok, eligibility_reasons=why,
                alert=decision.should_alert(ok, p, thr), alert_threshold=thr,
                drivers=self.model.drivers(it, p) if explain else [],
                unseen_categories=self.model.unseen(it), model_version=self.model.version))
        return out

    def score_all(self, features: list[PatientFeatures], index) -> "pd.DataFrame":
        """Vectorised scoring of the whole patient store (done once at start-up for the worklist)."""
        import pandas as pd
        probs = self.model.predict_proba(features)
        thr = self.threshold
        rows = []
        for f, p in zip(features, probs):
            ok, _ = decision.eligibility(f.patient_age, f.num_conditions, self.s)
            rows.append((round(float(p), 4), ok, decision.should_alert(ok, float(p), thr), decision.tier(float(p), thr)))
        return pd.DataFrame(rows, columns=["p", "eligible", "alert", "tier"], index=index)
