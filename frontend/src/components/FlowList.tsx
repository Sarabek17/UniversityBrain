"use client";

// One column of the document flow: the rows of an inbox or an outbox.
// Every row is a <button> (the whole card is clickable, and a real button also
// keeps keyboard users and the CDP smoke test happy).

import type { FlowBox, FlowItem } from "@/lib/api";
import {
  dueClass,
  flowStatusClass,
  flowStatusLabel,
  formatDate,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function FlowList({
  rows,
  box,
  activeId,
  onSelect,
}: {
  rows: FlowItem[];
  box: FlowBox;
  activeId: number | null;
  onSelect: (id: number) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="mt-3 text-sm text-ink-faint">
        {uz.docflow.empty}
      </p>
    );
  }

  return (
    <ul className="mt-3 flex flex-col gap-2">
      {rows.map((row) => {
        const active = row.id === activeId;
        return (
          <li key={row.id}>
            <button
              type="button"
              onClick={() => onSelect(row.id)}
              className={
                "w-full rounded-lg border px-3 py-2.5 text-left transition " +
                (active
                  ? "border-line-strong bg-raised"
                  : row.overdue
                    ? "border-bad-line hover:bg-raised"
                    : "border-line hover:bg-raised")
              }
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium">
                  {row.doc_type_label} №{row.id} — {row.title}
                </span>
                <span
                  className={
                    "shrink-0 rounded-full px-2 py-0.5 text-[11px] " +
                    flowStatusClass(row.status)
                  }
                >
                  {flowStatusLabel(row.status)}
                </span>
              </div>
              <p className="mt-1 text-xs text-ink-soft">
                {box === "inbox"
                  ? `${uz.docflow.from}: ${row.sender_name}`
                  : `${uz.docflow.to}: ${row.recipient_label}`}
                {" · "}
                {formatDate(row.created_at)}
              </p>
              {row.due_date && (
                <p
                  className={
                    "mt-1 text-xs " + dueClass(row.due_in_days, row.overdue)
                  }
                >
                  {uz.docflow.due}: {formatDate(row.due_date)}
                  {row.overdue
                    ? ` — ${uz.docflow.dueOverdue}`
                    : row.due_in_days !== null
                      ? ` (${row.due_in_days} ${uz.docflow.dueDays})`
                      : ""}
                </p>
              )}
              {row.last_comment && (
                <p className="mt-1 line-clamp-2 text-xs italic text-ink-faint">
                  {row.last_comment}
                </p>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
