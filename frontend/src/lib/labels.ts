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
    paid: "bg-ok-soft text-ok",
    partial: "bg-warn-soft text-warn",
    debtor: "bg-bad-soft text-bad",
  })[state] ?? "bg-raised text-ink-soft";

// --- presence / attendance (S9) ---------------------------------------------

const NEUTRAL_CHIP =
  "bg-raised text-ink-soft";

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
    inside: "bg-ok-soft text-ok",
    left: "bg-warn-soft text-warn",
    not_arrived: "bg-bad-soft text-bad",
  })[state] ?? NEUTRAL_CHIP;

export const attendanceStatusLabel = (status: AttendanceStatus): string =>
  uz.attendance.statuses[status] ?? status;

export const attendanceStatusClass = (status: AttendanceStatus | null): string =>
  status === null
    ? NEUTRAL_CHIP
    : ({
        present:
          "bg-ok-soft text-ok",
        late: "bg-warn-soft text-warn",
        absent: "bg-bad-soft text-bad",
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
    held: "bg-ok-soft text-ok",
    at_risk: "bg-bad-soft text-bad",
    needs_clarification:
      "bg-warn-soft text-warn",
    late: "bg-warn-soft text-warn",
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
    sent: "bg-raised text-ink-soft",
    seen: "bg-accent-soft text-accent-ink",
    in_progress: "bg-warn-soft text-warn",
    approved:
      "bg-ok-soft text-ok",
    rejected: "bg-bad-soft text-bad",
  })[status] ?? NEUTRAL_CHIP;

/** "3 kun qoldi" / "muddat o'tgan" — red once the deadline is behind us. */
export const dueClass = (days: number | null, overdue: boolean): string =>
  overdue
    ? "text-bad"
    : days !== null && days <= 3
      ? "text-warn"
      : "text-ink-soft";

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
    case "document":
      return "/documents";
    default:
      return null;
  }
}

/** Left border of a row: red for money/absence, amber for deadlines. */
export const notificationAccentClass = (type: string): string =>
  ({
    payment_debt: "border-l-bad",
    teacher_absence: "border-l-bad",
    class_absent: "border-l-bad",
    flow_due: "border-l-warn",
    payment_uploaded: "border-l-warn",
    payment_confirmed: "border-l-ok",
    flow_status: "border-l-accent",
    flow_incoming: "border-l-accent",
    new_assignment: "border-l-accent",
    new_order: "border-l-accent",
  })[type] ?? "border-l-line-strong";

/** Percentage colouring for the monthly report (same threshold as students). */
export const percentClass = (percent: number | null): string =>
  percent === null
    ? "text-ink-faint"
    : percent >= 90
      ? "text-ok"
      : percent >= 75
        ? "text-warn"
        : "text-bad";
