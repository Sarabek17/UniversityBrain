"use client";

// Admin dashboard figures (S13). Every number comes from the backend, which
// collects them from the existing services (payments, presence, docflow...) —
// this component only lays them out.

import type { AdminStats } from "@/lib/api";
import { formatAmount } from "@/lib/labels";
import uz from "@/i18n/uz.json";

function Card({
  title,
  value,
  hint,
  children,
}: {
  title: string;
  value: string;
  hint?: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-gray-200 px-3 py-2.5 dark:border-gray-700">
      <h3 className="text-xs text-gray-500 dark:text-gray-400">{title}</h3>
      <p className="mt-0.5 text-xl font-semibold">{value}</p>
      {hint && (
        <p className="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
          {hint}
        </p>
      )}
      {children && <div className="mt-1.5 space-y-0.5 text-[11px]">{children}</div>}
    </section>
  );
}

function Line({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "danger" | "warn" | "ok";
}) {
  const color =
    tone === "danger"
      ? "text-red-700 dark:text-red-300"
      : tone === "warn"
        ? "text-amber-700 dark:text-amber-300"
        : tone === "ok"
          ? "text-emerald-700 dark:text-emerald-300"
          : "text-gray-600 dark:text-gray-300";
  return (
    <p className={"flex justify-between gap-2 " + color}>
      <span>{label}</span>
      <span className="font-medium">{value}</span>
    </p>
  );
}

export default function AdminStatsCards({ stats }: { stats: AdminStats }) {
  const roles = Object.fromEntries(
    stats.users.by_role.map((row) => [row.role, row]),
  );
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <Card
        title={uz.admin.statsUsers}
        value={String(stats.users.total)}
        hint={`${stats.users.group_count} ${uz.admin.statsGroups.toLowerCase()} · ${stats.users.faculty_count} ${uz.admin.statsFaculties.toLowerCase()}`}
      >
        {stats.users.by_role.map((row) => (
          <Line key={row.role} label={row.label} value={row.count} />
        ))}
      </Card>

      <Card
        title={uz.admin.statsDocuments}
        value={String(stats.corpus.document_count)}
        hint={`${stats.corpus.chunk_count} ${uz.admin.statsChunks.toLowerCase()}`}
      >
        <Line
          label={uz.admin.statsIndexed}
          value={`${stats.corpus.indexed_count} / ${stats.corpus.document_count}`}
          tone={
            stats.corpus.indexed_count === stats.corpus.document_count
              ? "ok"
              : "warn"
          }
        />
        <Line
          label={uz.admin.statsUploaded}
          value={stats.corpus.uploaded_count}
        />
      </Card>

      <Card
        title={uz.admin.statsPayments}
        value={formatAmount(stats.payments.remaining_amount)}
        hint={uz.admin.statsRemaining}
      >
        <Line
          label={uz.admin.statsDebtors}
          value={stats.payments.debtor_count}
          tone="danger"
        />
        <Line
          label={uz.admin.statsPartial}
          value={stats.payments.partial_count}
          tone="warn"
        />
        <Line
          label={uz.admin.statsPaid}
          value={stats.payments.paid_count}
          tone="ok"
        />
        <Line
          label={uz.admin.statsPending}
          value={stats.payments.pending_count}
        />
      </Card>

      <Card
        title={uz.admin.statsPresence}
        value={
          stats.presence.attendance_percent === null
            ? "—"
            : `${stats.presence.attendance_percent}%`
        }
        hint={`${uz.admin.statsAttendance} · ${stats.presence.pair_label ?? "—"}`}
      >
        <Line
          label={uz.admin.statsInside}
          value={stats.presence.inside_count}
          tone="ok"
        />
        <Line label={uz.admin.statsLeft} value={stats.presence.left_count} />
        <Line
          label={uz.admin.statsNotArrived}
          value={stats.presence.absent_count}
          tone="warn"
        />
      </Card>

      <Card
        title={uz.admin.statsTeachers}
        value={String(roles.teacher?.count ?? stats.teachers.teacher_count)}
        hint={`${stats.teachers.class_count} ${uz.admin.statsClasses.toLowerCase()}`}
      >
        <Line
          label={uz.admin.statsTeachersInside}
          value={stats.teachers.inside_count}
          tone="ok"
        />
        <Line label={uz.admin.statsHeld} value={stats.teachers.held_count} />
        <Line
          label={uz.admin.statsAtRisk}
          value={stats.teachers.at_risk_count}
          tone={stats.teachers.at_risk_count > 0 ? "danger" : undefined}
        />
      </Card>

      <Card
        title={uz.admin.statsDocflow}
        value={String(stats.docflow.total)}
        hint={`${uz.admin.statsNotifications}: ${stats.notifications.total} (${stats.notifications.unread_count} ${uz.admin.statsUnread.toLowerCase()})`}
      >
        <Line label={uz.admin.statsFlowNew} value={stats.docflow.new_count} />
        <Line label={uz.admin.statsFlowOpen} value={stats.docflow.open_count} />
        <Line
          label={uz.admin.statsFlowOverdue}
          value={stats.docflow.overdue_count}
          tone={stats.docflow.overdue_count > 0 ? "danger" : undefined}
        />
      </Card>
    </div>
  );
}
