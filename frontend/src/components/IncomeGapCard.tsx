import { useIncomeGap } from "../api/queries";
import { fmtCompact } from "../utils/formatting";
import { fmtMonthYear } from "../utils/dates";

/**
 * What it takes for the plan to never run out at the configured spending:
 * extra after-tax income per year after retiring (or a one-time sum saved by
 * retirement), plus — for a dependent who outlives the owner — the extra life
 * insurance their trust would need at the worst age.
 */
export default function IncomeGapCard({ spendingOverrideCents }: { spendingOverrideCents?: number }) {
  const { data: gap, isLoading } = useIncomeGap(spendingOverrideCents);
  if (isLoading || !gap) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4 text-sm text-[var(--text-secondary)]">
        Working out what it takes to never run out…
      </div>
    );
  }
  const own = gap.own_gap;
  const ok = own === 0;
  const starts = gap.income_starts ? fmtMonthYear(gap.income_starts) : "retirement";
  const dep = gap.dependent_name;
  const depGap = gap.dependent_insurance_gap ?? 0;

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">
        To never run out at {fmtCompact(gap.spending)}/yr
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1">Your plan</div>
          {own == null ? (
            <div style={{ color: "var(--red)" }}>Not reachable with extra income alone: lower spending.</div>
          ) : ok ? (
            <div>
              <span className="font-mono font-semibold" style={{ color: "var(--green)" }}>No extra income needed</span>
              {gap.own_cushion != null && (
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  Cushion: you could spend about {fmtCompact(gap.own_cushion)}/yr more.
                </div>
              )}
            </div>
          ) : (
            <div>
              <span className="font-mono font-semibold" style={{ color: "var(--red)" }}>+{fmtCompact(own)}/yr</span>
              <span className="text-xs text-[var(--text-secondary)]"> after tax, from {starts}, for life</span>
              {gap.own_lump_sum != null && (
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  or <span className="font-mono text-[var(--text-primary)]">{fmtCompact(gap.own_lump_sum)}</span> more
                  saved by retirement (the gap sits mostly in the years before 59½)
                </div>
              )}
            </div>
          )}
        </div>
        {dep && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1">{dep}&apos;s trust</div>
            {depGap <= 0 ? (
              <span className="font-mono font-semibold" style={{ color: "var(--green)" }}>Funded at every age</span>
            ) : (
              <div>
                <span className="font-mono font-semibold" style={{ color: "var(--red)" }}>+{fmtCompact(depGap)}</span>
                <span className="text-xs text-[var(--text-secondary)]"> more life insurance to the trust</span>
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  Worst case: if you die around {Math.round(gap.dependent_gap_age ?? 0)}. A lump sum is the fix here;
                  income you would have earned later can&apos;t fund it.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
