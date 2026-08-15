"use client";

// Demo reset (S13): one button before the presentation. The backend runs the
// two seed steps in a background task (~15-30 s), this panel polls the status
// and logs out when it finishes — the reset re-creates user ids, so every
// token issued before it is meaningless afterwards.

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, adminApi, errorDetail, type AdminReset } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/labels";
import uz from "@/i18n/uz.json";

const POLL_MS = 1500;
const MAX_POLLS = 80; // 2 minutes is far beyond the measured 15-30 s
// While the seed re-creates the users table the status endpoint answers
// 401/403 for a second or two. That is the reset working, not a failure — the
// token starts working again as soon as the accounts are back.
const MAX_AUTH_FAILURES = 20;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export default function AdminResetPanel() {
  const { logout } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<AdminReset | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function poll(): Promise<AdminReset | null> {
    let authFailures = 0;
    for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
      await wait(POLL_MS);
      let status: AdminReset;
      try {
        status = await adminApi.resetStatus();
      } catch (e: unknown) {
        // The accounts are being re-created right now: keep waiting.
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
          authFailures += 1;
          if (authFailures >= MAX_AUTH_FAILURES) return null;
          continue;
        }
        throw e;
      }
      setState(status);
      if (!status.running) return status;
    }
    return null;
  }

  function start() {
    if (typeof window !== "undefined" && !window.confirm(uz.admin.resetConfirm)) {
      return;
    }
    setBusy(true);
    setError(null);
    setDone(false);
    adminApi
      .reset()
      .then((started) => {
        setState(started);
        return poll();
      })
      .then((final) => {
        setBusy(false);
        if (final && final.ok === false) {
          setError(final.message);
          return;
        }
        setDone(true);
        // Give the operator a second to read the result, then start over.
        setTimeout(() => {
          logout();
          router.replace("/login");
        }, 1500);
      })
      .catch((e: unknown) => {
        setBusy(false);
        setError(errorDetail(e) ?? uz.admin.resetError);
      });
  }

  return (
    <section className="rounded-lg border border-warn-line p-4">
      <h2 className="text-sm font-semibold">{uz.admin.resetTitle}</h2>
      <p className="mt-0.5 text-[11px] text-ink-soft">
        {uz.admin.resetHint}
      </p>
      <p className="mt-1 text-[11px] text-warn">
        {uz.admin.resetWarning}
      </p>

      <button
        type="button"
        onClick={start}
        disabled={busy}
        className="mt-3 rounded-md bg-warn-solid px-3 py-1.5 text-xs font-medium text-accent-fg hover:bg-warn-solid-hover disabled:bg-raised disabled:text-ink-faint"
      >
        {busy ? uz.admin.resetRunning : uz.admin.resetButton}
      </button>

      {busy && (
        <p className="mt-2 text-xs text-ink-soft">
          {state?.message ?? uz.admin.resetRunning}
        </p>
      )}
      {done && (
        <p className="mt-2 text-xs text-ok">
          {state?.ok ? `${state.message} ` : ""}
          {uz.admin.resetDone}
        </p>
      )}
      {error && <p className="mt-2 text-xs text-bad">{error}</p>}
      {!busy && state?.finished_at && (
        <p className="mt-1 text-[11px] text-ink-faint">
          {uz.admin.resetLast}: {formatDateTime(state.finished_at)}
        </p>
      )}
    </section>
  );
}
