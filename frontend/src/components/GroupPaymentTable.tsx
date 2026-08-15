"use client";

// The tutor's answer to "who still owes money?": one row per student, colour by
// state (paid green / partial amber / debtor red), sorted by debt by default.
// Sorting is done here on the already-fetched rows — no extra request.

import type { GroupPaymentRow } from "@/lib/api";
import {
  formatAmount,
  formatDate,
  paymentStateClass,
  paymentStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export type GroupSort = "remaining" | "name" | "group";

export const SORT_OPTIONS: { value: GroupSort; label: string }[] = [
  { value: "remaining", label: uz.payments.sortRemaining },
  { value: "name", label: uz.payments.sortName },
  { value: "group", label: uz.payments.sortGroup },
];

export function sortRows(
  rows: GroupPaymentRow[],
  sort: GroupSort,
): GroupPaymentRow[] {
  const copy = [...rows];
  if (sort === "name") {
    copy.sort((a, b) => a.full_name.localeCompare(b.full_name));
  } else if (sort === "group") {
    copy.sort(
      (a, b) =>
        (a.group_name ?? "").localeCompare(b.group_name ?? "") ||
        a.full_name.localeCompare(b.full_name),
    );
  } else {
    copy.sort(
      (a, b) =>
        b.remaining_amount - a.remaining_amount ||
        a.full_name.localeCompare(b.full_name),
    );
  }
  return copy;
}

export default function GroupPaymentTable({
  rows,
  activeStudentId,
  onSelect,
}: {
  rows: GroupPaymentRow[];
  activeStudentId: number | null;
  onSelect: (studentId: number) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="px-4 py-3 text-sm text-ink-faint">
        {uz.payments.groupEmpty}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
            <th className="py-2 pr-3 font-medium">{uz.payments.student}</th>
            <th className="py-2 pr-3 font-medium">{uz.payments.group}</th>
            <th className="py-2 pr-3 font-medium">{uz.payments.status}</th>
            <th className="py-2 pr-3 font-medium">{uz.payments.paid}</th>
            <th className="py-2 pr-3 font-medium">{uz.payments.remaining}</th>
            <th className="py-2 font-medium">{uz.payments.date}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr
              key={row.student_id}
              className={
                row.student_id === activeStudentId
                  ? "bg-raised"
                  : ""
              }
            >
              <td className="py-1.5 pr-3">
                <button
                  type="button"
                  onClick={() => onSelect(row.student_id)}
                  className="text-left font-medium text-accent-ink hover:underline"
                >
                  {row.full_name}
                </button>
                {row.pending_count > 0 && (
                  <span className="ml-2 rounded-full bg-warn-soft px-1.5 py-0.5 text-[10px] text-warn">
                    {row.pending_count} · {uz.payments.pending}
                  </span>
                )}
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">
                {row.group_name ?? "—"}
              </td>
              <td className="py-1.5 pr-3">
                <span
                  className={
                    "rounded-full px-2 py-0.5 text-[11px] " +
                    paymentStateClass(row.state)
                  }
                >
                  {paymentStateLabel(row.state)}
                </span>
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap">
                {formatAmount(row.paid_amount)}{" "}
                <span className="text-[11px] text-ink-faint">
                  ({row.paid_percent}%)
                </span>
              </td>
              <td
                className={
                  "py-1.5 pr-3 font-medium whitespace-nowrap " +
                  (row.remaining_amount > 0
                    ? "text-bad"
                    : "text-ok")
                }
              >
                {formatAmount(row.remaining_amount)}
              </td>
              <td className="py-1.5 whitespace-nowrap text-ink-soft">
                {row.last_payment_at ? formatDate(row.last_payment_at) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
