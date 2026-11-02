/** The what-if monthly budget (Retirement page), remembered in this browser across
 * reloads and logins. Never written to the plan. */
const BUDGET_KEY = "firemaster.retirement.budgetMonthly";

export function loadBudget(): number | null {
  try {
    const v = parseFloat(localStorage.getItem(BUDGET_KEY) ?? "");
    return isNaN(v) ? null : v;
  } catch {
    return null;
  }
}

export function saveBudget(v: number | null) {
  try {
    if (v == null) localStorage.removeItem(BUDGET_KEY);
    else localStorage.setItem(BUDGET_KEY, String(v));
  } catch {
    /* storage blocked: the value just won't survive a reload */
  }
}

/** The saved budget as the API's annual spending_override (cents), if any. */
export function budgetOverrideCents(): number | undefined {
  const v = loadBudget();
  return v == null ? undefined : Math.round(v * 12 * 100);
}
