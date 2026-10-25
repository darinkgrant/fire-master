"""The retirement month drives work-tied flows.

Events flagged "ends at retirement" (custom_data.end_at) stop in the plan's
retirement month, and workplace-plan contributions run through it — so moving the
retirement date moves pay, work-funded costs and savings together.
"""

import uuid
from datetime import date

from app.engines.fire_projections import (
    apply_retirement_end,
    build_cashflow_schedule,
    ends_at_retirement,
    retirement_contributions_monthly,
)
from app.models.cashflow_event import CashflowEvent
from app.schemas.cashflow import CashflowEventResponse

TODAY = date(2026, 10, 24)


def _pay(**kw):
    base = dict(name="Take-home pay", event_type="income", amount_cents=2_000_000,
                date=date(2026, 11, 1), is_recurring=True, recurrence="monthly",
                end_date=date(2030, 8, 31), probability=1.0, status="planned",
                custom_data={"end_at": "retirement"})
    return CashflowEvent(**{**base, **kw})


def _last_month(events):
    by_month, _ = build_cashflow_schedule(events, TODAY, 20 * 12)
    return max(m for m, rows in by_month.items() if rows)


def test_flagged_event_ends_in_the_retirement_month():
    late = apply_retirement_end([_pay()], date(2035, 9, 30))
    assert late[0].end_date == date(2035, 9, 30)
    assert _last_month(late) == (2035 - 2026) * 12 + (9 - 10)
    early = apply_retirement_end([_pay()], date(2029, 12, 31))
    assert _last_month(early) == (2029 - 2026) * 12 + (12 - 10)


def test_stored_row_is_not_mutated():
    row = _pay()
    apply_retirement_end([row], date(2035, 9, 30))
    assert row.end_date == date(2030, 8, 31)


def test_unflagged_event_keeps_its_end_date():
    row = _pay(custom_data=None)
    assert apply_retirement_end([row], date(2035, 9, 30))[0] is row
    assert not ends_at_retirement(row)


def test_no_retirement_date_falls_back_to_stored_end():
    row = _pay()
    assert apply_retirement_end([row], None)[0].end_date == date(2030, 8, 31)


def test_contributions_monthly_total():
    ca = {"retirement_contributions": {"tax_deferred_annual": 24_000, "roth_annual": 12_000}}
    assert retirement_contributions_monthly(ca) == 3_000
    assert retirement_contributions_monthly({}) == 0
    assert retirement_contributions_monthly(None) == 0


def test_response_exposes_the_flag_not_custom_data():
    resp = CashflowEventResponse.model_validate(_pay(id=uuid.uuid4(), created_at=None))
    dumped = resp.model_dump()
    assert dumped["ends_at_retirement"] is True
    assert "custom_data" not in dumped
