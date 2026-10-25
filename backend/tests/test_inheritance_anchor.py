"""custom_assumptions.inheritance: one month the plan moves on.

The block declares a one-off cash inflow, the inherited home's carrying cost and
(optionally) rent from the home moved out of, all starting the inheritance month.
A property sale dated "inheritance" sells that same month. Changing the one date
must move every one of those flows together, in every engine.
"""

from datetime import date

from app.engines.fire_projections import build_cashflow_schedule, inheritance_events
from app.engines.plan_months import (
    INHERITANCE_RENT_LABEL,
    apply_inheritance_anchor,
    inheritance_flows,
    inheritance_month,
    pin_plan_months,
    sale_offset,
)

TODAY = date(2026, 10, 24)
BLOCK = {"date": "2040-03", "cash": 250_000, "home_monthly_cost": 1_200,
         "vacated_home_rent": 3_000}


def _ca(**inh):
    return {"inheritance": {**BLOCK, **inh}}


def test_month_parsing():
    assert inheritance_month(_ca()) == "2040-03"
    assert inheritance_month(_ca(date="2038-03-15")) == "2038-03"
    assert inheritance_month(_ca(date="soon")) is None
    assert inheritance_month(_ca(date=None)) is None
    assert inheritance_month({}) is None


def test_flows_all_start_the_inheritance_month():
    flows = {f["name"]: f for f in inheritance_flows(_ca())}
    assert set(flows) == {"Inheritance: cash", "Inheritance: home carrying cost",
                          INHERITANCE_RENT_LABEL}
    assert all(f["date"] == date(2040, 3, 1) for f in flows.values())
    assert flows["Inheritance: cash"]["recurrence"] is None
    assert flows["Inheritance: home carrying cost"]["event_type"] == "expense"
    assert flows[INHERITANCE_RENT_LABEL]["recurrence"] == "monthly"


def test_zero_or_missing_amounts_emit_nothing():
    flows = inheritance_flows(_ca(vacated_home_rent=0, home_monthly_cost=None))
    assert [f["name"] for f in flows] == ["Inheritance: cash"]
    assert inheritance_flows({"inheritance": {"cash": 5}}) == []  # no month, no flows


def test_moving_the_date_moves_every_flow():
    total_months = 20 * 12
    early, _ = build_cashflow_schedule(inheritance_events(_ca(date="2034-01")), TODAY, total_months)
    late, _ = build_cashflow_schedule(inheritance_events(_ca(date="2040-03")), TODAY, total_months)
    m_early = (2034 - 2026) * 12 + (1 - 10)
    m_late = (2040 - 2026) * 12 + (3 - 10)
    assert ("Inheritance: cash", 250_000.0) in early[m_early]
    assert ("Inheritance: cash", 250_000.0) in late[m_late]
    assert m_late - 1 not in late  # nothing before the month
    # the recurring flows run every month after it
    assert {n for n, _ in late[m_late + 5]} == {"Inheritance: home carrying cost",
                                                INHERITANCE_RENT_LABEL}


def test_sale_dated_inheritance_follows_the_month():
    ca = {**_ca(date="2037-04"), "property_sales": [{"key": "home", "sale_date": "inheritance"}]}
    out = apply_inheritance_anchor(ca)
    assert out["property_sales"][0]["sale_date"] == "2037-04"
    assert ca["property_sales"][0]["sale_date"] == "inheritance"  # stored anchor untouched
    assert sale_offset(out["property_sales"][0], TODAY) == (2037 - 2026) * 12 + (4 - 10)


def test_sale_dated_inheritance_without_a_month_is_held():
    ca = {"property_sales": [{"key": "home", "sale_date": "inheritance"}]}
    sale = apply_inheritance_anchor(ca)["property_sales"][0]
    assert sale_offset(sale, TODAY) is None  # held, never sold "now"


def test_config_without_anchor_is_returned_as_is():
    ca = {"property_sales": [{"key": "home", "sale_date": "2030-01"}]}
    assert apply_inheritance_anchor(ca) is ca


def test_pinning_leaves_the_anchor_alone():
    ca = {"property_sales": [{"key": "home", "sale_date": "inheritance"}]}
    assert pin_plan_months(ca, TODAY)["property_sales"][0]["sale_date"] == "inheritance"
