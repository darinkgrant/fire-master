"""Income-gap probes: the smallest extra post-retirement income that keeps the plan alive."""

from datetime import date

import pytest

from app.api.fire import _bisect_dollars, _post_retirement_income


@pytest.mark.asyncio
async def test_bisect_finds_threshold_within_step():
    async def ok(x):
        return x >= 91_234
    found = await _bisect_dollars(ok)
    assert 91_234 <= found <= 91_234 + 1_000


@pytest.mark.asyncio
async def test_bisect_zero_when_already_fine():
    async def ok(x):
        return True
    assert await _bisect_dollars(ok) == 0


@pytest.mark.asyncio
async def test_bisect_none_when_unreachable():
    async def ok(x):
        return False
    assert await _bisect_dollars(ok) is None


def test_income_stream_is_monthly_for_life():
    (ev,) = _post_retirement_income(60_000, date(2032, 9, 1))
    assert ev.event_type == "income" and ev.is_recurring and ev.recurrence == "monthly"
    assert ev.amount_cents == 500_000 and ev.end_date is None and ev.date == date(2032, 9, 1)


def test_lump_is_one_time():
    (ev,) = _post_retirement_income(130_000, date(2032, 9, 1), lump=True)
    assert not ev.is_recurring and ev.recurrence is None and ev.amount_cents == 13_000_000


def test_zero_income_adds_nothing():
    assert _post_retirement_income(0, date(2032, 9, 1)) == []


def test_first_shortfall_finds_the_first_negative_point():
    from types import SimpleNamespace as P

    from app.api.fire import _first_shortfall
    ok = [P(age=50, cash=10, total=100, date="2030-01-01"), P(age=60, cash=5, total=50, date="2040-01-01")]
    assert _first_shortfall(P(points=ok), 61) is None
    dip = [ok[0], P(age=55, cash=-500, total=40, date="2035-03-01"), ok[1]]
    assert _first_shortfall(P(points=dip), 61).date == "2035-03-01"
    stops = [ok[0], P(age=70, cash=0, total=0, date="2050-01-01")]
    assert _first_shortfall(P(points=stops), 90).age == 70  # projection ended early
