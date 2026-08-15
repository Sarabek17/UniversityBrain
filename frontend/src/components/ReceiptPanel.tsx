"use client";

// Receipt viewer (modal). The demo data has receipt *numbers* but no receipt
// *files*, so this shows the payment record itself, laid out like a receipt,
// and says where it came from. It never fails over a missing image.
//
// State is derived by payment id (Next 16 forbids a synchronous setState in an
// effect), exactly like DocumentPanel does it.

import { useEffect, useState } from "react";
import { paymentsApi, type Receipt } from "@/lib/api";
import { formatAmount, formatDateTime, paymentStatusLabel } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function ReceiptPanel({
  paymentId,
  onClose,
}: {
  paymentId: number;
  onClose: () => void;
}) {
  const [loaded, setLoaded] = useState<{ id: number; data: Receipt } | null>(
    null,
  );
  const [failed, setFailed] = useState<{ id: number; message: string } | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    paymentsApi
      .receipt(paymentId)
      .then((data) => {
        if (!cancelled) setLoaded({ id: paymentId, data });
      })
      .catch(() => {
        if (!cancelled)
          setFailed({ id: paymentId, message: uz.payments.receiptLoadError });
      });
    return () => {
      cancelled = true;
    };
  }, [paymentId]);

  const receipt = loaded !== null && loaded.id === paymentId ? loaded.data : null;
  const error = failed !== null && failed.id === paymentId ? failed.message : null;

  const rows = receipt
    ? [
        { label: uz.payments.receiptStudent, value: receipt.student_name },
        {
          label: uz.payments.receiptNumber,
          value: receipt.receipt_number ?? "—",
        },
        { label: uz.payments.amount, value: formatAmount(receipt.amount) },
        { label: uz.payments.date, value: formatDateTime(receipt.paid_at) },
        {
          label: uz.payments.status,
          value: paymentStatusLabel(receipt.status),
        },
        { label: uz.payments.receiptMethod, value: receipt.method },
        { label: uz.payments.receiptYear, value: receipt.academic_year },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-surface max-h-full w-full max-w-md overflow-y-auto rounded-xl border border-line p-4 shadow-xl">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold">{uz.payments.receiptTitle}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-line-strong px-2 py-1 text-xs hover:bg-raised"
          >
            {uz.common.close}
          </button>
        </div>

        {!receipt && !error && (
          <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
        )}
        {error && <p className="mt-3 text-sm text-bad">{error}</p>}

        {receipt && (
          <>
            <dl className="mt-3 divide-y divide-dashed divide-line text-sm">
              {rows.map((row) => (
                <div
                  key={row.label}
                  className="flex items-start justify-between gap-3 py-1.5"
                >
                  <dt className="text-xs text-ink-faint">
                    {row.label}
                  </dt>
                  <dd className="text-right font-medium">{row.value}</dd>
                </div>
              ))}
            </dl>
            {!receipt.file_available && (
              <p className="mt-3 rounded-md bg-warn-soft px-2 py-1.5 text-[11px] text-warn">
                {receipt.note}
              </p>
            )}
            <p className="mt-2 text-[11px] text-ink-soft">
              {uz.payments.source}: {receipt.source.label}
            </p>
            <p className="mt-1 text-[11px] italic text-ink-faint">
              {receipt.disclaimer}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
