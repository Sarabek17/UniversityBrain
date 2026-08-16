"use client";

// "The payment did not arrive automatically" case: the student types the amount
// and the receipt number, the tutor confirms it later. No file upload — the demo
// stores no files, and the receipt record is what the tutor actually checks.

import { useState } from "react";
import { errorDetail, paymentsApi, type ContractSummary } from "@/lib/api";
import { formatAmount } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function ReceiptUploadForm({
  onUploaded,
  remaining,
}: {
  onUploaded: (contract: ContractSummary) => void;
  /** Contract remainder — shown as a hint so the demo never types too much. */
  remaining?: number;
}) {
  const [amount, setAmount] = useState("");
  const [receiptNumber, setReceiptNumber] = useState("");
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const value = Number(amount.replace(/\s/g, ""));
    if (!Number.isFinite(value) || value <= 0) {
      setError(uz.payments.uploadInvalid);
      setMessage(null);
      return;
    }
    setSending(true);
    setError(null);
    setMessage(null);
    paymentsApi
      .uploadReceipt(value, receiptNumber)
      .then((contract) => {
        setMessage(uz.payments.uploadSuccess);
        setAmount("");
        setReceiptNumber("");
        onUploaded(contract);
      })
      .catch((e: unknown) => {
        setError(errorDetail(e) ?? uz.payments.uploadError);
      })
      .finally(() => setSending(false));
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-dashed border-line-strong p-4"
    >
      <h3 className="text-sm font-semibold">{uz.payments.uploadTitle}</h3>
      <p className="mt-1 text-xs text-ink-faint">
        {uz.payments.uploadHint}
        {remaining !== undefined && remaining > 0 && (
          <>
            {" "}
            <span className="font-medium text-ink-soft">
              {uz.payments.remaining}: {formatAmount(remaining)}
            </span>
          </>
        )}
      </p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs text-ink-soft">
          {uz.payments.uploadAmount}
          <input
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            inputMode="numeric"
            className="mt-1 w-40 rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col text-xs text-ink-soft">
          {uz.payments.uploadReceiptNumber}
          <input
            value={receiptNumber}
            onChange={(event) => setReceiptNumber(event.target.value)}
            placeholder="CHK-123456"
            className="mt-1 w-44 rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={sending}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-raised disabled:text-ink-faint"
        >
          {sending ? uz.payments.uploadSubmitting : uz.payments.uploadSubmit}
        </button>
      </div>
      {message && (
        <p className="mt-2 text-xs text-ok">
          {message}
        </p>
      )}
      {error && <p className="mt-2 text-xs text-bad">{error}</p>}
    </form>
  );
}
