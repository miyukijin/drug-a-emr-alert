from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration; every value can be overridden with an EMRALERT_* env var."""

    model_config = SettingsConfigDict(env_prefix="EMRALERT_", env_file=".env", extra="ignore")

    model_path: Path = REPO_ROOT / "models" / "model.joblib"
    model_metadata_path: Path = REPO_ROOT / "models" / "model_metadata.json"
    patient_data_path: Path = REPO_ROOT / "data" / "model_table.csv"
    # Alert fires when eligible AND P(treated) < alert_threshold.
    alert_threshold: float | None = None
    # Drug A label: patients "over the age of 12" -> min age 13 (birth-year granularity, see ADR-004).
    min_eligible_age: int = 13
    high_risk_age: int = 65
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"
    max_batch_size: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
