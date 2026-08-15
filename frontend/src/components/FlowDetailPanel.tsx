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
        <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-ink-soft sm:grid-cols-2">
          <div className="flex gap-1">
            <dt className="text-ink-faint">
              {uz.docflow.from}:
            </dt>
            <dd>{detail.sender_name}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-ink-faint">
              {uz.docflow.to}:
            </dt>
            <dd>{detail.recipient_label}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-ink-faint">
              {uz.docflow.created}:
            </dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-ink-faint">
              {uz.docflow.updated}:
            </dt>
            <dd>{formatDateTime(detail.updated_at)}</dd>
          </div>
          {detail.due_date && (
            <div className="flex gap-1">
              <dt className="text-ink-faint">
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
            className="rounded-md border border-line-strong px-2.5 py-1 text-xs hover:bg-raised disabled:opacity-50"
          >
            {summaryLoading ? uz.docflow.summaryLoading : uz.docflow.summary}
          </button>
        </div>
      </header>

      {summaryError && (
        <p className="mt-2 text-xs text-bad">{summaryError}</p>
      )}
      {shownSummary && (
        <section className="mt-3 rounded-lg border border-line bg-raised px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{uz.docflow.summaryTitle}</h3>
            <button
              type="button"
              onClick={onCloseSummary}
              className="text-xs text-ink-faint hover:underline"
            >
              {uz.common.close}
            </button>
          </div>
          <p className="mt-1.5 whitespace-pre-wrap text-sm">
            {shownSummary.summary}
          </p>
          <p className="mt-2 text-[11px] text-ink-soft">
            {uz.docflow.source}: {shownSummary.source.label}
          </p>
          <p className="mt-0.5 text-[11px] italic text-ink-faint">
            {shownSummary.disclaimer}
          </p>
        </section>
      )}

      <section className="mt-3">
        <h3 className="text-sm font-semibold">{uz.docflow.body}</h3>
        <p className="mt-1 whitespace-pre-wrap rounded-lg border border-line px-3 py-2.5 text-sm">
          {detail.body_text}
        </p>
      </section>

      {detail.can_change_status && detail.next_statuses.length > 0 && (
        <section className="mt-3 rounded-lg border border-line px-3 py-2.5">
          <h3 className="text-sm font-semibold">{uz.docflow.actions}</h3>
          <p className="mt-0.5 text-[11px] text-ink-faint">
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
                    ? "bg-ok-solid text-accent-fg hover:bg-ok-solid-hover"
                    : status === "rejected"
                      ? "bg-bad-solid text-accent-fg hover:bg-bad-solid-hover"
                      : "border border-line-strong hover:bg-raised")
                }
              >
                {ACTION_LABELS[status]}
              </button>
            ))}
          </div>

          {active && (
            <div className="mt-3">
              <label className="block text-xs text-ink-soft">
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
                  className="mt-1 w-full rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
                />
              </label>
              {localError && (
                <p className="mt-1 text-xs text-bad">{localError}</p>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={submit}
                  className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
                >
                  {uz.docflow.confirm}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPending(null);
                    setLocalError(null);
                  }}
                  className="rounded-md border border-line-strong px-3 py-1.5 text-xs hover:bg-raised"
                >
                  {uz.docflow.cancel}
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {!detail.can_change_status && detail.is_incoming && (
        <p className="mt-3 text-xs text-ink-faint">
          {uz.docflow.closed}
        </p>
      )}

      {error && <p className="mt-2 text-sm text-bad">{error}</p>}

      <section className="mt-4">
        <h3 className="text-sm font-semibold">{uz.docflow.historyTitle}</h3>
        {detail.history.length === 0 ? (
          <p className="mt-1 text-xs text-ink-faint">{uz.docflow.noHistory}</p>
        ) : (
          <ol className="mt-2 flex flex-col gap-2 border-l border-line pl-3">
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
                  <span className="text-ink-faint">
                    {formatDateTime(item.timestamp)} · {item.changed_by_name}
                  </span>
                </div>
                {item.comment && (
                  <p className="mt-0.5 text-ink-soft">
                    {item.comment}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      <p className="mt-4 text-[11px] text-ink-soft">
        {uz.docflow.source}: {detail.source.label}
      </p>
      <p className="mt-1 text-[11px] italic text-ink-faint">
        {detail.disclaimer}
      </p>
    </div>
  );
}
