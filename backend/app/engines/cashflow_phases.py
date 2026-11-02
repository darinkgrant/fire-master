"""Cash flow by phase: the plan's monthly flows grouped into stretches where the
same income and costs apply.

Built from project_wealth_pools(capture_lines=True, monthly points), so the
numbers are the trusted engine's own: income sources (take-home), Social
Security, cashflow events (income +, costs −), and spending (budget incl.
healthcare and property carry, after spending phases). Pool draws are how a
negative month is funded, not income, so they are not lines.

A line that fires once is a one-off (listed apart). A recurring line is "on"
for its whole cycle — a quarterly bill covers the 3 months up to each payment —
so quarterly and annual bills don't split a phase into slivers, and their
monthly figure is the payment spread over its interval (an annual premium /12).
Monthly lines are averaged over the phase.
"""

from statistics import median

from collections import defaultdict

SPENDING = "Spending"


def cash_flow_phases(points) -> dict:
    """{phases: [...], one_offs: [...]} from monthly WealthPoolPoints with lines."""
    pts = [p for p in points if p.lines is not None]
    if not pts:
        return {"phases": [], "one_offs": []}

    seen: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(pts):
        for label, amount in p.lines.items():
            if label != SPENDING and abs(amount) >= 0.5:
                seen[label].append(i)
    one_off = {label for label, idx in seen.items() if len(idx) == 1}
    # Payment interval (months) of each recurring line; a 3- or 12-month line covers
    # the months leading up to each payment.
    period = {
        label: max(1, round(median(b - a for a, b in zip(idx, idx[1:]))))
        for label, idx in seen.items() if label not in one_off
    }
    window = {
        label: (max(0, idx[0] - period[label] + 1), idx[-1])
        for label, idx in seen.items() if label not in one_off
    }
    spread = {
        label: median(pts[i].lines[label] for i in seen[label]) / period[label]
        for label in window if period[label] > 1
    }

    def signature(i: int):
        on = frozenset(l for l, (a, b) in window.items() if a <= i <= b)
        return on, round(-pts[i].lines.get(SPENDING, 0) / 100)

    runs: list[tuple[int, int]] = []
    start = 0
    for i in range(1, len(pts) + 1):
        if i == len(pts) or signature(i) != signature(start):
            runs.append((start, i - 1))
            start = i

    phases = []
    prev = None
    for a, b in runs:
        n = b - a + 1
        totals: dict[str, float] = defaultdict(float)
        for p in pts[a:b + 1]:
            for label, amount in p.lines.items():
                if label not in one_off and label not in spread:
                    totals[label] += amount
        for label, monthly in spread.items():
            lo, hi = window[label]
            totals[label] += monthly * max(0, min(b, hi) - max(a, lo) + 1)
        lines = sorted(
            ({"label": k, "monthly": round(v / n)} for k, v in totals.items() if abs(v / n) >= 0.5),
            key=lambda x: -x["monthly"],
        )
        income = sum(x["monthly"] for x in lines if x["monthly"] > 0)
        expenses = -sum(x["monthly"] for x in lines if x["monthly"] < 0)
        sig = signature(a)
        phases.append({
            "start": pts[a].date[:7],
            "end": pts[b].date[:7],
            "start_age": round(pts[a].age, 1),
            "months": n,
            "changes": _changes(prev, sig),
            "income": income,
            "expenses": expenses,
            "net": income - expenses,
            "lines": lines,
        })
        prev = sig

    one_offs = [
        {"month": pts[i].date[:7], "label": label, "amount": round(pts[i].lines[label])}
        for label in sorted(one_off, key=lambda l: seen[l][0])
        for i in seen[label]
    ]
    return {"phases": phases, "one_offs": one_offs}


def _changes(prev, sig) -> list[str]:
    """What differs from the previous phase, in words."""
    if prev is None:
        return ["Today"]
    (was_on, was_spend), (on, spend) = prev, sig
    out = [f"{l} starts" for l in sorted(on - was_on)]
    out += [f"{l} ends" for l in sorted(was_on - on)]
    if spend != was_spend:
        out.append(f"Spending {'drops' if spend < was_spend else 'rises'} to ${spend * 100:,.0f}/mo")
    return out or ["Change"]
