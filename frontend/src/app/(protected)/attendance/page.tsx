"use client";

// "Davomat" — one route, four views, because the same three sources (turnstile,
// schedule, journal) answer four different questions:
//
//   teacher      -> today's classes -> roster -> mark attendance in one click
//   tutor        -> the group presence list (inside / in class / left / absent)
//   staff/admin  -> the teachers of the faculty (S10) + the student list + the
//                   monthly report
//   student      -> own presence right now + own attendance history
//
// Everything schedule-derived is labelled "jadval bo'yicha" (domain rule 6) and
// the backend's `schedule_note` / `disclaimer` texts are never hardcoded here.

import { useCallback, useEffect, useState } from "react";
import {
  attendanceApi,
  errorDetail,
  type AttendanceStatus,
  type AttendanceSummary,
  type ClassRoster,
  type GroupPresence,
  type Presence,
  type TeacherDay,
  type TeacherDayOverview,
  type TeacherMonth,
  type TeacherPresenceRow,
} from "@/lib/api";
import AttendanceMarker from "@/components/AttendanceMarker";
import PresenceList, {
  PRESENCE_SORT_OPTIONS,
  sortPresenceRows,
  type PresenceSort,
} from "@/components/PresenceList";
import { useAuth } from "@/lib/auth";
import {
  attendanceStatusClass,
  attendanceStatusLabel,
  classStateClass,
  classStateLabel,
  formatDate,
  formatTime,
  percentClass,
  presenceStateClass,
  presenceStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function AttendancePage() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role === "teacher") return <TeacherView />;
  if (user.role === "student") return <StudentView />;
  if (user.role === "staff" || user.role === "admin") return <StaffView />;
  return <TutorView />;
}

// --- teacher ----------------------------------------------------------------

