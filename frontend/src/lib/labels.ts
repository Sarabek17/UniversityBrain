// Uzbek labels for backend enums. UI text itself lives in i18n/uz.json.

import type {
  AccessLevel,
  AttendanceStatus,
  ClassSessionStatus,
  ClassState,
  DocumentType,
  FlowDocumentType,
  FlowStatus,
  PaymentState,
  PaymentStatus,
  PresenceState,
  UserRole,
} from "@/lib/api";
import uz from "@/i18n/uz.json";

const LANGUAGE_LABELS: Record<string, string> = uz.documents.languages;

export const docTypeLabel = (type: DocumentType): string =>
  uz.documents.types[type] ?? type;

export const accessLabel = (level: AccessLevel): string =>
  uz.documents.access[level] ?? level;

export const languageLabel = (code: string): string =>
  LANGUAGE_LABELS[code] ?? code.toUpperCase();

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatDate(iso: string): string {
  return formatDateTime(iso).split(" ")[0];
}

// --- payments (S8) ----------------------------------------------------------

/** `12000000` -> `"12 000 000 so'm"` — the same shape the backend prints. */
export function formatAmount(value: number): string {
  const rounded = Math.round(value);
  return `${rounded.toLocaleString("en-US").replace(/,/g, " ")} so'm`;
}

export const paymentStateLabel = (state: PaymentState): string =>
  uz.payments.states[state] ?? state;

export const paymentStatusLabel = (status: PaymentStatus): string =>
  uz.payments.statuses[status] ?? status;

/** Traffic light for a contract state: green paid, amber partial, red debtor. */
export const paymentStateClass = (state: PaymentState): string =>
  ({
    paid: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
    partial: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    debtor: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  })[state] ?? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";

// --- presence / attendance (S9) ---------------------------------------------

const NEUTRAL_CHIP =
  "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";

/** `"2026-08-14T10:02:00"` -> `"10:02"`. */
export function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export const presenceStateLabel = (state: PresenceState): string =>
  uz.attendance.states[state] ?? state;

/** Green inside, amber left the building, red never came today. */
export const presenceStateClass = (state: PresenceState): string =>
  ({
    inside: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
    left: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    not_arrived: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  })[state] ?? NEUTRAL_CHIP;

export const attendanceStatusLabel = (status: AttendanceStatus): string =>
  uz.attendance.statuses[status] ?? status;

export const attendanceStatusClass = (status: AttendanceStatus | null): string =>
  status === null
    ? NEUTRAL_CHIP
    : ({
        present:
          "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
        late: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
        absent: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
      })[status] ?? NEUTRAL_CHIP;

export const sessionStatusLabel = (status: ClassSessionStatus): string =>
  uz.attendance.sessions[status] ?? status;

// --- teacher attendance (S10) ------------------------------------------------

export const classStateLabel = (state: ClassState): string =>
  uz.attendance.classStates[state] ?? state;

/** The dean's traffic light: green held, red at risk, amber unclear,
 * orange late, grey not started / cancelled. */
export const classStateClass = (state: ClassState): string =>
  ({
    held: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
    at_risk: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
    needs_clarification:
      "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    late: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200",
    upcoming: NEUTRAL_CHIP,
    cancelled: NEUTRAL_CHIP,
  })[state] ?? NEUTRAL_CHIP;

// --- document flow (S11) -----------------------------------------------------

export const flowTypeLabel = (type: FlowDocumentType): string =>
  uz.docflow.types[type] ?? type;

export const flowStatusLabel = (status: FlowStatus): string =>
  uz.docflow.statuses[status] ?? status;

/** The status chain as a traffic light: grey sent, blue seen/in progress,
 * green approved, red rejected. */
export const flowStatusClass = (status: FlowStatus): string =>
  ({
    sent: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    seen: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
    in_progress: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    approved:
      "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
    rejected: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  })[status] ?? NEUTRAL_CHIP;

/** "3 kun qoldi" / "muddat o'tgan" — red once the deadline is behind us. */
export const dueClass = (days: number | null, overdue: boolean): string =>
  overdue
    ? "text-red-700 dark:text-red-300"
    : days !== null && days <= 3
      ? "text-amber-700 dark:text-amber-300"
      : "text-gray-600 dark:text-gray-300";

// --- notifications (S12) ----------------------------------------------------

const NOTIFICATION_TYPE_LABELS: Record<string, string> = uz.notifications.types;

export const notificationTypeLabel = (type: string): string =>
  NOTIFICATION_TYPE_LABELS[type] ?? uz.notifications.title;

/** `link_type` -> the page the bell opens. The table is the backend's
 * convention (services/notifications.py); money is the only role-dependent
 * one: a student has a contract page, a tutor/dean a group page. */
export function notificationHref(
  linkType: string | null,
  role: UserRole,
): string | null {
  switch (linkType) {
    case "flow_document":
      return "/docflow";
    case "schedule":
      return "/attendance";
    case "payment":
    case "contract":
      return role === "student" ? "/contract" : "/group";
    case "assignment":
      return "/documents";
    default:
      return null;
  }
}

/** Left border of a row: red for money/absence, amber for deadlines. */
export const notificationAccentClass = (type: string): string =>
  ({
    payment_debt: "border-l-red-500",
    teacher_absence: "border-l-red-500",
    class_absent: "border-l-red-500",
    flow_due: "border-l-amber-500",
    payment_uploaded: "border-l-amber-500",
    payment_confirmed: "border-l-emerald-500",
    flow_status: "border-l-sky-500",
    flow_incoming: "border-l-sky-500",
    new_assignment: "border-l-blue-500",
  })[type] ?? "border-l-gray-300 dark:border-l-gray-600";

/** Percentage colouring for the monthly report (same threshold as students). */
export const percentClass = (percent: number | null): string =>
  percent === null
    ? "text-gray-500 dark:text-gray-400"
    : percent >= 90
      ? "text-emerald-700 dark:text-emerald-300"
      : percent >= 75
        ? "text-amber-700 dark:text-amber-300"
        : "text-red-700 dark:text-red-300";
