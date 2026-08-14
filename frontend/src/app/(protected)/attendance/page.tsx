"use client";

// "Davomat" — one route, three views, because the same three sources (turnstile,
// schedule, journal) answer three different questions:
//
//   teacher      -> today's classes -> roster -> mark attendance in one click
//   tutor/staff  -> the group presence list (inside / in class / left / absent)
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
  formatDate,
  formatTime,
  presenceStateClass,
  presenceStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function AttendancePage() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role === "teacher") return <TeacherView />;
  if (user.role === "student") return <StudentView />;
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
    <div className="flex min-h-0 flex-1">
      <section className="flex min-h-0 w-80 shrink-0 flex-col overflow-y-auto border-r border-gray-200 px-4 py-5 dark:border-gray-700">
        <h1 className="text-lg font-semibold">{uz.attendance.titleTeacher}</h1>
        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
          {uz.attendance.myClasses}
          {day ? ` · ${formatDate(day.date)}` : ""}
        </p>

        {!day && !error && (
          <p className="mt-3 text-sm text-gray-500">{uz.common.loading}</p>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {day && day.classes.length === 0 && (
          <p className="mt-3 text-sm text-gray-500">{uz.attendance.noClasses}</p>
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
                    ? "border-blue-400 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/40"
                    : "border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800")
                }
              >
                <span className="flex items-baseline justify-between gap-2">
                  <span className="font-medium">{item.subject}</span>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400">
                    {formatTime(item.starts_at)}–{formatTime(item.ends_at)}
                  </span>
                </span>
                <span className="mt-0.5 block text-[11px] text-gray-600 dark:text-gray-300">
                  {item.group_name} · {item.room}-{uz.attendance.room}{" "}
                  <span className="italic">({uz.attendance.scheduleNote})</span>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-1.5">
                  {item.is_current && (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      {uz.attendance.now}
                    </span>
                  )}
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[10px] " +
                      (item.marked_count > 0
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300")
                    }
                  >
                    {item.marked_count}/{item.student_count}{" "}
                    {uz.attendance.marked}
                  </span>
                  {item.session_label && (
                    <span className="text-[10px] text-gray-500 dark:text-gray-400">
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
          <p className="text-sm text-red-600">{rosterError}</p>
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
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {uz.attendance.selectClass}
            </p>
          )
        )}
      </section>
    </div>
  );
}

// --- tutor / dean's office --------------------------------------------------

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
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
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
          <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
            {uz.payments.sortBy}
            <select
              value={sort}
              onChange={(event) =>
                setSort(event.target.value as PresenceSort)
              }
              className="rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
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
            className="rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {uz.attendance.refresh}
          </button>
        </div>
      </div>

      {!summary && !error && (
        <p className="mt-3 text-sm text-gray-500">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

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
              <span className="rounded-full border border-blue-300 px-2.5 py-1 text-blue-800 dark:border-blue-800 dark:text-blue-200">
                {uz.attendance.inClass}: {summary.in_class_count}
              </span>
            )}
            {summary.attendance_percent !== null && (
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {uz.attendance.dayAttendance}: {summary.attendance_percent}%
              </span>
            )}
          </div>

          <div className="mt-3">
            <PresenceList rows={rows} />
          </div>

          <p className="mt-3 text-[11px] text-gray-600 dark:text-gray-300">
            {uz.attendance.source}: {summary.source.label}
          </p>
          <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
            {summary.schedule_note}
          </p>
          <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
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
        <p className="mt-3 text-sm text-gray-500">{uz.common.loading}</p>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {presence && (
        <section className="mt-3 rounded-lg border border-gray-200 px-4 py-3 dark:border-gray-700">
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
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {formatTime(presence.at)} {uz.attendance.asOf}
            </span>
          </div>
          <p className="mt-2 text-sm">{presence.summary}</p>
          {presence.current_class && (
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
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
                className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              >
                {source.label}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] italic text-gray-500 dark:text-gray-400">
            {presence.schedule_note}
          </p>
        </section>
      )}

      {summary && (
        <section className="mt-4">
          <h2 className="text-sm font-semibold">
            {uz.attendance.historyTitle}{" "}
            <span className="font-normal text-gray-500 dark:text-gray-400">
              ({formatDate(summary.date_from)} – {formatDate(summary.date_to)})
            </span>
          </h2>
          {summary.total === 0 ? (
            <p className="mt-2 text-sm text-gray-500">{uz.attendance.empty}</p>
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
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  {summary.percent}% ({summary.total})
                </span>
              </div>

              <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
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
                          ? "text-emerald-700 dark:text-emerald-300"
                          : "text-red-700 dark:text-red-300"
                      }
                    >
                      {row.attended}/{row.total} ({row.percent}%)
                    </span>
                  </li>
                ))}
              </ul>

              <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {uz.attendance.recent}
              </h3>
              <div className="mt-1 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-[11px] uppercase tracking-wide text-gray-500 dark:border-gray-700 dark:text-gray-400">
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
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {summary.recent.map((row, index) => (
                      <tr key={`${row.date}-${row.pair_number}-${index}`}>
                        <td className="py-1.5 pr-3 whitespace-nowrap">
                          {formatDate(row.date)} · {row.pair_number}-
                          {uz.attendance.pair}
                        </td>
                        <td className="py-1.5 pr-3">{row.subject}</td>
                        <td className="py-1.5 pr-3 whitespace-nowrap text-gray-600 dark:text-gray-300">
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

              <p className="mt-3 text-[11px] text-gray-600 dark:text-gray-300">
                {uz.attendance.source}: {summary.source.label}
              </p>
              <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
                {summary.disclaimer}
              </p>
            </>
          )}
        </section>
      )}
    </div>
  );
}
