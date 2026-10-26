import { Link } from "react-router";
import { useDependentPlan } from "../api/queries";
import { fmtCompact } from "../utils/formatting";
import { fmtMonthYear } from "../utils/dates";

const COMPONENT_LABELS: Record<string, string> = {
  investments: "Investments (pre-tax accounts after tax)",
  property_equity: "Property equity",
  inherited_home: "Inherited home",
  death_benefit: "Life insurance",
  existing_trust: "Already in the trust",
};

/**
 * Will a dependent who outlives the plan owner be funded for life?
 * For each age the owner could die at, compares what would reach the
 * dependent's trust (from the active plan's projection) with the present value
 * of the dependent's remaining lifetime need. Config: Settings → Dependent.
 */
export default function DependentPlanSection({ spendingOverrideCents }: { spendingOverrideCents?: number }) {
  const { data: plan, isLoading } = useDependentPlan(spendingOverrideCents);

  if (isLoading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-5 text-sm text-[var(--text-secondary)]">
        Checking the dependent&apos;s lifetime plan…
      </div>
    );
  }
  if (!plan?.configured) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-5 text-sm text-[var(--text-secondary)]">
        Planning for someone who will outlive you?{" "}
        <Link to="/settings" className="text-[var(--blue)] hover:underline">
          Add a dependent in Settings
        </Link>{" "}
        to see whether their trust would be funded for life.
      </div>
    );
  }

  const name = plan.name || "Dependent";
  const funded = !!plan.fully_funded;
  const maxSpend = plan.max_spending_fully_funded;
  const spend = plan.spending ?? 0;
  const worst = plan.rows.reduce<typeof plan.rows[number] | null>(
    (w, r) => (w == null || r.surplus < w.surplus ? r : w), null,
  );

  return (
    <div
      className="bg-[var(--bg-card)] border rounded-lg p-5"
      style={{ borderColor: funded ? "rgba(0,212,170,0.3)" : "rgba(255,77,106,0.3)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">{name}&apos;s lifetime plan</h3>
          <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-2xl">
            If you die at each age below, would what reaches {name}&apos;s trust pay{" "}
            {fmtCompact(plan.annual_need ?? 0)}/yr (today&apos;s dollars, beyond public benefits) until{" "}
            {name} is {plan.life_expectancy}? The trust is assumed to earn{" "}
            {((plan.trust_return_rate ?? 0) * 100).toFixed(1)}% a year after inflation.
          </p>
        </div>
        <div className="text-right">
          <div
            className="text-sm font-semibold"
            style={{ color: funded ? "var(--green)" : "var(--red)" }}
          >
            {funded ? "Funded at every age" : "Shortfall at some ages"}
          </div>
          <div className="text-xs text-[var(--text-secondary)] mt-1">
            at your spending of {fmtCompact(spend)}/yr
          </div>
          <div className="text-xs text-[var(--text-secondary)] mt-1">
            {maxSpend != null
              ? <>Max spending that still funds {name} for life: <span className="font-mono text-[var(--text-primary)]">{fmtCompact(maxSpend)}/yr</span></>
              : <>No spending level fully funds {name} — the need exceeds the estate</>}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] text-left">
              <th className="py-1 pr-3 font-medium">If you die at</th>
              <th className="py-1 pr-3 font-medium">{name}&apos;s age</th>
              <th className="py-1 pr-3 font-medium">Years to fund</th>
              <th className="py-1 pr-3 font-medium text-right">Trust needs</th>
              <th className="py-1 pr-3 font-medium text-right">Trust gets</th>
              <th className="py-1 font-medium text-right">Surplus / shortfall</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {plan.rows.map((r) => (
              <tr key={r.date} className="border-t border-[var(--border)]">
                <td className="py-1.5 pr-3">
                  {Math.round(r.owner_age)} <span className="text-[var(--text-secondary)]">({fmtMonthYear(r.date)})</span>
                </td>
                <td className="py-1.5 pr-3">{Math.round(r.dependent_age)}</td>
                <td className="py-1.5 pr-3">{Math.round(r.years_to_fund)}</td>
                <td className="py-1.5 pr-3 text-right">{fmtCompact(r.need)}</td>
                <td
                  className="py-1.5 pr-3 text-right"
                  title={Object.entries(r.components)
                    .filter(([, v]) => v > 0)
                    .map(([k, v]) => `${COMPONENT_LABELS[k] ?? k}: ${fmtCompact(v)}`)
                    .join("\n")}
                >
                  {fmtCompact(r.available)}
                </td>
                <td className="py-1.5 text-right" style={{ color: r.surplus >= 0 ? "var(--green)" : "var(--red)" }}>
                  {r.surplus >= 0 ? "+" : "−"}{fmtCompact(Math.abs(r.surplus))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-[var(--text-secondary)] mt-3 italic">
        Hover &quot;Trust gets&quot; for the breakdown. Tightest point: age {worst ? Math.round(worst.owner_age) : "—"}.
        Assumes life insurance and the inherited home are payable to the trust, pre-tax accounts lose ~25% to
        income tax, and public benefits (SSI, Medicaid, in-home support) continue. Change these in Settings → Dependent. Have a
        special-needs planning attorney confirm the trust can hold and use these assets without affecting benefits.
      </p>
    </div>
  );
}