function TeacherView() {
  const [day, setDay] = useState<TeacherDay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [roster, setRoster] = useState<ClassRoster | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(
    () =>
      attendanceApi
        .myClasses()
        .then((data) => {
          setDay(data);
          setError(null);
        })
        .catch(() => setError(uz.attendance.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  function openClass(scheduleId: number) {
    setRosterError(null);
    setSaved(false);
    attendanceApi
      .roster(scheduleId)
      .then((data) => setRoster(data))
      .catch((e: unknown) =>
        setRosterError(errorDetail(e) ?? uz.attendance.noAccess),
      );
  }

  function save(marks: { student_id: number; status: AttendanceStatus }[]) {
    if (!roster) return;
    setSaving(true);
    setRosterError(null);
    attendanceApi
      .mark(roster.schedule_id, marks)
      .then((fresh) => {
        setRoster(fresh);
        setSaved(true);
        return load();
      })
      .catch((e: unknown) =>
        setRosterError(errorDetail(e) ?? uz.attendance.saveError),
      )
      .finally(() => setSaving(false));
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col md:flex-row">
      <section className="flex max-h-[40vh] min-h-0 w-full shrink-0 flex-col overflow-y-auto border-b border-line bg-sidebar px-4 py-5 md:max-h-none md:w-80 md:border-b-0 md:border-r">
        <h1 className="text-lg font-semibold">{uz.attendance.titleTeacher}</h1>
        <p className="mt-0.5 text-xs text-ink-faint">
          {uz.attendance.myClasses}
          {day ? ` · ${formatDate(day.date)}` : ""}
        </p>

        {!day && !error && (
          <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
        )}
        {error && <p className="mt-3 text-sm text-bad">{error}</p>}
        {day && day.classes.length === 0 && (
          <p className="mt-3 text-sm text-ink-faint">{uz.attendance.noClasses}</p>
        )}

        <ul className="mt-3 flex flex-col gap-2">
          {day?.classes.map((item) => (
            <li key={item.schedule_id}>
              <button
                type="button"
                onClick={() => openClass(item.schedule_id)}
                className={
                  "w-full rounded-lg border px-3 py-2 text-left text-sm " +
                  (roster?.schedule_id === item.schedule_id
                    ? "border-line-strong bg-raised"
                    : "border-line hover:bg-raised")
                }
              >
                <span className="flex items-baseline justify-between gap-2">
                  <span className="font-medium">{item.subject}</span>
                  <span className="text-[11px] text-ink-faint">
                    {formatTime(item.starts_at)}–{formatTime(item.ends_at)}
                  </span>
                </span>
                <span className="mt-0.5 block text-[11px] text-ink-soft">
                  {item.group_name} · {item.room}-{uz.attendance.room}{" "}
                  <span className="italic">({uz.attendance.scheduleNote})</span>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-1.5">
                  {item.is_current && (
                    <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[10px] text-accent-ink">
                      {uz.attendance.now}
                    </span>
                  )}
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[10px] " +
                      (item.marked_count > 0
                        ? "bg-ok-soft text-ok"
                        : "bg-raised text-ink-soft")
                    }
                  >
                    {item.marked_count}/{item.student_count}{" "}
                    {uz.attendance.marked}
                  </span>
                  {item.session_label && (
                    <span className="text-[10px] text-ink-faint">
                      {item.session_label}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
        {rosterError && !roster && (
          <p className="text-sm text-bad">{rosterError}</p>
        )}
        {roster ? (
          <AttendanceMarker
            roster={roster}
            onSave={save}
            saving={saving}
            error={rosterError}
            saved={saved}
          />
        ) : (
          !rosterError && (
            <p className="text-sm text-ink-faint">
              {uz.attendance.selectClass}
            </p>
          )
        )}
      </section>
    </div>
  );
}

// --- dean's office (S10) ----------------------------------------------------

type StaffTab = "teachers" | "monthly" | "students";

const STAFF_TABS: { value: StaffTab; label: string }[] = [
  { value: "teachers", label: uz.attendance.tabTeachers },
  { value: "monthly", label: uz.attendance.tabMonthly },
  { value: "students", label: uz.attendance.tabStudents },
];

function StaffView() {
  const [tab, setTab] = useState<StaffTab>("teachers");

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <nav className="flex shrink-0 gap-1 border-b border-line px-4 pt-4">
        {STAFF_TABS.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => setTab(item.value)}
            className={
              "rounded-t-md px-3 py-1.5 text-sm " +
              (tab === item.value
                ? "border-b-2 border-ink font-medium text-ink"
                : "text-ink-soft hover:bg-raised")
            }
          >
            {item.label}
          </button>
        ))}
      </nav>
      {tab === "teachers" && <TeacherMonitorView />}
      {tab === "monthly" && <TeacherMonthlyView />}
      {tab === "students" && <TutorView />}
    </div>
  );
}

/** One class of one teacher: the traffic light the dean reads the day from. */
function ClassChip({ item }: { item: TeacherPresenceRow["classes"][number] }) {
  return (
    <li
      className={
        "rounded-md px-2 py-1 text-[11px] " + classStateClass(item.state)
      }
      title={item.summary}
    >
      <span className="font-medium">
        {item.pair_number}-{uz.attendance.pair}
      </span>{" "}
      {item.subject} · {item.group_name} · {item.room}{" "}
      <span className="italic">({uz.attendance.scheduleNote})</span> ·{" "}
      {classStateLabel(item.state)}
    </li>
  );
}

function TeacherMonitorView() {
  const [overview, setOverview] = useState<TeacherDayOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      attendanceApi
        .teachers()
        .then((data) => {
          setOverview(data);
          setError(null);
        })
        .catch(() => setError(uz.attendance.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">{uz.attendance.titleStaff}</h1>
          {overview && (
            <p className="mt-0.5 text-xs text-ink-faint">
              {overview.teacher_count} {uz.attendance.teachers} ·{" "}
              {formatDate(overview.date)} · {formatTime(overview.at)}{" "}
              {uz.attendance.asOf}
              {overview.pair_label
                ? ` · ${overview.pair_label} (${uz.attendance.scheduleNote})`
                : ""}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-line-strong px-3 py-1 text-xs hover:bg-raised"
        >
          {uz.attendance.refresh}
        </button>
      </div>

      {!overview && !error && (
        <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      {overview && (
        <>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span
              className={
                "rounded-full px-2.5 py-1 " + presenceStateClass("inside")
              }
            >
              {uz.attendance.inside}: {overview.inside_count}
            </span>
            <span
              className={
                "rounded-full px-2.5 py-1 " + presenceStateClass("not_arrived")
              }
            >
              {uz.attendance.notArrived}: {overview.absent_count}
            </span>
            <span
              className={"rounded-full px-2.5 py-1 " + classStateClass("at_risk")}
            >
              {uz.attendance.atRisk}: {overview.at_risk_count}
            </span>
            <span
              className={
                "rounded-full px-2.5 py-1 " +
                classStateClass("needs_clarification")
              }
            >
              {uz.attendance.unclear}: {overview.unclear_count}
            </span>
            <span className={"rounded-full px-2.5 py-1 " + classStateClass("held")}>
              {uz.attendance.heldClasses}: {overview.held_count}/
              {overview.class_count}
            </span>
            {overview.late_count > 0 && (
              <span
                className={"rounded-full px-2.5 py-1 " + classStateClass("late")}
              >
                {uz.attendance.lateClasses}: {overview.late_count}
              </span>
            )}
          </div>

          {overview.rows.length === 0 && (
            <p className="mt-3 text-sm text-ink-faint">
              {uz.attendance.noTeachers}
            </p>
          )}

          <ul className="mt-3 flex flex-col gap-2">
            {overview.rows.map((row) => (
              <li
                key={row.teacher_id}
                className={
                  "rounded-lg border px-3 py-2 " +
                  // Red card: a class is at risk right now, or the teacher has
                  // classes today and the turnstile never saw them.
                  (row.at_risk_count > 0 ||
                  (row.state === "not_arrived" && row.class_count > 0)
                    ? "border-bad-line bg-bad-soft"
                    : "border-line")
                }
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{row.full_name}</span>
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[11px] " +
                      presenceStateClass(row.state)
                    }
                  >
                    {presenceStateLabel(row.state)}
                    {row.entered_at ? ` · ${formatTime(row.entered_at)}` : ""}
                    {row.left_at ? ` → ${formatTime(row.left_at)}` : ""}
                  </span>
                  {row.at_risk_count > 0 && (
                    <span
                      className={
                        "rounded-full px-2 py-0.5 text-[11px] " +
                        classStateClass("at_risk")
                      }
                    >
                      {uz.attendance.atRisk}: {row.at_risk_count}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  {row.summary}
                </p>
                {row.classes.length === 0 ? (
                  <p className="mt-1 text-[11px] text-ink-faint">
                    {uz.attendance.noTeacherClasses}
                  </p>
                ) : (
                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                    {row.classes.map((item) => (
                      <ClassChip key={item.schedule_id} item={item} />
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>

          <p className="mt-3 text-[11px] text-ink-soft">
            {uz.attendance.source}: {overview.source.label}
          </p>
          <p className="mt-1 text-[11px] italic text-ink-faint">
            {overview.schedule_note}
          </p>
          <p className="mt-1 text-[11px] italic text-ink-faint">
            {overview.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}

function TeacherMonthlyView() {
  const [summary, setSummary] = useState<TeacherMonth | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      attendanceApi
        .teachersMonthly()
        .then((data) => {
          setSummary(data);
          setError(null);
        })
        .catch(() => setError(uz.attendance.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
      <h1 className="text-lg font-semibold">{uz.attendance.monthlyTitle}</h1>
      {summary && (
        <p className="mt-0.5 text-xs text-ink-faint">
          {uz.attendance.monthlyPeriod}: {formatDate(summary.date_from)} –{" "}
          {formatDate(summary.date_to)} · {uz.attendance.monthlyTotal}:{" "}
          {summary.total}
          {summary.percent !== null ? ` · ${summary.percent}%` : ""}
        </p>
      )}

      {!summary && !error && (
        <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      {summary &&
        (summary.rows.length === 0 || summary.total === 0 ? (
          <p className="mt-3 text-sm text-ink-faint">
            {uz.attendance.monthlyEmpty}
          </p>
        ) : (
          <>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
                    <th className="py-2 pr-3 font-medium">
                      {uz.attendance.teacher}
                    </th>
                    <th className="py-2 pr-3 font-medium">
                      {uz.attendance.monthlyHeld}
                    </th>
                    <th className="py-2 pr-3 font-medium">
                      {uz.attendance.monthlyPercent}
                    </th>
                    <th className="py-2 pr-3 font-medium">
                      {uz.attendance.lateClasses}
                    </th>
                    <th className="py-2 pr-3 font-medium">
                      {uz.attendance.monthlyCancelled}
                    </th>
                    <th className="py-2 font-medium">{uz.attendance.unclear}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {summary.rows.map((row) => (
                    <tr key={row.teacher_id}>
                      <td className="py-1.5 pr-3">{row.full_name}</td>
                      <td className="py-1.5 pr-3 whitespace-nowrap">
                        {row.held}/{row.total}
                      </td>
                      <td
                        className={
                          "py-1.5 pr-3 whitespace-nowrap " +
                          percentClass(row.percent)
                        }
                      >
                        {row.percent === null ? "—" : `${row.percent}%`}
                      </td>
                      <td className="py-1.5 pr-3">{row.late}</td>
                      <td className="py-1.5 pr-3">{row.cancelled}</td>
                      <td className="py-1.5">{row.unclear}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-3 text-[11px] text-ink-soft">
              {uz.attendance.source}: {summary.source.label}
            </p>
            <p className="mt-1 text-[11px] italic text-ink-faint">
              {summary.disclaimer}
            </p>
          </>
        ))}
    </div>
  );
}

// --- tutor / dean's office (students) ---------------------------------------

function TutorView() {
  const [summary, setSummary] = useState<GroupPresence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<PresenceSort>("state");

  const load = useCallback(
    () =>
      attendanceApi
        .group()
        .then((data) => {
          setSummary(data);
          setError(null);
        })
        .catch(() => setError(uz.attendance.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const rows = summary ? sortPresenceRows(summary.rows, sort) : [];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">{uz.attendance.titleTutor}</h1>
          {summary && (
            <p className="mt-0.5 text-xs text-ink-faint">
              {summary.group_names.join(", ")} · {summary.rows.length}{" "}
              {uz.attendance.students} · {formatTime(summary.at)}{" "}
              {uz.attendance.asOf}
              {summary.pair_label
                ? ` · ${summary.pair_label} (${uz.attendance.scheduleNote})`
                : ""}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-ink-soft">
            {uz.payments.sortBy}
            <select
              value={sort}
              onChange={(event) =>
                setSort(event.target.value as PresenceSort)
              }
              className="rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            >
              {PRESENCE_SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-md border border-line-strong px-3 py-1 text-xs hover:bg-raised"
          >
            {uz.attendance.refresh}
          </button>
        </div>
      </div>

      {!summary && !error && (
        <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      {summary && (
        <>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span
              className={
                "rounded-full px-2.5 py-1 " + presenceStateClass("inside")
              }
            >
              {uz.attendance.inside}: {summary.inside_count}
            </span>
            <span
              className={"rounded-full px-2.5 py-1 " + presenceStateClass("left")}
            >
              {uz.attendance.left}: {summary.left_count}
            </span>
            <span
              className={
                "rounded-full px-2.5 py-1 " + presenceStateClass("not_arrived")
              }
            >
              {uz.attendance.notArrived}: {summary.absent_count}
            </span>
            {summary.current_pair !== null && (
              <span className="rounded-full bg-raised px-2.5 py-1 text-ink-soft">
                {uz.attendance.inClass}: {summary.in_class_count}
              </span>
            )}
            {summary.attendance_percent !== null && (
              <span className="rounded-full bg-raised px-2.5 py-1 text-ink-soft">
                {uz.attendance.dayAttendance}: {summary.attendance_percent}%
              </span>
            )}
          </div>

          <div className="mt-3">
            <PresenceList rows={rows} />
          </div>

          <p className="mt-3 text-[11px] text-ink-soft">
            {uz.attendance.source}: {summary.source.label}
          </p>
          <p className="mt-1 text-[11px] italic text-ink-faint">
            {summary.schedule_note}
          </p>
          <p className="mt-1 text-[11px] italic text-ink-faint">
            {summary.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}

// --- student ----------------------------------------------------------------

function StudentView() {
  const [presence, setPresence] = useState<Presence | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      Promise.all([attendanceApi.presence(), attendanceApi.summary()])
        .then(([now, history]) => {
          setPresence(now);
          setSummary(history);
          setError(null);
        })
        .catch(() => setError(uz.attendance.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
      <h1 className="text-lg font-semibold">{uz.attendance.titleStudent}</h1>
      {!presence && !error && (
        <p className="mt-3 text-sm text-ink-faint">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      {presence && (
        <section className="mt-3 rounded-lg border border-line px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">
              {uz.attendance.presenceTitle}
            </h2>
            <span
              className={
                "rounded-full px-2.5 py-0.5 text-xs " +
                presenceStateClass(presence.state)
              }
            >
              {presenceStateLabel(presence.state)}
            </span>
            <span className="text-xs text-ink-faint">
              {formatTime(presence.at)} {uz.attendance.asOf}
            </span>
          </div>
          <p className="mt-2 text-sm">{presence.summary}</p>
          {presence.current_class && (
            <p className="mt-1 text-xs text-ink-soft">
              {uz.attendance.currentClass} ({uz.attendance.scheduleNote}):{" "}
              {presence.current_class.subject} · {presence.current_class.room}-
              {uz.attendance.room} ·{" "}
              <span
                className={
                  "rounded-full px-2 py-0.5 " +
                  attendanceStatusClass(presence.attendance_status)
                }
              >
                {presence.attendance_status
                  ? attendanceStatusLabel(presence.attendance_status)
                  : uz.attendance.notMarked}
              </span>
            </p>
          )}
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {presence.sources.map((source, index) => (
              <li
                key={`${source.type}-${index}`}
                className="rounded-full bg-raised px-2 py-0.5 text-[11px] text-ink-soft"
              >
                {source.label}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] italic text-ink-faint">
            {presence.schedule_note}
          </p>
        </section>
      )}

      {summary && (
        <section className="mt-4">
          <h2 className="text-sm font-semibold">
            {uz.attendance.historyTitle}{" "}
            <span className="font-normal text-ink-faint">
              ({formatDate(summary.date_from)} – {formatDate(summary.date_to)})
            </span>
          </h2>
          {summary.total === 0 ? (
            <p className="mt-2 text-sm text-ink-faint">{uz.attendance.empty}</p>
          ) : (
            <>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span
                  className={
                    "rounded-full px-2.5 py-1 " + attendanceStatusClass("present")
                  }
                >
                  {uz.attendance.statuses.present}: {summary.present}
                </span>
                <span
                  className={
                    "rounded-full px-2.5 py-1 " + attendanceStatusClass("late")
                  }
                >
                  {uz.attendance.statuses.late}: {summary.late}
                </span>
                <span
                  className={
                    "rounded-full px-2.5 py-1 " + attendanceStatusClass("absent")
                  }
                >
                  {uz.attendance.statuses.absent}: {summary.absent}
                </span>
                <span className="rounded-full bg-raised px-2.5 py-1 text-ink-soft">
                  {summary.percent}% ({summary.total})
                </span>
              </div>

              <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                {uz.attendance.bySubject}
              </h3>
              <ul className="mt-1 flex flex-col gap-1">
                {summary.by_subject.map((row) => (
                  <li
                    key={row.subject}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="truncate">{row.subject}</span>
                    <span
                      className={
                        row.percent >= 75
                          ? "text-ok"
                          : "text-bad"
                      }
                    >
                      {row.attended}/{row.total} ({row.percent}%)
                    </span>
                  </li>
                ))}
              </ul>

              <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                {uz.attendance.recent}
              </h3>
              <div className="mt-1 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
                      <th className="py-2 pr-3 font-medium">
                        {uz.attendance.date}
                      </th>
                      <th className="py-2 pr-3 font-medium">
                        {uz.attendance.subject}
                      </th>
                      <th className="py-2 pr-3 font-medium">
                        {uz.attendance.room}
                      </th>
                      <th className="py-2 font-medium">
                        {uz.attendance.status}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {summary.recent.map((row, index) => (
                      <tr key={`${row.date}-${row.pair_number}-${index}`}>
                        <td className="py-1.5 pr-3 whitespace-nowrap">
                          {formatDate(row.date)} · {row.pair_number}-
                          {uz.attendance.pair}
                        </td>
                        <td className="py-1.5 pr-3">{row.subject}</td>
                        <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">
                          {row.room}
                        </td>
                        <td className="py-1.5 whitespace-nowrap">
                          <span
                            className={
                              "rounded-full px-2 py-0.5 text-[11px] " +
                              attendanceStatusClass(row.status)
                            }
                          >
                            {attendanceStatusLabel(row.status)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="mt-3 text-[11px] text-ink-soft">
                {uz.attendance.source}: {summary.source.label}
              </p>
              <p className="mt-1 text-[11px] italic text-ink-faint">
                {summary.disclaimer}
              </p>
            </>
          )}
        </section>
      )}
    </div>
  );
}
