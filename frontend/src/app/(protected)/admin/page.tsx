"use client";

// Admin panel (S13): the state of the whole system on one page — figures,
// user/role management, document upload and the demo reset. The nav link is
// admin-only, and so is every endpoint behind it (`require_role()`).

import { useCallback, useEffect, useState } from "react";
import { adminApi, type AdminStats } from "@/lib/api";
import AdminStatsCards from "@/components/AdminStatsCards";
import AdminUsersPanel from "@/components/AdminUsersPanel";
import AdminUploadPanel from "@/components/AdminUploadPanel";
import AdminResetPanel from "@/components/AdminResetPanel";
import { formatDateTime } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(
    () =>
      adminApi
        .stats()
        .then((data) => {
          setStats(data);
          setError(null);
        })
        .catch(() => setError(uz.admin.loadError)),
    [],
  );

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">{uz.admin.title}</h1>
          <p className="mt-0.5 text-xs text-ink-faint">
            {uz.admin.subtitle}
            {stats && ` · ${formatDateTime(stats.generated_at)}`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadStats()}
          className="rounded-md border border-line-strong px-3 py-1.5 text-xs hover:bg-raised"
        >
          {uz.admin.refresh}
        </button>
      </div>

      {!stats && !error && (
        <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      {stats && (
        <>
          <div className="mt-3">
            <AdminStatsCards stats={stats} />
          </div>
          <p className="mt-2 text-[11px] text-ink-soft">
            {uz.admin.statsSource}: {stats.source.label}
          </p>
          <p className="mt-1 text-[11px] italic text-ink-faint">
            {stats.disclaimer}
          </p>
        </>
      )}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <AdminUsersPanel onChanged={loadStats} />
        <div className="flex flex-col gap-4">
          <AdminUploadPanel onUploaded={loadStats} />
          <AdminResetPanel />
        </div>
      </div>
    </div>
  );
}
