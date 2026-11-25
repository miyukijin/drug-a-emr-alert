from app.core.config import Settings
from app.services import decision

S = Settings()


def test_child_not_eligible():
    ok, why = decision.eligibility(12, 3, S)
    assert not ok and "below" in why[0]


def test_age_65_eligible_without_conditions():
    assert decision.eligibility(65, 0, S)[0]


def test_condition_makes_adult_eligible():
    assert decision.eligibility(40, 1, S)[0]


def test_healthy_adult_not_eligible():
    assert not decision.eligibility(40, 0, S)[0]


def test_alert_requires_eligibility_and_low_likelihood():
    assert decision.should_alert(True, 0.05, 0.15)
    assert not decision.should_alert(True, 0.30, 0.15)
    assert not decision.should_alert(False, 0.01, 0.15)


def test_tiers():
    assert decision.tier(0.1, 0.15) == "LOW"
    assert decision.tier(0.2, 0.15) == "MEDIUM"
    assert decision.tier(0.5, 0.15) == "HIGH"
