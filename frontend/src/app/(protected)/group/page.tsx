"use client";

// Tutor / dean's office "Guruh" page (S8): the payment summary of every student
// in scope. Picking a student opens their contract on the right, where an
// `uploaded` receipt can be confirmed in one click — the tutor never has to ask
// anyone for a photo of a receipt again.

import { useCallback, useEffect, useState } from "react";
import {
  errorDetail,
  paymentsApi,
  type ContractSummary,
  type GroupPaymentSummary,
} from "@/lib/api";
import ContractCard from "@/components/ContractCard";
import GroupPaymentTable, {
  SORT_OPTIONS,
  sortRows,
  type GroupSort,
} from "@/components/GroupPaymentTable";
import PaymentTable from "@/components/PaymentTable";
import ReceiptPanel from "@/components/ReceiptPanel";
import { formatAmount } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function GroupPage() {
  const [summary, setSummary] = useState<GroupPaymentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<GroupSort>("remaining");

  const [selected, setSelected] = useState<ContractSummary | null>(null);
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [loadingStudentId, setLoadingStudentId] = useState<number | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [receiptId, setReceiptId] = useState<number | null>(null);

  const load = useCallback(
    () =>
      paymentsApi
        .group()
        .then((data) => {
          setSummary(data);
          setError(null);
        })
        .catch(() => setError(uz.payments.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  function selectStudent(studentId: number) {
    setLoadingStudentId(studentId);
    setSelectedError(null);
    paymentsApi
      .studentContract(studentId)
      .then((data) => setSelected(data))
      .catch((e: unknown) =>
        setSelectedError(errorDetail(e) ?? uz.payments.noAccess),
      )
      .finally(() => setLoadingStudentId(null));
  }

  function confirmReceipt(paymentId: number) {
    setConfirmingId(paymentId);
    setSelectedError(null);
    paymentsApi
      .confirm(paymentId)
      .then((fresh) => {
        setSelected(fresh);
        return load();
      })
      .catch((e: unknown) =>
        setSelectedError(errorDetail(e) ?? uz.payments.confirmError),
      )
      .finally(() => setConfirmingId(null));
  }

  const rows = summary ? sortRows(summary.rows, sort) : [];

  return (
    <div className="flex min-h-0 flex-1">
      <section className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-lg font-semibold">{uz.payments.groupTitle}</h1>
            {summary && (
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {summary.group_names.join(", ")} · {summary.rows.length}{" "}
                {uz.payments.student.toLowerCase()}
              </p>
            )}
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
            {uz.payments.sortBy}
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as GroupSort)}
              className="rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {!summary && !error && (
          <p className="mt-3 text-sm text-gray-500">{uz.common.loading}</p>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        {summary && (
          <>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                {uz.payments.states.paid}: {summary.paid_count}
              </span>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                {uz.payments.states.partial}: {summary.partial_count}
              </span>
              <span className="rounded-full bg-red-100 px-2.5 py-1 text-red-800 dark:bg-red-950 dark:text-red-200">
                {uz.payments.states.debtor}: {summary.debtor_count}
              </span>
              {summary.pending_count > 0 && (
                <span className="rounded-full border border-amber-300 px-2.5 py-1 text-amber-800 dark:border-amber-800 dark:text-amber-200">
                  {summary.pending_count} {uz.payments.groupPending}
                </span>
              )}
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {uz.payments.groupDebtTotal}:{" "}
                {formatAmount(summary.remaining_amount)}
              </span>
            </div>

            <div className="mt-3">
              <GroupPaymentTable
                rows={rows}
                activeStudentId={selected?.student_id ?? null}
                onSelect={selectStudent}
              />
            </div>

            <p className="mt-3 text-[11px] text-gray-600 dark:text-gray-300">
              {uz.payments.source}: {summary.source.label}
            </p>
            <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
              {summary.disclaimer}
            </p>
          </>
        )}
      </section>

      <aside className="hidden w-96 shrink-0 flex-col overflow-y-auto border-l border-gray-200 px-4 py-5 lg:flex dark:border-gray-700">
        {loadingStudentId !== null && (
          <p className="text-sm text-gray-500">{uz.common.loading}</p>
        )}
        {selectedError && (
          <p className="mb-2 text-sm text-red-600">{selectedError}</p>
        )}
        {selected ? (
          <>
            <ContractCard contract={selected} compact />
            <section className="mt-3">
              <h2 className="mb-2 text-sm font-semibold">
                {uz.payments.historyTitle}
              </h2>
              <PaymentTable
                payments={selected.payments}
                onOpenReceipt={(id) => setReceiptId(id)}
                onConfirm={confirmReceipt}
                confirmingId={confirmingId}
              />
            </section>
          </>
        ) : (
          loadingStudentId === null && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {uz.payments.selectStudentHint}
            </p>
          )
        )}
      </aside>

      {receiptId !== null && (
        <ReceiptPanel
          paymentId={receiptId}
          onClose={() => setReceiptId(null)}
        />
      )}
    </div>
  );
}
