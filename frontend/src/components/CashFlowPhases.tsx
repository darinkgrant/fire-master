import { Fragment, useState } from "react";
import { useCashFlowPhases } from "../api/queries";
import { budgetOverrideCents } from "../utils/budget";
import { fmtMonthYear } from "../utils/dates";

const money = (v: number) => `${v < 0 ? "−" : ""}$${Math.abs(v).toLocaleString()}`;

/**
 * The plan's monthly cash flow from today to life expectancy, grouped into
 * phases where the same income and costs apply — the same engine (and the same
 * saved budget) as the Retirement page. A negative net is drawn from savings.
 */
export default function CashFlowPhases() {
  const { data, isLoading } = useCashFlowPhases(budgetOverrideCents());
  const [open, setOpen] = useState<string | null>(null);

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)]">Cash flow by phase</h3>
      <p className="text-[11px] text-[var(--text-secondary)] mt-1 mb-3">
        Per month, in today&rsquo;s dollars, from the retirement plan. Click a row for its line items.
        A negative net is drawn from savings and investments.
      </p>
      {isLoading || !data ? (
        <div className="text-xs text-[var(--text-secondary)]">Loading…</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-secondary)]">
                <th className="text-left font-medium py-1.5 pr-3">When</th>
                <th className="text-left font-medium py-1.5 pr-3">What changes</th>
                <th className="text-right font-medium py-1.5 pr-3">Income</th>
                <th className="text-right font-medium py-1.5 pr-3">Expenses</th>
                <th className="text-right font-medium py-1.5">Net</th>
              </tr>
            </thead>
            <tbody>
              {data.phases.map((p) => {
                const key = p.start;
                const isRetirement = data.retirement_month != null && p.start > data.retirement_month
                  && !data.phases.some((q) => q.start > data.retirement_month! && q.start < p.start);
                return (
                  <Fragment key={key}>
                    <tr
                      onClick={() => setOpen(open === key ? null : key)}
                      className={`border-b border-[var(--border)] cursor-pointer hover:bg-[var(--bg-hover)] ${isRetirement ? "border-t-2 border-t-[var(--blue)]" : ""}`}
                    >
                      <td className="py-2 pr-3 whitespace-nowrap">
                        <span className="text-[var(--text-primary)]">
                          {fmtMonthYear(p.start)}
                          {p.months > 1 && ` – ${fmtMonthYear(p.end)}`}
                        </span>
                        <span className="block text-[10px] text-[var(--text-secondary)]">
                          age {Math.floor(p.start_age)}{isRetirement && " · retired"}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-[var(--text-secondary)]">{p.changes.join("; ")}</td>
                      <td className="py-2 pr-3 text-right font-mono text-[var(--green)]">{money(p.income)}</td>
                      <td className="py-2 pr-3 text-right font-mono text-[var(--red)]">{money(-p.expenses)}</td>
                      <td className="py-2 text-right font-mono font-bold" style={{ color: p.net >= 0 ? "var(--green)" : "var(--red)" }}>
                        {p.net >= 0 ? "+" : ""}{money(p.net)}
                      </td>
                    </tr>
                    {open === key && (
                      <tr className="border-b border-[var(--border)] bg-[var(--bg-secondary)]">
                        <td />
                        <td colSpan={4} className="py-2">
                          {p.lines.map((l) => (
                            <div key={l.label} className="flex justify-between py-0.5">
                              <span className="text-[var(--text-secondary)]">{l.label}</span>
                              <span className="font-mono" style={{ color: l.monthly >= 0 ? "var(--green)" : "var(--red)" }}>
                                {l.monthly >= 0 ? "+" : ""}{money(l.monthly)}
                              </span>
                            </div>
                          ))}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          {data.one_offs.length > 0 && (
            <div className="mt-3 text-[11px] text-[var(--text-secondary)]">
              One-time:{" "}
              {data.one_offs.map((o, i) => (
                <span key={`${o.month}-${o.label}`}>
                  {i > 0 && " · "}
                  {o.label} {o.amount >= 0 ? "+" : ""}{money(o.amount)} ({fmtMonthYear(o.month)})
                </span>
              ))}
            </div>
          )}
          {data.runs_out_age != null && (
            <div className="mt-2 text-[11px]" style={{ color: "var(--red)" }}>
              Savings run out at {Math.floor(data.runs_out_age)}; the table stops there.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
