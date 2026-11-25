"""Eligibility and alert logic - pure functions, unit-tested, independent of the model."""
from __future__ import annotations

from app.core.config import Settings


def eligibility(age: int, num_conditions: int, s: Settings) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if age < s.min_eligible_age:
        return False, [f"Age {age} is below the Drug A label (over 12 years)"]
    if age >= s.high_risk_age:
        reasons.append(f"Age {age} (>= {s.high_risk_age})")
    if num_conditions >= 1:
        reasons.append(f"{num_conditions} high-risk condition(s) recorded")
    if not reasons:
        return False, ["No high-risk criterion met (age < 65 and no qualifying condition)"]
    return True, reasons


def tier(p_treated: float, threshold: float) -> str:
    if p_treated < threshold:
        return "LOW"
    return "MEDIUM" if p_treated < 2 * threshold else "HIGH"


def should_alert(eligible: bool, p_treated: float, threshold: float) -> bool:
    return eligible and p_treated < threshold
