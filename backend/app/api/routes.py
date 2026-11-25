from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings
from app.core.errors import InvalidInputError, ModelUnavailableError, NotFoundError
from app.schemas import (BatchRequest, BatchResponse, Health, ModelInfo, PatientFeatures, PatientPage,
                         PatientRecord, PatientSummary, Prediction)
from app.services.patient_repo import PatientRepo

router = APIRouter()


def predictor(request: Request):
    p = getattr(request.app.state, "predictor", None)
    if p is None or not request.app.state.model.ready:
        raise ModelUnavailableError("Model or patient data is not loaded; check /health")
    return p


Pred = Annotated[object, Depends(predictor)]


@router.get("/health", response_model=Health, tags=["ops"])
def health(request: Request):
    st = request.app.state
    loaded = bool(st.model.ready and st.repo is not None)
    return Health(status="ok" if loaded else "degraded", model_loaded=st.model.ready,
                  patients_loaded=len(st.repo) if st.repo is not None else 0)


@router.get("/api/v1/model", response_model=ModelInfo, tags=["model"])
def model_info(request: Request, pred: Pred):
    m, s = request.app.state.model.meta, request.app.state.settings
    return ModelInfo(model_name=m["model_name"], version=m["version"], feature_set=m["feature_set"],
                     trained_rows=m["trained_rows"], alert_threshold=pred.threshold, min_eligible_age=s.min_eligible_age,
                     holdout_metrics=m["holdout"], categories=m["categories"])


@router.post("/api/v1/predict", response_model=Prediction, tags=["predict"])
def predict(body: PatientFeatures, pred: Pred):
    """Score one patient from JSON features; returns likelihood of being treated with Drug A."""
    return pred.predict([body])[0]


@router.post("/api/v1/predict/batch", response_model=BatchResponse, tags=["predict"])
def predict_batch(body: BatchRequest, request: Request, pred: Pred):
    limit = request.app.state.settings.max_batch_size
    if len(body.patients) > limit:
        raise InvalidInputError(f"Batch too large: {len(body.patients)} > {limit}")
    preds = pred.predict(body.patients, explain=False)
    return BatchResponse(count=len(preds), alerts=sum(p.alert for p in preds), predictions=preds)


@router.get("/api/v1/patients", response_model=PatientPage, tags=["patients"])
def list_patients(
    request: Request, pred: Pred,
    alerts_only: bool = False,
    tier: str | None = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    min_age: int | None = Query(None, ge=0, le=120),
    q: str | None = Query(None, description="Patient ID prefix"),
    sort: str = Query("likelihood_asc", pattern="^(likelihood_asc|likelihood_desc|age_desc|id_asc)$"),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
):
    st = request.app.state
    df = st.repo.df.join(st.scores)
    if alerts_only:
        df = df[df["alert"]]
    if tier:
        df = df[df["tier"] == tier]
    if min_age is not None:
        df = df[df["PATIENT_AGE"] >= min_age]
    if q:
        df = df[df["PATIENT_ID"].astype(str).str.startswith(q.strip())]
    order = {"likelihood_asc": ("p", True), "likelihood_desc": ("p", False),
             "age_desc": ("PATIENT_AGE", False), "id_asc": ("PATIENT_ID", True)}[sort]
    df = df.sort_values([order[0], "PATIENT_ID"], ascending=[order[1], True])
    total = len(df)
    chunk = df.iloc[(page - 1) * page_size: page * page_size]
    items = [PatientSummary(
        patient_id=int(r.PATIENT_ID), diagnosis_date=r.DISEASEX_DT, patient_age=int(r.PATIENT_AGE),
        patient_gender=r.PATIENT_GENDER, num_conditions=int(r.NUM_CONDITIONS), physician_type=r.PHYSICIAN_TYPE,
        location_type=r.LOCATION_TYPE, likelihood_treated=float(r.p), tier=r.tier, eligible=bool(r.eligible),
        alert=bool(r.alert), recorded_outcome_received_drug_a=bool(r.TARGET)) for r in chunk.itertuples()]
    return PatientPage(total=total, page=page, page_size=page_size, items=items)


@router.get("/api/v1/patients/{patient_id}", response_model=PatientRecord, tags=["patients"])
def get_patient(patient_id: int, request: Request, pred: Pred):
    row = request.app.state.repo.get(patient_id)
    if row is None:
        raise NotFoundError(f"Patient {patient_id} not found")
    feats = PatientRepo.features(row)
    return PatientRecord(
        patient_id=patient_id, diagnosis_date=row.DISEASEX_DT, features=feats, context=PatientRepo.context(row),
        prediction=pred.predict([feats])[0], recorded_outcome_received_drug_a=bool(row.TARGET))
