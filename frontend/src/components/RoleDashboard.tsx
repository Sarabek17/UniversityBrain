"use client";

// Dashboard rail next to the chat (teacher / tutor / staff / admin).
// S8 filled its first widget: the payment state of the caller's groups —
// counts, biggest debts, receipts waiting for confirmation — with a link to the
// full "Guruh" page. S9 filled the teacher's half: today's classes and how much
// of the attendance is already marked, linking to "Davomat". S10 added the
// dean's alert: how many classes are at risk right now.

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  attendanceApi,
  paymentsApi,
  type GroupPaymentSummary,
  type TeacherDay,
  type TeacherDayOverview,
  type UserRole,
} from "@/lib/api";
import {
  classStateClass,
  formatAmount,
  formatTime,
  paymentStateClass,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

const DASHBOARD_ROLES: UserRole[] = ["teacher", "tutor", "staff", "admin"];
const PAYMENT_ROLES: UserRole[] = ["tutor", "staff", "admin"];
const TEACHER_RISK_ROLES: UserRole[] = ["staff", "admin"];
const TOP_DEBTORS = 4;
const TOP_RISK_TEACHERS = 3;

export const hasDashboard = (role: UserRole): boolean =>
  DASHBOARD_ROLES.includes(role);

export default function RoleDashboard({ role }: { role: UserRole }) {
  const [summary, setSummary] = useState<GroupPaymentSummary | null>(null);
  const [failed, setFailed] = useState(false);
  const [day, setDay] = useState<TeacherDay | null>(null);
  const [teachers, setTeachers] = useState<TeacherDayOverview | null>(null);
  const showPayments = PAYMENT_ROLES.includes(role);
  const showClasses = role === "teacher";
  const showTeacherRisk = TEACHER_RISK_ROLES.includes(role);

  useEffect(() => {
    if (!showPayments) return;
    let cancelled = false;
    paymentsApi
      .group()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [showPayments]);

  useEffect(() => {
    if (!showClasses) return;
    let cancelled = false;
    attendanceApi
      .myClasses()
      .then((data) => {
        if (!cancelled) setDay(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [showClasses]);

  useEffect(() => {
    if (!showTeacherRisk) return;
    let cancelled = false;
    attendanceApi
      .teachers()
      .then((data) => {
        if (!cancelled) setTeachers(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [showTeacherRisk]);

  if (!hasDashboard(role)) return null;
  const item =
    uz.dashboard.items[role as "teacher" | "tutor" | "staff" | "admin"];
  const debtors = summary
    ? summary.rows.filter((row) => row.remaining_amount > 0).slice(0, TOP_DEBTORS)
    : [];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
      <h2 className="text-sm font-semibold">{uz.dashboard.title}</h2>
      <p className="mt-1 text-xs text-ink-faint">
        {uz.roles[role]}
      </p>

      {showPayments && (
        <section className="mt-3 rounded-lg border border-line px-3 py-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
              {uz.dashboard.paymentsTitle}
            </h3>
            <Link
              href="/group"
              className="text-[11px] text-accent-ink hover:underline"
            >
              {uz.dashboard.openGroup}
            </Link>
          </div>

          {!summary && !failed && (
            <p className="mt-2 text-xs text-ink-faint">{uz.common.loading}</p>
          )}
          {failed && (
            <p className="mt-2 text-xs text-bad">{uz.payments.loadError}</p>
          )}

          {summary && (
            <>
              <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                <span
                  className={"rounded-full px-2 py-0.5 " + paymentStateClass("paid")}
                >
                  {uz.payments.states.paid}: {summary.paid_count}
                </span>
                <span
                  className={
                    "rounded-full px-2 py-0.5 " + paymentStateClass("partial")
                  }
                >
                  {uz.payments.states.partial}: {summary.partial_count}
                </span>
                <span
                  className={
                    "rounded-full px-2 py-0.5 " + paymentStateClass("debtor")
                  }
                >
                  {uz.payments.states.debtor}: {summary.debtor_count}
                </span>
              </div>
              {summary.pending_count > 0 && (
                <p className="mt-2 rounded-md bg-warn-soft px-2 py-1 text-[11px] text-warn">
                  {summary.pending_count} {uz.payments.groupPending}
                </p>
              )}
              <ul className="mt-2 flex flex-col gap-1">
                {debtors.map((row) => (
                  <li
                    key={row.student_id}
                    className="flex items-center justify-between gap-2 text-[11px]"
                  >
                    <span className="truncate">{row.full_name}</span>
                    <span className="shrink-0 text-bad">
                      {formatAmount(row.remaining_amount)}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-ink-faint">
                {uz.payments.groupDebtTotal}:{" "}
                {formatAmount(summary.remaining_amount)}
              </p>
            </>
          )}
        </section>
      )}

      {showClasses && (
        <section className="mt-3 rounded-lg border border-line px-3 py-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
              {uz.dashboard.attendanceTitle}
            </h3>
            <Link
              href="/attendance"
              className="text-[11px] text-accent-ink hover:underline"
            >
              {uz.dashboard.openAttendance}
            </Link>
          </div>

          {!day && !failed && (
            <p className="mt-2 text-xs text-ink-faint">{uz.common.loading}</p>
          )}
          {failed && !day && (
            <p className="mt-2 text-xs text-bad">
              {uz.attendance.loadError}
            </p>
          )}
          {day && day.classes.length === 0 && (
            <p className="mt-2 text-xs text-ink-faint">
              {uz.attendance.noClasses}
            </p>
          )}
          <ul className="mt-2 flex flex-col gap-1.5">
            {day?.classes.map((row) => (
              <li key={row.schedule_id} className="text-[11px]">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate">
                    {formatTime(row.starts_at)} · {row.subject}
                  </span>
                  <span
                    className={
                      "shrink-0 rounded-full px-1.5 py-0.5 " +
                      (row.marked_count > 0
                        ? "bg-ok-soft text-ok"
                        : "bg-raised text-ink-soft")
                    }
                  >
                    {row.marked_count}/{row.student_count}
                  </span>
                </span>
                <span className="text-ink-faint">
                  {row.group_name} · {row.room}-{uz.attendance.room} (
                  {uz.attendance.scheduleNote})
                  {row.is_current ? ` · ${uz.attendance.now}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {showTeacherRisk && (
        <section className="mt-3 rounded-lg border border-line px-3 py-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
              {uz.attendance.titleStaff}
            </h3>
            <Link
              href="/attendance"
              className="text-[11px] text-accent-ink hover:underline"
            >
              {uz.dashboard.openAttendance}
            </Link>
          </div>

          {!teachers && !failed && (
            <p className="mt-2 text-xs text-ink-faint">{uz.common.loading}</p>
          )}
          {failed && !teachers && (
            <p className="mt-2 text-xs text-bad">
              {uz.attendance.loadError}
            </p>
          )}

          {teachers && (
            <>
              <p
                className={
                  "mt-2 rounded-md px-2 py-1 text-[11px] " +
                  (teachers.at_risk_count > 0
                    ? classStateClass("at_risk")
                    : classStateClass("held"))
                }
              >
                {teachers.at_risk_count > 0
                  ? `${uz.attendance.riskWidget}: ${teachers.at_risk_count} ${uz.attendance.riskWidgetUnit}`
                  : uz.attendance.riskNone}
              </p>
              <ul className="mt-2 flex flex-col gap-1">
                {teachers.rows
                  .filter(
                    (row) =>
                      row.at_risk_count > 0 ||
                      (row.state === "not_arrived" && row.class_count > 0),
                  )
                  .slice(0, TOP_RISK_TEACHERS)
                  .map((row) => (
                    <li key={row.teacher_id} className="text-[11px]">
                      <span className="font-medium">{row.full_name}</span>
                      <span className="text-ink-faint">
                        {row.classes
                          .filter(
                            (cls) =>
                              cls.state === "at_risk" ||
                              cls.state === "needs_clarification",
                          )
                          .map(
                            (cls) =>
                              ` · ${cls.pair_number}-${uz.attendance.pair} ${cls.subject} (${cls.room})`,
                          )
                          .join("")}
                      </span>
                    </li>
                  ))}
              </ul>
              <p className="mt-2 text-[11px] text-ink-faint">
                {uz.attendance.notArrived}: {teachers.absent_count} ·{" "}
                {uz.attendance.unclear}: {teachers.unclear_count} ·{" "}
                {uz.attendance.heldClasses}: {teachers.held_count}/
                {teachers.class_count}
              </p>
            </>
          )}
        </section>
      )}

      <div className="mt-3 flex flex-col gap-2">
        <div className="rounded-lg border border-dashed border-line-strong px-3 py-4 text-xs text-ink-soft">
          {item}
        </div>
      </div>

      <p className="mt-4 text-[11px] text-ink-faint">
        {uz.documents.panelHint}
      </p>
    </div>
  );
}
