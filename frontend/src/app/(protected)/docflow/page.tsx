"use client";

// "Arizalar" — the document flow, one route and three questions:
//
//   student  -> "where is my application?" (outbox + a new one from a template)
//   teacher  -> hands in reports, and reads the orders addressed to them
//   staff    -> the inbox of the faculty: sort by newest or by deadline, open a
//               document, summarize it and decide (ko'rildi / ijroda /
//               tasdiqlash / rad etish + sabab)
//
// Which buttons appear is never guessed from the role: `can_change_status` and
// `next_statuses` come from the backend, which is also the only place the rules
// are enforced (domain rule 2).

import { useCallback, useEffect, useState } from "react";
import {
  docflowApi,
  errorDetail,
  type FlowBox,
  type FlowCreateInput,
  type FlowDetail,
  type FlowList as FlowListOut,
  type FlowRecipient,
  type FlowSort,
  type FlowStatus,
  type FlowSummary,
  type FlowTemplate,
  type UserRole,
} from "@/lib/api";
import FlowComposer from "@/components/FlowComposer";
import FlowDetailPanel from "@/components/FlowDetailPanel";
import FlowList from "@/components/FlowList";
import { useAuth } from "@/lib/auth";
import uz from "@/i18n/uz.json";

const SORT_OPTIONS: { value: FlowSort; label: string }[] = [
  { value: "new", label: uz.docflow.sortNew },
  { value: "due", label: uz.docflow.sortDue },
];

function titleFor(role: UserRole): string {
  if (role === "student") return uz.docflow.titleStudent;
  if (role === "teacher") return uz.docflow.titleTeacher;
  return uz.docflow.titleStaff;
}

function defaultBox(role: UserRole): FlowBox {
  return role === "student" || role === "teacher" ? "outbox" : "inbox";
}

export default function DocflowPage() {
  const { user } = useAuth();
  if (!user) return null;
  return <Workspace role={user.role} />;
}

