"use client";

// The tutor's answer to "who is actually here?": one row per student, colour by
// turnstile state (green inside / amber left / red never came), plus what the
// journal says about the class running right now.
//
// Domain rule 6: the room comes from the schedule, so every cell that shows one
// carries the "jadval bo'yicha" note — it is an inference, not a measurement.

import type { GroupPresenceRow } from "@/lib/api";
import {
  attendanceStatusClass,
  attendanceStatusLabel,
  formatTime,
  presenceStateClass,
  presenceStateLabel,
} from "@/lib/labels";
import uz from "@/i18n/uz.json";

export type PresenceSort = "state" | "name" | "group";

export const PRESENCE_SORT_OPTIONS: { value: PresenceSort; label: string }[] = [
  { value: "state", label: uz.attendance.status },
  { value: "name", label: uz.payments.sortName },
  { value: "group", label: uz.payments.sortGroup },
];

const STATE_ORDER: Record<string, number> = {
  not_arrived: 0,
  left: 1,
  inside: 2,
};

export function sortPresenceRows(
  rows: GroupPresenceRow[],
  sort: PresenceSort,
): GroupPresenceRow[] {
  const copy = [...rows];
  if (sort === "name") {
    copy.sort((a, b) => a.full_name.localeCompare(b.full_name));
  } else if (sort === "group") {
    copy.sort(
      (a, b) =>
        (a.group_name ?? "").localeCompare(b.group_name ?? "") ||
        a.full_name.localeCompare(b.full_name),
    );
  } else {
    // Default = the order the tutor needs: problems first.
    copy.sort(
      (a, b) =>
        (STATE_ORDER[a.state] ?? 9) - (STATE_ORDER[b.state] ?? 9) ||
        Number(a.attendance_marked) - Number(b.attendance_marked) ||
        a.full_name.localeCompare(b.full_name),
    );
  }
  return copy;
}

export default function PresenceList({
  rows,
  activeStudentId,
  onSelect,
}: {
  rows: GroupPresenceRow[];
  activeStudentId?: number | null;
  onSelect?: (studentId: number) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="px-4 py-3 text-sm text-ink-faint">
        {uz.attendance.groupEmpty}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
            <th className="py-2 pr-3 font-medium">{uz.attendance.student}</th>
            <th className="py-2 pr-3 font-medium">{uz.attendance.group}</th>
            <th className="py-2 pr-3 font-medium">{uz.attendance.turnstile}</th>
            <th className="py-2 pr-3 font-medium">
              {uz.attendance.currentClass}{" "}
              <span className="normal-case">({uz.attendance.scheduleNote})</span>
            </th>
            <th className="py-2 pr-3 font-medium">{uz.attendance.markTitle}</th>
            <th className="py-2 font-medium">{uz.attendance.dayAttendance}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr
              key={row.student_id}
              className={
                row.student_id === activeStudentId
                  ? "bg-raised"
                  : ""
              }
            >
              <td className="py-1.5 pr-3">
                {onSelect ? (
                  <button
                    type="button"
                    onClick={() => onSelect(row.student_id)}
                    className="text-left font-medium text-accent-ink hover:underline"
                  >
                    {row.full_name}
                  </button>
                ) : (
                  <span className="font-medium">{row.full_name}</span>
                )}
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">
                {row.group_name ?? "—"}
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap">
                <span
                  className={
                    "rounded-full px-2 py-0.5 text-[11px] " +
                    presenceStateClass(row.state)
                  }
                >
                  {presenceStateLabel(row.state)}
                </span>
                <span className="ml-2 text-[11px] text-ink-faint">
                  {row.state === "inside" && row.entered_at
                    ? `${formatTime(row.entered_at)} ${uz.attendance.entered}`
                    : row.state === "left" && row.left_at
                      ? `${formatTime(row.left_at)} ${uz.attendance.leftAt}`
                      : uz.attendance.noEntry}
                </span>
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap text-ink-soft">
                {row.room ? (
                  <>
                    <span className="font-medium">
                      {row.room}-{uz.attendance.room}
                    </span>
                    <span className="ml-1 text-[11px] text-ink-faint">
                      {row.subject}
                    </span>
                  </>
                ) : (
                  <span className="text-[11px] text-ink-faint">
                    {uz.attendance.noCurrentClass}
                  </span>
                )}
              </td>
              <td className="py-1.5 pr-3 whitespace-nowrap">
                {row.pair_number === null ? (
                  <span className="text-[11px] text-ink-faint">—</span>
                ) : (
                  <span
                    className={
                      "rounded-full px-2 py-0.5 text-[11px] " +
                      attendanceStatusClass(row.attendance_status)
                    }
                  >
                    {row.attendance_status
                      ? attendanceStatusLabel(row.attendance_status)
                      : uz.attendance.notMarked}
                  </span>
                )}
              </td>
              <td className="py-1.5 whitespace-nowrap">
                {row.attendance_percent === null ? (
                  <span className="text-[11px] text-ink-faint">—</span>
                ) : (
                  <span
                    className={
                      row.attendance_percent >= 75
                        ? "text-ok"
                        : "text-bad"
                    }
                  >
                    {row.attended_count}/{row.marked_count} (
                    {row.attendance_percent}%)
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
