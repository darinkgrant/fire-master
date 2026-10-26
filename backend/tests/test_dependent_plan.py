"""Dependent who outlives the owner: trust need vs what reaches the trust."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.engines.dependent_plan import (
    dependent_age,
    dependent_cfg,
    trust_need,
    trust_resources,
)

DEP = {"name": "Child", "birth_date": "2005-06", "life_expectancy": 80,
       "annual_need": 60_000, "trust_return_rate": 0.04, "trust_balance": 0,
       "death_benefit": 250_000, "include_inherited_home": True, "ira_tax_rate": 0.25}
TODAY = date(2026, 10, 1)


def _point(**kw):
    base = dict(cash=10_000, taxable=100_000, roth=50_000, ira_sepp=0, ira_growth=200_000,
                real_estate=300_000)
    return SimpleNamespace(**{**base, **kw})


def test_configured_only_with_a_birth_month():
    assert dependent_cfg({"dependent": DEP}) is DEP
    assert dependent_cfg({"dependent": {**DEP, "birth_date": ""}}) is None
    assert dependent_cfg({}) is None


def test_need_is_present_value_of_remaining_life():
    need, years = trust_need(DEP, date(2055, 6, 1))  # child is 50 → 30 years to 80
    assert years == pytest.approx(30, abs=0.01)
    # 30 years of $60k at 4% real ≈ $1.05M (an annuity factor ~17.4, monthly payments)
    assert 1_030_000 < need < 1_070_000


def test_zero_rate_is_simple_sum():
    need, _ = trust_need({**DEP, "trust_return_rate": 0}, date(2075, 6, 1))  # 10 years left
    assert need == pytest.approx(600_000)


def test_no_need_after_planned_end():
    assert trust_need(DEP, date(2090, 1, 1)) == (0.0, 0.0)


def test_earlier_death_needs_more():
    assert trust_need(DEP, date(2040, 1, 1))[0] > trust_need(DEP, date(2060, 1, 1))[0]


def test_resources_haircut_pretax_and_add_home_after_inheritance():
    ca = {"inheritance": {"date": "2030-01", "home_value": 1_000_000},
          "projection": {"re_appreciation_rate": 0.0}}
    before = trust_resources(_point(), DEP, ca, date(2029, 1, 1), TODAY)
    after = trust_resources(_point(), DEP, ca, date(2031, 1, 1), TODAY)
    assert before["investments"] == pytest.approx(10_000 + 100_000 + 50_000 + 200_000 * 0.75)
    assert before["inherited_home"] == 0
    assert after["inherited_home"] == pytest.approx(1_000_000)
    assert after["death_benefit"] == 250_000
    assert after["property_equity"] == 300_000


def test_home_excluded_when_not_earmarked():
    ca = {"inheritance": {"date": "2030-01", "home_value": 1_000_000}}
    res = trust_resources(_point(), {**DEP, "include_inherited_home": False}, ca, date(2031, 1, 1), TODAY)
    assert res["inherited_home"] == 0


def test_negative_cash_does_not_reduce_resources():
    res = trust_resources(_point(cash=-5_000), DEP, {}, date(2031, 1, 1), TODAY)
    assert res["investments"] == pytest.approx(100_000 + 50_000 + 150_000)


def test_dependent_age():
    assert dependent_age(DEP, date(2035, 6, 1)) == pytest.approx(30)


def test_working_death_benefit_applies_through_retirement():
    from app.engines.dependent_plan import death_benefit
    dep = {**DEP, "death_benefit_working": 1_000_000}
    retire = date(2032, 6, 30)
    assert death_benefit(dep, date(2030, 1, 1), retire) == 1_000_000
    assert death_benefit(dep, date(2032, 6, 30), retire) == 1_000_000
    assert death_benefit(dep, date(2033, 1, 1), retire) == 250_000
    assert death_benefit(DEP, date(2030, 1, 1), retire) == 250_000  # no working amount set
    assert death_benefit(dep, date(2030, 1, 1), None) == 250_000
