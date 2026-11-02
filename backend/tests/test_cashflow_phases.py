"""Cash flow by phase: monthly engine lines grouped where the same flows apply."""

from types import SimpleNamespace as P

from app.engines.cashflow_phases import cash_flow_phases


def _pt(i, **lines):
    y, m = divmod(i, 12)
    return P(date=f"{2030 + y}-{m + 1:02d}-01", age=50 + i / 12, lines={"Spending": -4_000, **lines})


def test_phase_splits_where_a_stream_ends_and_spending_changes():
    pts = [_pt(i, Pay=6_000) for i in range(6)] + [_pt(i) for i in range(6, 9)]
    pts[8].lines["Spending"] = -3_000
    out = cash_flow_phases(pts)
    assert [(p["start"], p["months"]) for p in out["phases"]] == [("2030-01", 6), ("2030-07", 2), ("2030-09", 1)]
    first, second, third = out["phases"]
    assert (first["income"], first["expenses"], first["net"]) == (6_000, 4_000, 2_000)
    assert second["changes"] == ["Pay ends"] and second["net"] == -4_000
    assert third["changes"] == ["Spending drops to $3,000/mo"]


def test_quarterly_bill_is_spread_and_does_not_split_phases():
    pts = [_pt(i, Pay=6_000) for i in range(12)]
    for i in (2, 5, 8, 11):
        pts[i].lines["Insurance"] = -900
    out = cash_flow_phases(pts)
    assert len(out["phases"]) == 1
    lines = {x["label"]: x["monthly"] for x in out["phases"][0]["lines"]}
    assert lines["Insurance"] == -300  # 900 per quarter, from month 0 (the cycle before the first payment)


def test_single_occurrence_is_a_one_off():
    pts = [_pt(i, Pay=6_000) for i in range(4)]
    pts[2].lines["Inheritance"] = 50_000
    out = cash_flow_phases(pts)
    assert len(out["phases"]) == 1
    assert out["one_offs"] == [{"month": "2030-03", "label": "Inheritance", "amount": 50_000}]
