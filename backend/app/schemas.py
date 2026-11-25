from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["M", "F", "U"]
Tier = Literal["LOW", "MEDIUM", "HIGH"]


class PatientFeatures(BaseModel):
    """Model inputs: the model_table feature columns (snake_case JSON)."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "patient_age": 71, "patient_gender": "F", "num_conditions": 2,
        "physician_type": "FAMILY MEDICINE", "physician_state": "CA", "location_type": "TELEHEALTH"}})

    patient_age: int = Field(ge=0, le=120, description="Age at Disease X diagnosis, years")
    patient_gender: Gender = Field(description="M, F or U (unknown)")
    num_conditions: int = Field(ge=0, le=10, description="Number of high-risk conditions at diagnosis")
    physician_type: str = Field(min_length=1, max_length=80, description="Diagnosing physician specialty")
    physician_state: str = Field(min_length=1, max_length=20, description="Diagnosing physician state code or UNKNOWN")
    location_type: str = Field(min_length=1, max_length=80, description="Care setting of the diagnosis")

    @field_validator("patient_gender", mode="before")
    @classmethod
    def _g(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("physician_type", "physician_state", "location_type", mode="before")
    @classmethod
    def _norm(cls, v):
        return " ".join(v.split()).upper() if isinstance(v, str) else v


class Driver(BaseModel):
    feature: str
    value: str
    effect: float = Field(description="Change in P(treated) attributable to this feature vs. a typical patient (percentage points)")
    direction: Literal["raises", "lowers"]


class Prediction(BaseModel):
    likelihood_treated: float = Field(ge=0, le=1, description="Model probability the patient receives Drug A")
    likelihood_untreated: float = Field(ge=0, le=1)
    tier: Tier = Field(description="Treatment-likelihood tier: LOW is the alert candidate band")
    eligible: bool
    eligibility_reasons: list[str]
    alert: bool = Field(description="True when eligible and likelihood_treated is below the alert threshold")
    alert_threshold: float
    drivers: list[Driver]
    unseen_categories: list[str] = []
    model_version: str


class BatchRequest(BaseModel):
    patients: list[PatientFeatures] = Field(min_length=1)


class BatchResponse(BaseModel):
    count: int
    alerts: int
    predictions: list[Prediction]


class PatientRecord(BaseModel):
    patient_id: int
    diagnosis_date: str
    features: PatientFeatures
    context: dict[str, int | str]
    prediction: Prediction
    recorded_outcome_received_drug_a: bool | None = Field(
        None, description="Historical outcome from the sample data (for back-testing the demo only)")


class PatientSummary(BaseModel):
    patient_id: int
    diagnosis_date: str
    patient_age: int
    patient_gender: str
    num_conditions: int
    physician_type: str
    location_type: str
    likelihood_treated: float
    tier: Tier
    eligible: bool
    alert: bool
    recorded_outcome_received_drug_a: bool


class PatientPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PatientSummary]


class ModelInfo(BaseModel):
    model_name: str
    version: str
    feature_set: str
    trained_rows: int
    alert_threshold: float
    min_eligible_age: int
    holdout_metrics: list[dict]
    categories: dict[str, list[str]]


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    patients_loaded: int
