"""Per-month P&L divisor: calendar months in the window, not months with activity.

A quarterly mortgage (or semi-annual property tax) posts in 1 of every 3 (or 6) months;
dividing by active months reported each lump payment as the monthly cost.
"""

from datetime import date

from app.engines.property_pnl import months_in_window

TODAY = date(2026, 10, 24)


def test_twelve_month_preset_counts_every_month():
    # The page's default "12m" range: start = 1st of the month 11 months back.
    assert months_in_window(date(2025, 11, 1), None, "2026-01", TODAY) == 12


def test_quarterly_payments_average_to_a_third():
    # 4 quarterly $3,000 payments in a 12-month window -> $1,000/mo, not $3,000.
    total = 4 * 3_000_00
    assert round(total / months_in_window(date(2025, 11, 1), None, "2026-01", TODAY)) == 1_000_00


def test_open_range_starts_at_first_activity():
    assert months_in_window(None, None, "2025-10", TODAY) == 13


def test_explicit_end_bounds_the_window():
    assert months_in_window(date(2026, 1, 1), date(2026, 6, 30), "2026-01", TODAY) == 6


def test_no_activity_and_open_range_is_one():
    assert months_in_window(None, None, None, TODAY) == 1


def test_never_below_one():
    assert months_in_window(date(2026, 12, 1), date(2026, 11, 30), None, TODAY) == 1
