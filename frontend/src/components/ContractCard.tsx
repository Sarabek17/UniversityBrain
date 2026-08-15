"use client";

// One contract at a glance: total / paid / pending / remaining + a progress bar.
// `pending` is money the student handed in but the tutor has not confirmed yet —
// it is shown separately and deliberately does NOT shrink the remainder.

import type { ContractSummary } from "@/lib/api";
import {
  formatAmount,
  paymentStateClass,
  paymentStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function ContractCard({
  contract,
  compact = false,
}: {
  contract: ContractSummary;
  compact?: boolean;
}) {
  const cells = [
    { label: uz.payments.total, value: contract.total_amount, tone: "" },
    {
      label: uz.payments.paid,
      value: contract.paid_amount,
      tone: "text-ok",
    },
    {
      label: uz.payments.remaining,
      value: contract.remaining_amount,
      tone:
        contract.remaining_amount > 0
          ? "text-bad"
          : "text-ok",
    },
  ];

  return (
    <section className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className={compact ? "text-sm font-semibold" : "text-base font-semibold"}>
            {contract.student_name}
            {contract.group_name ? ` · ${contract.group_name}` : ""}
          </h2>
          <p className="mt-0.5 text-xs text-ink-faint">
            {uz.payments.academicYear}: {contract.academic_year}
          </p>
        </div>
        <span
          className={
            "rounded-full px-2.5 py-1 text-xs font-medium " +
            paymentStateClass(contract.state)
          }
        >
          {paymentStateLabel(contract.state)}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cells.map((cell) => (
          <div key={cell.label}>
            <p className="text-[11px] uppercase tracking-wide text-ink-faint">
              {cell.label}
            </p>
            <p className={"mt-0.5 text-sm font-semibold " + cell.tone}>
              {formatAmount(cell.value)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3">
        <div className="h-2 w-full overflow-hidden rounded-full bg-raised">
          <div
            className="h-full rounded-full bg-ok-solid"
            style={{ width: `${contract.paid_percent}%` }}
          />
        </div>
        <p className="mt-1 text-[11px] text-ink-faint">
          {contract.paid_percent}% {uz.payments.percent}
        </p>
      </div>

      {contract.pending_amount > 0 && (
        <p className="mt-2 rounded-md bg-warn-soft px-2 py-1 text-xs text-warn">
          {uz.payments.pending}: {formatAmount(contract.pending_amount)}
        </p>
      )}

      <p className="mt-3 text-[11px] text-ink-soft">
        {uz.payments.source}: {contract.source.label}
      </p>
      <p className="mt-1 text-[11px] italic text-ink-faint">
        {contract.disclaimer}
      </p>
    </section>
  );
}
