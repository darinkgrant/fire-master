import type { ReactNode } from "react";
import { Link } from "react-router";
import { useDependentPlan, useIncomeGap, useScenarios } from "../api/queries";
import { fmtCompact } from "../utils/formatting";
import { fmtMonthYear } from "../utils/dates";

/** Smooth-scroll to a section of the Retirement page by its element id. */
function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function Title({ to, section, children }: { to?: string; section?: string; children: ReactNode }) {
  const cls =
    "text-[var(--text-secondary)] hover:text-[var(--blue)] underline decoration-dotted underline-offset-4 decoration-[var(--border)] hover:decoration-[var(--blue)] text-left";
  if (to) return <Link to={to} className={cls}>{children}</Link>;
  return (
    <button type="button" onClick={() => section && jump(section)} className={cls}>
      {children}
    </button>
  );
}

function Pill({ tone, children }: { tone: "ok" | "warn" | "bad"; children: ReactNode }) {
  const color = tone === "ok" ? "var(--green)" : tone === "warn" ? "var(--yellow)" : "var(--red)";
  return (
    <span
      className="text-[10px] font-mono px-1.5 py-0.5 rounded ml-2"
      style={{ color, background: `color-mix(in srgb, ${color} 14%, transparent)` }}
    >
      {children}
    </span>
  );
}

function Row({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 text-sm">
      {title}
      <span className="flex items-center text-right font-mono text-[var(--text-primary)]">{children}</span>
    </div>
  );
}

/**
 * Top-of-page summary: the choices that drive the plan on the left (the monthly
 * budget is edited right here), and what they produce on the right. Every title
 * links to the section (or Settings field) holding the detail.
 */
export default function PlanSummary({
  budget,
  baseBudget,
  onBudgetChange,
  healthcare,
  retirementDate,
  cashZeroMonth,
  spendingOverrideCents,
}: {
  budget: number;
  baseBudget: number;
  onBudgetChange: (v: number | null) => void;
  healthcare: number;
  retirementDate: string | null | undefined;
  cashZeroMonth: number | null | undefined;
  spendingOverrideCents?: number;
}) {
  const { data: scenarios } = useScenarios();
  const { data: gap } = useIncomeGap(spendingOverrideCents);
  const { data: dep } = useDependentPlan(spendingOverrideCents);
  const scenario = scenarios?.find((s) => s.is_active)?.name ?? "Base plan";
  const modified = budget !== baseBudget;

  const now = new Date();
  const cashZero =
    cashZeroMonth != null
      ? new Date(now.getFullYear(), now.getMonth() + cashZeroMonth, 1).toLocaleDateString("en-US", {
          month: "short",
          year: "numeric",
        })
      : null;

  const worst = dep?.configured && dep.rows.length
    ? dep.rows.reduce((a, b) => (b.surplus < a.surplus ? b : a))
    : null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] gap-4">
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
        <div className="text-[11px] uppercase tracking-wider text-[var(--text-secondary)] mb-2">Your choices</div>
        <Row title={<Title section="spending">Monthly budget</Title>}>
          <span className="text-[var(--text-secondary)] mr-0.5">$</span>
          <input
            type="number"
            min={0}
            step={500}
            aria-label="Total monthly budget, including housing"
            value={budget}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              onBudgetChange(isNaN(v) ? null : v);
            }}
            className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-2 py-1 text-sm font-mono font-bold w-24 text-right focus:border-[var(--blue)] focus:outline-none"
            style={{ color: modified ? "var(--blue)" : "var(--text-primary)" }}
          />
        </Row>
        <div className="flex justify-end gap-2 -mt-1 mb-1 text-[10px] text-[var(--text-secondary)]">
          <span>+ ${healthcare.toLocaleString()} healthcare</span>
          {modified && (
            <button
              type="button"
              onClick={() => onBudgetChange(null)}
              className="hover:text-[var(--blue)] underline underline-offset-2"
            >
              reset to ${baseBudget.toLocaleString()}
            </button>
          )}
        </div>
        <Row title={<Title to="/settings">Last working month</Title>}>
          {retirementDate ? fmtMonthYear(retirementDate) : "—"}
        </Row>
        <Row title={<Title to="/settings">Scenario</Title>}>{scenario}</Row>
      </div>

      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
        <div className="text-[11px] uppercase tracking-wider text-[var(--text-secondary)] mb-2">What that gives you</div>
        <Row title={<Title section="cash">Cash lasts</Title>}>
          {cashZeroMonth == null ? (
            <>Never runs out<Pill tone="ok">ok</Pill></>
          ) : (
            <>
              {cashZeroMonth} months
              <Pill tone={cashZeroMonth > 12 ? "warn" : "bad"}>{cashZero}</Pill>
            </>
          )}
        </Row>
        <Row title={<Title section="income-gap">Extra income to never run out</Title>}>
          {!gap ? (
            "…"
          ) : gap.own_gap == null ? (
            <>Not reachable<Pill tone="bad">lower spending</Pill></>
          ) : gap.own_gap === 0 ? (
            <>None<Pill tone="ok">{gap.own_cushion != null ? `+${fmtCompact(gap.own_cushion)}/yr spare` : "funded"}</Pill></>
          ) : (
            <>
              {fmtCompact(gap.own_gap)}/yr
              {gap.own_lump_sum != null && <Pill tone="warn">or {fmtCompact(gap.own_lump_sum)} lump</Pill>}
            </>
          )}
        </Row>
        {dep?.configured && (
          <>
            <Row title={<Title section="dependent">{dep.name ?? "Dependent"}&apos;s trust</Title>}>
              {!worst ? (
                "…"
              ) : worst.surplus >= 0 ? (
                <>Funded<Pill tone="ok">every age</Pill></>
              ) : (
                <>
                  −{fmtCompact(-worst.surplus)}
                  <Pill tone="bad">age {Math.round(worst.owner_age)}</Pill>
                </>
              )}
            </Row>
            {dep.max_spending_fully_funded != null && (
              <Row title={<Title section="dependent">Max spend, all funded</Title>}>
                {fmtCompact(dep.max_spending_fully_funded)}/yr
                <Pill tone="ok">${Math.round(dep.max_spending_fully_funded / 12).toLocaleString()}/mo</Pill>
              </Row>
            )}
          </>
        )}
      </div>
    </div>
  );
}
