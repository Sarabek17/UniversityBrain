"use client";

// Payment history of one student. Every row can open its receipt; rows that are
// still `uploaded` get a "Tasdiqlash" button when the viewer may confirm them
// (tutor / dean's office — the backend re-checks that anyway).

import type { PaymentRow } from "@/lib/api";
import { formatAmount, formatDate, paymentStatusLabel } from "@/lib/labels";
import uz from "@/i18n/uz.json";

const STATUS_CLASS: Record<string, string> = {
  automatic: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  uploaded: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  confirmed:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
};

export default function PaymentTable({
  payments,
  onOpenReceipt,
  onConfirm,
  confirmingId = null,
}: {
  payments: PaymentRow[];
  onOpenReceipt: (paymentId: number) => void;
  onConfirm?: (paymentId: number) => void;
  confirmingId?: number | null;
}) {
  if (payments.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {uz.payments.empty}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-[11px] uppercase tracking-wide text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <th className="py-2 pr-3 font-medium">{uz.payments.date}</th>
            <th className="py-2 pr-3 font-medium">{uz.payments.amount}</th>
            <th className="py-2 pr-3 font-medium">
              {uz.payments.receiptNumber}
            </th>
            <th className="py-2 pr-3 font-medium">{uz.payments.status}</th>
            <th className="py-2 font-medium">{uz.payments.actions}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {payments.map((row) => (
            <tr key={row.id}>
              <td className="py-2 pr-3 whitespace-nowrap">
                {formatDate(row.paid_at)}
              </td>
              <td className="py-2 pr-3 whitespace-nowrap font-medium">
                {formatAmount(row.amount)}
              </td>
              <td className="py-2 pr-3 whitespace-nowrap text-gray-600 dark:text-gray-300">
                {row.receipt_number ?? "—"}
              </td>
              <td className="py-2 pr-3">
                <span
                  className={
                    "rounded-full px-2 py-0.5 text-[11px] " +
                    (STATUS_CLASS[row.status] ?? "")
                  }
                >
                  {paymentStatusLabel(row.status)}
                </span>
              </td>
              <td className="py-2">
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => onOpenReceipt(row.id)}
                    className="rounded-md border border-blue-300 px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 dark:border-blue-800 dark:text-blue-300 dark:hover:bg-blue-950"
                  >
                    {uz.payments.openReceipt}
                  </button>
                  {onConfirm && row.status === "uploaded" && (
                    <button
                      type="button"
                      onClick={() => onConfirm(row.id)}
                      disabled={confirmingId === row.id}
                      className="rounded-md border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 dark:hover:bg-emerald-900"
                    >
                      {confirmingId === row.id
                        ? uz.payments.confirming
                        : uz.payments.confirm}
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
