"use client";

// "The payment did not arrive automatically" case: the student types the amount
// and the receipt number, the tutor confirms it later. No file upload — the demo
// stores no files, and the receipt record is what the tutor actually checks.

import { useState } from "react";
import { errorDetail, paymentsApi, type ContractSummary } from "@/lib/api";
import uz from "@/i18n/uz.json";

export default function ReceiptUploadForm({
  onUploaded,
}: {
  onUploaded: (contract: ContractSummary) => void;
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
      className="rounded-xl border border-dashed border-gray-300 p-4 dark:border-gray-600"
    >
      <h3 className="text-sm font-semibold">{uz.payments.uploadTitle}</h3>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
        {uz.payments.uploadHint}
      </p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs text-gray-600 dark:text-gray-300">
          {uz.payments.uploadAmount}
          <input
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            inputMode="numeric"
            className="mt-1 w-40 rounded-md border border-gray-300 bg-transparent px-2 py-1.5 text-sm dark:border-gray-600"
          />
        </label>
        <label className="flex flex-col text-xs text-gray-600 dark:text-gray-300">
          {uz.payments.uploadReceiptNumber}
          <input
            value={receiptNumber}
            onChange={(event) => setReceiptNumber(event.target.value)}
            placeholder="CHK-123456"
            className="mt-1 w-44 rounded-md border border-gray-300 bg-transparent px-2 py-1.5 text-sm dark:border-gray-600"
          />
        </label>
        <button
          type="submit"
          disabled={sending}
          className="rounded-md border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-800 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200 dark:hover:bg-blue-900"
        >
          {sending ? uz.payments.uploadSubmitting : uz.payments.uploadSubmit}
        </button>
      </div>
      {message && (
        <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
          {message}
        </p>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </form>
  );
}
