"use client";

// The bell (S12): one counter for every module event.
//
// The backend answers the page **and** `unread_count` in a single request, so
// the badge never costs a second call. Clicking a row marks it read and opens
// the page its `link_type` points at (the table lives in `lib/labels.ts`).
//
// Next 16 rule (`react-hooks/set-state-in-effect`): no synchronous setState in
// an effect — every update below happens inside `.then()` or an event handler.

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  notificationsApi,
  type NotificationItem,
  type NotificationList,
  type UserRole,
} from "@/lib/api";
import {
  formatDateTime,
  notificationAccentClass,
  notificationHref,
  notificationTypeLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

// In-app polling is enough for the hackathon (FUNKSIONALLIK 3.10: real
// push/SMS is a documented extension).
const POLL_MS = 60_000;

export default function NotifBell({ role }: { role: UserRole }) {
  const router = useRouter();
  const [data, setData] = useState<NotificationList | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      notificationsApi
        .list()
        .then((body) => {
          if (!cancelled) {
            setData(body);
            setFailed(false);
          }
        })
        .catch(() => {
          if (!cancelled) setFailed(true);
        });
    };
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const unread = data?.unread_count ?? 0;
  const rows = data
    ? unreadOnly
      ? data.rows.filter((row) => !row.is_read)
      : data.rows
    : [];

  const openItem = (item: NotificationItem) => {
    const href = notificationHref(item.link_type, role);
    if (!item.is_read) {
      notificationsApi
        .read(item.id)
        .then(setData)
        .catch(() => setFailed(true));
    }
    setOpen(false);
    if (href) router.push(href);
  };

  const markAll = () => {
    notificationsApi
      .readAll()
      .then(setData)
      .catch(() => setFailed(true));
  };

  return (
    <div className="relative" ref={boxRef}>
      <button
        type="button"
        aria-label={uz.notifications.open}
        onClick={() => setOpen((value) => !value)}
        className="relative rounded-md border border-line-strong px-2.5 py-1.5 text-sm hover:bg-raised"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
          aria-hidden="true"
        >
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {unread > 0 && (
          <span
            data-testid="notif-count"
            className="absolute -right-1.5 -top-1.5 min-w-5 rounded-full bg-bad-solid px-1 text-xs font-medium text-accent-fg"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[26rem] max-w-[90vw] rounded-lg border border-line bg-surface shadow-lg">
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2">
            <div className="min-w-0">
              <p className="text-sm font-medium">{uz.notifications.title}</p>
              <p className="text-xs text-ink-faint">
                {unread} {uz.notifications.unreadCount} ·{" "}
                {data?.total ?? 0} {uz.notifications.totalCount}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2 whitespace-nowrap">
              <button
                type="button"
                onClick={() => setUnreadOnly((value) => !value)}
                className="rounded-md px-2 py-1 text-xs text-ink-soft hover:bg-raised"
              >
                {unreadOnly
                  ? uz.notifications.showAll
                  : uz.notifications.unreadOnly}
              </button>
              <button
                type="button"
                onClick={markAll}
                disabled={unread === 0}
                className="rounded-md border border-line-strong px-2 py-1 text-xs hover:bg-raised disabled:opacity-40"
              >
                {uz.notifications.markAll}
              </button>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {failed && (
              <p className="px-4 py-3 text-sm text-bad">
                {uz.notifications.loadError}
              </p>
            )}
            {!failed && rows.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-ink-faint">
                {unreadOnly
                  ? uz.notifications.empty
                  : uz.notifications.emptyAll}
              </p>
            )}
            <ul>
              {rows.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    onClick={() => openItem(row)}
                    className={
                      "w-full border-b border-l-4 border-line px-4 py-2.5 text-left hover:bg-raised " +
                      notificationAccentClass(row.notif_type) +
                      (row.is_read ? " opacity-60" : "")
                    }
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-ink-soft">
                        {notificationTypeLabel(row.notif_type)}
                      </span>
                      <span className="shrink-0 text-xs text-ink-faint">
                        {formatDateTime(row.created_at)}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm">
                      {!row.is_read && (
                        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-accent align-middle" />
                      )}
                      {row.text}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <p className="border-t border-line px-4 py-2 text-xs text-ink-faint">
            {uz.notifications.hint}
          </p>
        </div>
      )}
    </div>
  );
}
