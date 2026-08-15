"use client";

// One document of the flow: who sent it to whom, the body, the whole status
// history and — for the recipient only — the decision buttons.
//
// `can_change_status` / `next_statuses` come from the backend, so the buttons
// mirror the server's rules instead of guessing them from the role: an approved
// document offers nothing, and a rejection asks for its reason before it is
// sent (the backend refuses it otherwise with 422).

import { useState } from "react";
import type { FlowDetail, FlowStatus, FlowSummary } from "@/lib/api";
import {
  dueClass,
  flowStatusClass,
  flowStatusLabel,
  formatDate,
  formatDateTime,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

const ACTION_LABELS: Record<FlowStatus, string> = {
  sent: uz.docflow.statuses.sent,
  seen: uz.docflow.markSeen,
  in_progress: uz.docflow.markInProgress,
  approved: uz.docflow.approve,
  rejected: uz.docflow.reject,
};

// Which steps open a comment box first: a rejection must carry a reason, an
// approval may carry one ("204-xonadan olib keting").
const COMMENTED: FlowStatus[] = ["approved", "rejected"];

export default function FlowDetailPanel({
  detail,
  busy,
  error,
  onChangeStatus,
  onSummarize,
  summary,
  summaryLoading,
  summaryError,
  onCloseSummary,
}: {
  detail: FlowDetail;
  busy: boolean;
  error: string | null;
  onChangeStatus: (status: FlowStatus, comment: string | null) => void;
  onSummarize: () => void;
  summary: FlowSummary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  onCloseSummary: () => void;
}) {
  // Kept per document id, so switching rows resets the form by derivation
  // instead of by an effect (Next 16 `react-hooks/set-state-in-effect`).
  const [pending, setPending] = useState<{
    flowId: number;
    status: FlowStatus;
    comment: string;
  } | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const active = pending && pending.flowId === detail.id ? pending : null;
  const shownSummary = summary && summary.flow_id === detail.id ? summary : null;

  function start(status: FlowStatus) {
    setLocalError(null);
    if (COMMENTED.includes(status)) {
      setPending({ flowId: detail.id, status, comment: "" });
      return;
    }
    onChangeStatus(status, null);
  }

  function submit() {
    if (!active) return;
    const comment = active.comment.trim();
    if (active.status === "rejected" && !comment) {
      setLocalError(uz.docflow.reasonRequired);
      return;
    }
    setPending(null);
    onChangeStatus(active.status, comment || null);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <header>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">
            {detail.doc_type_label} №{detail.id} — {detail.title}
          </h2>
          <span
            className={
              "rounded-full px-2.5 py-0.5 text-xs " +
              flowStatusClass(detail.status)
            }
          >
            {flowStatusLabel(detail.status)}
          </span>
        </div>
        <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-gray-600 sm:grid-cols-2 dark:text-gray-300">
          <div className="flex gap-1">
            <dt className="text-gray-500 dark:text-gray-400">
              {uz.docflow.from}:
            </dt>
            <dd>{detail.sender_name}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-gray-500 dark:text-gray-400">
              {uz.docflow.to}:
            </dt>
            <dd>{detail.recipient_label}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-gray-500 dark:text-gray-400">
              {uz.docflow.created}:
            </dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-gray-500 dark:text-gray-400">
              {uz.docflow.updated}:
            </dt>
            <dd>{formatDateTime(detail.updated_at)}</dd>
          </div>
          {detail.due_date && (
            <div className="flex gap-1">
              <dt className="text-gray-500 dark:text-gray-400">
                {uz.docflow.due}:
              </dt>
              <dd className={dueClass(detail.due_in_days, detail.overdue)}>
                {formatDate(detail.due_date)}
                {detail.overdue
                  ? ` — ${uz.docflow.dueOverdue}`
                  : detail.due_in_days !== null
                    ? ` (${detail.due_in_days} ${uz.docflow.dueDays})`
                    : ""}
              </dd>
            </div>
          )}
        </dl>
        <div className="mt-2">
          <button
            type="button"
            onClick={onSummarize}
            disabled={summaryLoading}
            className="rounded-md border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {summaryLoading ? uz.docflow.summaryLoading : uz.docflow.summary}
          </button>
        </div>
      </header>

      {summaryError && (
        <p className="mt-2 text-xs text-red-600">{summaryError}</p>
      )}
      {shownSummary && (
        <section className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 dark:border-gray-700 dark:bg-gray-900">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{uz.docflow.summaryTitle}</h3>
            <button
              type="button"
              onClick={onCloseSummary}
              className="text-xs text-gray-500 hover:underline dark:text-gray-400"
            >
              {uz.common.close}
            </button>
          </div>
          <p className="mt-1.5 whitespace-pre-wrap text-sm">
            {shownSummary.summary}
          </p>
          <p className="mt-2 text-[11px] text-gray-600 dark:text-gray-300">
            {uz.docflow.source}: {shownSummary.source.label}
          </p>
          <p className="mt-0.5 text-[11px] italic text-gray-500 dark:text-gray-400">
            {shownSummary.disclaimer}
          </p>
        </section>
      )}

      <section className="mt-3">
        <h3 className="text-sm font-semibold">{uz.docflow.body}</h3>
        <p className="mt-1 whitespace-pre-wrap rounded-lg border border-gray-200 px-3 py-2.5 text-sm dark:border-gray-700">
          {detail.body_text}
        </p>
      </section>

      {detail.can_change_status && detail.next_statuses.length > 0 && (
        <section className="mt-3 rounded-lg border border-gray-200 px-3 py-2.5 dark:border-gray-700">
          <h3 className="text-sm font-semibold">{uz.docflow.actions}</h3>
          <p className="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
            {uz.docflow.actionHint}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {detail.next_statuses.map((status) => (
              <button
                key={status}
                type="button"
                disabled={busy}
                onClick={() => start(status)}
                className={
                  "rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50 " +
                  (status === "approved"
                    ? "bg-emerald-600 text-white hover:bg-emerald-700"
                    : status === "rejected"
                      ? "bg-red-600 text-white hover:bg-red-700"
                      : "border border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800")
                }
              >
                {ACTION_LABELS[status]}
              </button>
            ))}
          </div>

          {active && (
            <div className="mt-3">
              <label className="block text-xs text-gray-600 dark:text-gray-300">
                {active.status === "rejected"
                  ? uz.docflow.reasonLabel
                  : uz.docflow.commentLabel}
                <textarea
                  value={active.comment}
                  rows={3}
                  onChange={(event) =>
                    setPending({
                      flowId: detail.id,
                      status: active.status,
                      comment: event.target.value,
                    })
                  }
                  className="mt-1 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1.5 text-sm dark:border-gray-600"
                />
              </label>
              {localError && (
                <p className="mt-1 text-xs text-red-600">{localError}</p>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={submit}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {uz.docflow.confirm}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPending(null);
                    setLocalError(null);
                  }}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
                >
                  {uz.docflow.cancel}
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {!detail.can_change_status && detail.is_incoming && (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          {uz.docflow.closed}
        </p>
      )}

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      <section className="mt-4">
        <h3 className="text-sm font-semibold">{uz.docflow.historyTitle}</h3>
        {detail.history.length === 0 ? (
          <p className="mt-1 text-xs text-gray-500">{uz.docflow.noHistory}</p>
        ) : (
          <ol className="mt-2 flex flex-col gap-2 border-l border-gray-200 pl-3 dark:border-gray-700">
            {detail.history.map((item) => (
              <li key={item.id} className="text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={
                      "rounded-full px-2 py-0.5 " + flowStatusClass(item.status)
                    }
                  >
                    {flowStatusLabel(item.status)}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">
                    {formatDateTime(item.timestamp)} · {item.changed_by_name}
                  </span>
                </div>
                {item.comment && (
                  <p className="mt-0.5 text-gray-700 dark:text-gray-200">
                    {item.comment}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      <p className="mt-4 text-[11px] text-gray-600 dark:text-gray-300">
        {uz.docflow.source}: {detail.source.label}
      </p>
      <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
        {detail.disclaimer}
      </p>
    </div>
  );
}
