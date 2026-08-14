"use client";

// Student's "Kontrakt" page (S8): the contract card, the payment history, the
// receipt viewer and — for the case where the payment never arrived
// automatically — a receipt form the tutor confirms later.

import { useEffect, useState } from "react";
import { ApiError, paymentsApi, type ContractSummary } from "@/lib/api";
import ContractCard from "@/components/ContractCard";
import PaymentTable from "@/components/PaymentTable";
import ReceiptPanel from "@/components/ReceiptPanel";
import ReceiptUploadForm from "@/components/ReceiptUploadForm";
import uz from "@/i18n/uz.json";

export default function ContractPage() {
  const [contract, setContract] = useState<ContractSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receiptId, setReceiptId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    paymentsApi
      .contract()
      .then((data) => {
        if (!cancelled) setContract(data);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof ApiError && e.status === 404
            ? uz.payments.noContract
            : uz.payments.loadError,
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-5">
        <h1 className="text-lg font-semibold">{uz.payments.contractTitle}</h1>

        {!contract && !error && (
          <p className="text-sm text-gray-500">{uz.common.loading}</p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {contract && (
          <>
            <ContractCard contract={contract} />

            <section className="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
              <h2 className="mb-2 text-sm font-semibold">
                {uz.payments.historyTitle}
              </h2>
              <PaymentTable
                payments={contract.payments}
                onOpenReceipt={(id) => setReceiptId(id)}
              />
            </section>

            <ReceiptUploadForm onUploaded={(fresh) => setContract(fresh)} />
          </>
        )}
      </div>

      {receiptId !== null && (
        <ReceiptPanel
          paymentId={receiptId}
          onClose={() => setReceiptId(null)}
        />
      )}
    </div>
  );
}
