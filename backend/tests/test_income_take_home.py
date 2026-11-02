"""Income sources carry dates and an optional take-home amount.

Cash-flow engines use net_annual_amount when set (the tax engine keeps the
gross). Earned income ends at retirement without an end_date, and joins the
pool engine only once it has a take-home amount — without one the plan models
pay as net cashflow events, so the gross would double count.
"""

from datetime import date

from app.engines.cashflow import CashflowEngine
from app.engines.fire_projections import (
    FireProjectionsEngine,
    cash_annual_cents,
    earned_source_active,
    net_annual_cents,
)
from app.models.enums import IncomeType
from app.models.income_source import IncomeSource

RETIRE = date(2032, 8, 31)


def _src(annual, net=None, income_type=IncomeType.SALARY, start=None, end=None):
    s = IncomeSource()
    s.name = "Pay"
    s.income_type = income_type
    s.annual_amount = annual
    s.net_annual_amount = net
    s.start_date = start
    s.end_date = end
    s.growth_rate = None
    s.is_active = True
    return s


def test_take_home_wins_for_cash_flow():
    assert cash_annual_cents(_src(825_000_00, 347_712_00)) == 347_712_00
    assert cash_annual_cents(_src(825_000_00)) == 825_000_00
    assert net_annual_cents(_src(825_000_00)) is None


def test_start_and_end_dates_bound_a_source():
    s = _src(100, start=date(2027, 1, 1), end=date(2027, 12, 31))
    assert not earned_source_active(s, date(2026, 12, 2), RETIRE)
    assert earned_source_active(s, date(2027, 6, 2), RETIRE)
    assert not earned_source_active(s, date(2028, 1, 2), RETIRE)


def test_earned_without_end_date_stops_at_retirement():
    pay = _src(100, start=date(2027, 1, 1))
    assert earned_source_active(pay, date(2032, 8, 2), RETIRE)
    assert not earned_source_active(pay, date(2032, 9, 2), RETIRE)
    rent = _src(100, income_type=IncomeType.RENTAL)
    assert earned_source_active(rent, date(2040, 1, 2), RETIRE)


def test_runway_and_lifetime_use_take_home_and_dates():
    sources = [
        _src(800_925_00, 335_916_00, end=date(2026, 12, 31)),
        _src(825_000_00, 347_712_00, start=date(2027, 1, 1)),
    ]
    fp = FireProjectionsEngine.__new__(FireProjectionsEngine)
    for on, expected in [
        (date(2026, 12, 2), 335_916_00 // 12),
        (date(2027, 1, 2), 347_712_00 // 12),
        (date(2032, 9, 2), 0),
    ]:
        assert CashflowEngine.modeled_income_for_month(sources, on, RETIRE) == expected
        assert fp._income_at_month(sources, on, RETIRE, 0.0) == expected


def test_start_and_end_can_follow_retirement():
    from app.engines.fire_projections import source_window
    pension = _src(100, income_type=IncomeType.OTHER)
    pension.custom_data = {"start_at": "retirement"}
    assert source_window(pension, RETIRE) == (date(2032, 9, 1), None)
    assert not earned_source_active(pension, date(2032, 8, 2), RETIRE)
    assert earned_source_active(pension, date(2032, 9, 2), RETIRE)
    assert not earned_source_active(pension, date(2040, 1, 1), None)  # no retirement date: not started

    consult = _src(100, income_type=IncomeType.OTHER, start=date(2027, 1, 1))
    consult.custom_data = {"end_at": "retirement"}
    assert earned_source_active(consult, date(2032, 8, 2), RETIRE)
    assert not earned_source_active(consult, date(2032, 9, 2), RETIRE)
    later = date(2035, 6, 30)  # moving retirement moves the end
    assert earned_source_active(consult, date(2035, 6, 2), later)


def test_tax_engine_prorates_anchored_windows():
    from app.engines.tax_engine import _prorated_annual_for_year
    pension = _src(120_000_00, income_type=IncomeType.OTHER)
    pension.custom_data = {"start_at": "retirement"}
    assert _prorated_annual_for_year(pension, 2031, retirement_date=RETIRE) == 0
    assert 39_000 < _prorated_annual_for_year(pension, 2032, retirement_date=RETIRE) < 41_000  # Sep–Dec
    assert _prorated_annual_for_year(pension, 2032) == 0  # retirement unknown: not started


def test_pay_that_starts_at_retirement_is_not_cut_off_by_it():
    from app.engines.fire_projections import in_pool_engine
    side = _src(60_000_00, 60_000_00)
    side.custom_data = {"start_at": "retirement"}
    assert earned_source_active(side, date(2033, 1, 2), RETIRE)
    assert earned_source_active(side, date(2050, 1, 2), RETIRE)  # no end: keeps paying
    gross_only = _src(100_000_00, end=date(2037, 8, 15))
    gross_only.custom_data = {"start_at": "retirement"}
    assert in_pool_engine(gross_only, RETIRE)  # no events to double count after retirement
    assert not in_pool_engine(_src(100_000_00), RETIRE)  # working-years pay still needs take-home
    assert earned_source_active(gross_only, date(2037, 8, 2), RETIRE)
    assert not earned_source_active(gross_only, date(2037, 9, 2), RETIRE)


def test_tax_engine_counts_post_retirement_pay():
    from app.engines.fire_projections import ends_with_work
    from app.engines.tax_engine import _prorated_annual_for_year
    side = _src(60_000_00)
    side.custom_data = {"start_at": "retirement"}
    assert not ends_with_work(side, RETIRE)
    assert _prorated_annual_for_year(side, 2034, None, RETIRE) == 60_000
