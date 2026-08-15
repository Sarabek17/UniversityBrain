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
        className="relative rounded-md border border-gray-300 px-2.5 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
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
            className="absolute -right-1.5 -top-1.5 min-w-5 rounded-full bg-red-600 px-1 text-xs font-medium text-white"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-2 w-96 max-w-[90vw] rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-700">
            <div>
              <p className="text-sm font-medium">{uz.notifications.title}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {unread} {uz.notifications.unreadCount} ·{" "}
                {data?.total ?? 0} {uz.notifications.totalCount}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setUnreadOnly((value) => !value)}
                className="rounded-md px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {unreadOnly
                  ? uz.notifications.showAll
                  : uz.notifications.unreadOnly}
              </button>
              <button
                type="button"
                onClick={markAll}
                disabled={unread === 0}
                className="rounded-md border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-800"
              >
                {uz.notifications.markAll}
              </button>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {failed && (
              <p className="px-4 py-3 text-sm text-red-600 dark:text-red-400">
                {uz.notifications.loadError}
              </p>
            )}
            {!failed && rows.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
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
                      "w-full border-b border-l-4 border-gray-100 px-4 py-2.5 text-left hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800 " +
                      notificationAccentClass(row.notif_type) +
                      (row.is_read ? " opacity-60" : "")
                    }
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        {notificationTypeLabel(row.notif_type)}
                      </span>
                      <span className="shrink-0 text-xs text-gray-400">
                        {formatDateTime(row.created_at)}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm">
                      {!row.is_read && (
                        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-blue-600 align-middle" />
                      )}
                      {row.text}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <p className="border-t border-gray-200 px-4 py-2 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {uz.notifications.hint}
          </p>
        </div>
      )}
    </div>
  );
}