function Workspace({ role }: { role: UserRole }) {
  const [box, setBox] = useState<FlowBox>(defaultBox(role));
  const [sort, setSort] = useState<FlowSort>("new");
  const [listing, setListing] = useState<FlowListOut | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<FlowDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [statusBusy, setStatusBusy] = useState(false);

  const [composing, setComposing] = useState(false);
  const [templates, setTemplates] = useState<FlowTemplate[]>([]);
  const [recipients, setRecipients] = useState<FlowRecipient[]>([]);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const [summary, setSummary] = useState<FlowSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      docflowApi
        .list(box, sort)
        .then((data) => {
          setListing(data);
          setListError(null);
        })
        .catch(() => setListError(uz.docflow.loadError)),
    [box, sort],
  );

  useEffect(() => {
    void load();
  }, [load]);

  // Derived, not reset by an effect: the panel shows the loaded document only
  // while it is the selected one (Next 16 `react-hooks/set-state-in-effect`).
  const shownDetail = detail && detail.id === selectedId ? detail : null;
  const showTabs = role !== "student";

  function openFlow(id: number) {
    setSelectedId(id);
    setComposing(false);
    setDetailError(null);
    setSummaryError(null);
    setSent(false);
    docflowApi
      .get(id)
      .then((data) => setDetail(data))
      .catch((e: unknown) =>
        setDetailError(errorDetail(e) ?? uz.docflow.detailError),
      );
  }

  function startCompose() {
    setComposing(true);
    setSelectedId(null);
    setSendError(null);
    setSent(false);
    docflowApi
      .templates()
      .then((data) => setTemplates(data))
      .catch(() => setSendError(uz.docflow.loadError));
    docflowApi
      .recipients()
      .then((data) => setRecipients(data))
      .catch(() => setRecipients([]));
  }

  function submitNew(input: FlowCreateInput) {
    setSending(true);
    setSendError(null);
    docflowApi
      .create(input)
      .then((created) => {
        setDetail(created);
        setSelectedId(created.id);
        setComposing(false);
        setSent(true);
        setBox("outbox"); // the fresh document lives in "Yuborilganlar"
        return load();
      })
      .catch((e: unknown) => setSendError(errorDetail(e) ?? uz.docflow.sendError))
      .finally(() => setSending(false));
  }

  function changeStatus(status: FlowStatus, comment: string | null) {
    if (selectedId === null) return;
    setStatusBusy(true);
    setDetailError(null);
    docflowApi
      .changeStatus(selectedId, status, comment)
      .then((fresh) => {
        setDetail(fresh);
        return load();
      })
      .catch((e: unknown) =>
        setDetailError(errorDetail(e) ?? uz.docflow.statusError),
      )
      .finally(() => setStatusBusy(false));
  }

  function summarize() {
    if (selectedId === null) return;
    setSummaryLoading(true);
    setSummaryError(null);
    docflowApi
      .summary(selectedId)
      .then((data) => setSummary(data))
      .catch((e: unknown) =>
        setSummaryError(errorDetail(e) ?? uz.docflow.summaryError),
      )
      .finally(() => setSummaryLoading(false));
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col md:flex-row">
      <section className="flex max-h-[45vh] min-h-0 w-full shrink-0 flex-col overflow-y-auto border-b border-line bg-sidebar px-4 py-5 md:max-h-none md:w-96 md:border-b-0 md:border-r">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-lg font-semibold">{titleFor(role)}</h1>
          <button
            type="button"
            onClick={startCompose}
            className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-fg hover:bg-accent-hover"
          >
            {role === "student" ? uz.docflow.newStudent : uz.docflow.new}
          </button>
        </div>

        {showTabs && (
          <div className="mt-3 flex gap-1">
            {(["inbox", "outbox"] as FlowBox[]).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setBox(value)}
                className={
                  "rounded-md px-3 py-1.5 text-xs " +
                  (box === value
                    ? "bg-raised font-medium text-ink"
                    : "text-ink-soft hover:bg-raised")
                }
              >
                {value === "inbox" ? uz.docflow.inbox : uz.docflow.outbox}
              </button>
            ))}
          </div>
        )}

        {listing && (
          <>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
              <span className="rounded-full bg-raised px-2.5 py-1 text-ink-soft">
                {uz.docflow.open}: {listing.open_count}
              </span>
              {box === "inbox" && (
                <span className="rounded-full bg-accent-soft px-2.5 py-1 text-accent-ink">
                  {uz.docflow.fresh}: {listing.new_count}
                </span>
              )}
              {listing.due_soon_count > 0 && (
                <span className="rounded-full bg-warn-soft px-2.5 py-1 text-warn">
                  {uz.docflow.dueSoon}: {listing.due_soon_count}
                </span>
              )}
              {listing.overdue_count > 0 && (
                <span className="rounded-full bg-bad-soft px-2.5 py-1 text-bad">
                  {uz.docflow.overdue}: {listing.overdue_count}
                </span>
              )}
            </div>

            <label className="mt-3 flex items-center gap-2 text-xs text-ink-soft">
              {uz.docflow.sortBy}
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as FlowSort)}
                className="rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}

        {!listing && !listError && (
          <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
        )}
        {listError && <p className="mt-3 text-sm text-bad">{listError}</p>}

        {listing && (
          <FlowList
            rows={listing.rows}
            box={listing.box}
            activeId={selectedId}
            onSelect={openFlow}
          />
        )}
      </section>

      <section className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 py-5">
        {composing ? (
          <FlowComposer
            templates={templates}
            recipients={recipients}
            sending={sending}
            error={sendError}
            onSubmit={submitNew}
            onCancel={() => setComposing(false)}
          />
        ) : shownDetail ? (
          <>
            {sent && (
              <p className="mb-2 rounded-md bg-ok-soft px-3 py-1.5 text-xs text-ok">
                {uz.docflow.sendSuccess}
              </p>
            )}
            <FlowDetailPanel
              detail={shownDetail}
              busy={statusBusy}
              error={detailError}
              onChangeStatus={changeStatus}
              onSummarize={summarize}
              summary={summary}
              summaryLoading={summaryLoading}
              summaryError={summaryError}
              onCloseSummary={() => setSummary(null)}
            />
          </>
        ) : (
          <div>
            {detailError && (
              <p className="mb-2 text-sm text-bad">{detailError}</p>
            )}
            <p className="text-sm text-ink-faint">
              {uz.docflow.selectHint}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
