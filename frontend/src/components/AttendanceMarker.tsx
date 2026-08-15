"use client";

// The teacher's marking sheet: the group roster of one class, the journal state
// of every student and the turnstile hint next to it. "Turniket bo'yicha
// to'ldirish" fills the whole list in one click; "Saqlash" writes the journal
// and turns the class session into "o'tildi".
//
// The draft lives in this component and is *derived* from the roster (the key
// changes whenever the server sends different counts), so no `setState` ever
// runs inside an effect (Next 16 `react-hooks/set-state-in-effect`).

import { useState } from "react";
import type { AttendanceStatus, ClassRoster } from "@/lib/api";
import {
  attendanceStatusClass,
  attendanceStatusLabel,
  formatTime,
  presenceStateClass,
  presenceStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

const STATUSES: AttendanceStatus[] = ["present", "late", "absent"];

type Marks = Record<number, AttendanceStatus>;

function rosterKey(roster: ClassRoster): string {
  return [
    roster.schedule_id,
    roster.date,
    roster.marked_count,
    roster.present_count,
    roster.late_count,
    roster.absent_count,
  ].join(":");
}

function journalMarks(roster: ClassRoster): Marks {
  const marks: Marks = {};
  for (const student of roster.students) {
    marks[student.student_id] = student.status ?? student.suggested;
  }
  return marks;
}

function turnstileMarks(roster: ClassRoster): Marks {
  const marks: Marks = {};
  for (const student of roster.students) {
    marks[student.student_id] = student.suggested;
  }
  return marks;
}

export default function AttendanceMarker({
  roster,
  onSave,
  saving,
  error,
  saved,
}: {
  roster: ClassRoster;
  onSave: (marks: { student_id: number; status: AttendanceStatus }[]) => void;
  saving: boolean;
  error: string | null;
  saved: boolean;
}) {
  const [draft, setDraft] = useState<{ key: string; marks: Marks } | null>(null);
  const key = rosterKey(roster);
  const marks = draft?.key === key ? draft.marks : journalMarks(roster);

  function setStatus(studentId: number, status: AttendanceStatus) {
    setDraft({ key, marks: { ...marks, [studentId]: status } });
  }

  return (
    <section className="flex min-h-0 flex-col">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">
            {roster.subject}{" "}
            <span className="text-sm font-normal text-ink-faint">
              · {roster.group_name}
            </span>
          </h2>
          <p className="mt-0.5 text-xs text-ink-faint">
            {roster.pair_label} · {roster.room}-{uz.attendance.room}{" "}
            <span className="italic">({uz.attendance.scheduleNote})</span>
            {roster.session_label ? (
              <> · {uz.attendance.sessionStatus}: {roster.session_label}</>
            ) : null}
          </p>
        </div>
        <p className="text-xs text-ink-faint">
          {roster.marked_count}/{roster.students.length}{" "}
          {uz.attendance.markedOf}
        </p>
      </header>

      {roster.can_mark && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setDraft({ key, marks: turnstileMarks(roster) })}
            className="rounded-md border border-line-strong px-3 py-1.5 text-xs hover:bg-raised"
          >
            {uz.attendance.fillFromTurnstile}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              onSave(
                Object.entries(marks).map(([studentId, status]) => ({
                  student_id: Number(studentId),
                  status,
                })),
              )
            }
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
          >
            {saving ? uz.attendance.saving : uz.attendance.save}
          </button>
          <span className="text-[11px] text-ink-faint">
            {uz.attendance.fillHint}
          </span>
        </div>
      )}

      {error && <p className="mt-2 text-sm text-bad">{error}</p>}
      {saved && !error && (
        <p className="mt-2 text-sm text-ok">
          {uz.attendance.saveSuccess}
        </p>
      )}

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
              <th className="py-2 pr-3 font-medium">{uz.attendance.student}</th>
              <th className="py-2 pr-3 font-medium">
                {uz.attendance.turnstile}
              </th>
              <th className="py-2 pr-3 font-medium">
                {uz.attendance.markTitle}
              </th>
              <th className="py-2 font-medium">{uz.attendance.status}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {roster.students.map((student) => (
              <tr key={student.student_id}>
                <td className="py-1.5 pr-3 font-medium">{student.full_name}</td>
                <td className="py-1.5 pr-3 whitespace-nowrap">
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[11px] " +
                      presenceStateClass(student.state)
                    }
                  >
                    {presenceStateLabel(student.state)}
                  </span>
                  <span className="ml-2 text-[11px] text-ink-faint">
                    {student.state === "inside" && student.entered_at
                      ? `${formatTime(student.entered_at)} ${uz.attendance.entered}`
                      : student.state === "left" && student.left_at
                        ? `${formatTime(student.left_at)} ${uz.attendance.leftAt}`
                        : uz.attendance.noEntry}
                  </span>
                </td>
                <td className="py-1.5 pr-3">
                  <div className="flex gap-1">
                    {STATUSES.map((status) => {
                      const active = marks[student.student_id] === status;
                      return (
                        <button
                          key={status}
                          type="button"
                          disabled={!roster.can_mark}
                          onClick={() => setStatus(student.student_id, status)}
                          className={
                            "rounded-full px-2 py-0.5 text-[11px] " +
                            (active
                              ? attendanceStatusClass(status)
                              : "border border-line-strong text-ink-faint hover:bg-raised") +
                            (roster.can_mark ? "" : " opacity-60")
                          }
                        >
                          {attendanceStatusLabel(status)}
                        </button>
                      );
                    })}
                  </div>
                </td>
                <td className="py-1.5 whitespace-nowrap text-[11px] text-ink-faint">
                  {student.status
                    ? attendanceStatusLabel(student.status)
                    : uz.attendance.notMarked}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] text-ink-soft">
        {uz.attendance.source}: {roster.source.label}
      </p>
      <p className="mt-1 text-[11px] italic text-ink-faint">
        {roster.schedule_note}
      </p>
    </section>
  );
}
