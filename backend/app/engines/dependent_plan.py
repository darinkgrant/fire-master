"""Lifetime funding for a dependent who outlives the plan owner.

custom_assumptions.dependent = {
    "name": "...",                  # display only
    "birth_date": "YYYY-MM",
    "life_expectancy": 85,          # plan the trust to last to this age
    "annual_need": 100000,          # real $/yr the trust must pay beyond public benefits
    "trust_return_rate": 0.04,      # real return the trust earns
    "trust_balance": 0,             # already in the trust today (real $)
    "death_benefit": 700000,        # life insurance payable to the trust (after retirement)
    "death_benefit_working": 2000000,  # optional: through the retirement date (premiums paid)
    "include_inherited_home": true, # custom_assumptions.inheritance.home_value goes to the trust
    "ira_tax_rate": 0.25,           # haircut on pre-tax accounts the trust inherits
}

The question it answers: if the owner dies at age X, is what the estate holds
then (per project_wealth_pools) enough to fund the dependent's need for the rest
of the dependent's life? Pure functions — the API composes them with the projection.
"""

from datetime import date

DEFAULT_TRUST_RETURN = 0.04
DEFAULT_IRA_TAX = 0.25


def dependent_cfg(ca: dict | None) -> dict | None:
    """The dependent block, or None when not configured (no birth date)."""
    dep = (ca or {}).get("dependent")
    if not isinstance(dep, dict) or not str(dep.get("birth_date") or "")[:7]:
        return None
    return dep


def _ym(value: str) -> tuple[int, int]:
    raw = str(value)[:7]
    return int(raw[:4]), int(raw[5:7])


def dependent_end(dep: dict) -> date:
    """First month after the dependent reaches the planned life expectancy."""
    y, m = _ym(dep["birth_date"])
    return date(y + int(dep.get("life_expectancy") or 85), m, 1)


def dependent_age(dep: dict, on: date) -> float:
    y, m = _ym(dep["birth_date"])
    return (on.year - y) + (on.month - m) / 12


def trust_need(dep: dict, death: date) -> tuple[float, float]:
    """(Trust money needed at `death`, years it must last), in real dollars.

    Present value at the trust's real return of the dependent's annual need,
    paid monthly from the month after death until the planned end of the
    dependent's life."""
    end = dependent_end(dep)
    months = (end.year - death.year) * 12 + (end.month - death.month)
    if months <= 0:
        return 0.0, 0.0
    need_m = float(dep.get("annual_need") or 0) / 12
    rate = dep.get("trust_return_rate")
    r_m = (1 + (DEFAULT_TRUST_RETURN if rate is None else float(rate))) ** (1 / 12) - 1
    pv = need_m * months if r_m == 0 else need_m * (1 - (1 + r_m) ** -months) / r_m
    return pv, months / 12


def death_benefit(dep: dict, death: date, retirement: date | None) -> float:
    """Life insurance reaching the trust. `death_benefit_working` applies through the
    retirement date (premiums still being paid — typically the full face amount);
    `death_benefit` after it (e.g. a reduced paid-up policy once premiums stop)."""
    working = dep.get("death_benefit_working")
    if working is not None and retirement is not None and death <= retirement:
        return float(working or 0)
    return float(dep.get("death_benefit") or 0)


def trust_resources(
    point, dep: dict, ca: dict, death: date, today: date, retirement: date | None = None,
) -> dict[str, float]:
    """What reaches the trust if the owner dies at this projection point (real $).

    Investments come from the projection (pre-tax IRA pools haircut for the
    income tax due when the trust draws them); property equity the projection
    still holds; the inherited home when it has been received and is earmarked;
    the life-insurance death benefit (working-years amount through retirement);
    and what the trust already holds, grown at its real return."""
    ira_tax = dep.get("ira_tax_rate")
    ira_tax = DEFAULT_IRA_TAX if ira_tax is None else float(ira_tax)
    years = max(0.0, (death.year - today.year) + (death.month - today.month) / 12)
    rate = dep.get("trust_return_rate")
    rate = DEFAULT_TRUST_RETURN if rate is None else float(rate)

    home = 0.0
    inh = (ca or {}).get("inheritance") or {}
    if dep.get("include_inherited_home") and inh.get("date") and inh.get("home_value"):
        iy, im = _ym(inh["date"])
        if (iy, im) <= (death.year, death.month):
            appr = float(((ca or {}).get("projection") or {}).get("re_appreciation_rate", 0.01) or 0)
            home = float(inh["home_value"]) * (1 + appr) ** years

    return {
        "investments": max(0.0, point.cash) + point.taxable + point.roth
        + (point.ira_sepp + point.ira_growth) * (1 - ira_tax),
        "property_equity": max(0.0, point.real_estate),
        "inherited_home": home,
        "death_benefit": death_benefit(dep, death, retirement),
        "existing_trust": float(dep.get("trust_balance") or 0) * (1 + rate) ** years,
    }
