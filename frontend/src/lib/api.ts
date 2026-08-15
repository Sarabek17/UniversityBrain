// Backend client — the ONLY place the frontend talks to the API from.

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "uniagent_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token === null) {
    window.localStorage.removeItem(TOKEN_KEY);
  } else {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(`API error ${status}`);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    // Expired/invalid token -> drop it and return to the login page.
    // (Not for /auth/login itself: a wrong password is handled by the form.)
    if (
      res.status === 401 &&
      path !== "/auth/login" &&
      typeof window !== "undefined"
    ) {
      setToken(null);
      if (window.location.pathname !== "/login") {
        // Module-level fetch layer has no access to useRouter(); a hard
        // redirect on an expired session is intentional (no basePath in use).
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign("/login");
      }
    }
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => null);
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "PATCH",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "DELETE" }),
};

/** The human message FastAPI put in `{"detail": "..."}`, when there is one. */
export function errorDetail(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  const body = error.detail;
  if (body !== null && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

export interface HealthOut {
  status: string;
  app: string;
}

export const getHealth = () => api.get<HealthOut>("/health");

// --- auth -------------------------------------------------------------------

export type UserRole = "student" | "teacher" | "tutor" | "staff" | "admin";

export interface UserOut {
  id: number;
  username: string;
  full_name: string;
  role: UserRole;
  group_id: number | null;
  faculty_id: number | null;
  language: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<TokenOut>("/auth/login", { username, password }),
  me: () => api.get<UserOut>("/auth/me"),
  logout: () => api.post<{ status: string }>("/auth/logout"),
};

// --- chat / agent (S4 API) --------------------------------------------------

/** One citation. `label` is the ready-made text shown on the chip. */
export interface ChatSource {
  type: string; // "document" | "schedule" | ...
  label: string;
  document_id: number | null;
  title: string | null;
  heading: string | null;
  order_index: number | null;
  chunk_id: number | null;
}

export interface ChatOut {
  conversation_id: number;
  text: string;
  sources: ChatSource[];
  disclaimer: string;
}

export interface ConversationOut {
  id: number;
  user_id: number;
  title: string | null;
  created_at: string;
}

export type ChatMessageRole = "user" | "assistant" | "tool";

export interface ChatMessageOut {
  id: number;
  conversation_id: number;
  role: ChatMessageRole;
  content: string;
  tool_name: string | null;
  sources: ChatSource[] | null;
  created_at: string;
}

export interface ConversationDetailOut extends ConversationOut {
  messages: ChatMessageOut[];
  disclaimer: string;
}

export const chatApi = {
  send: (message: string, conversationId?: number | null) =>
    api.post<ChatOut>("/chat", {
      message,
      conversation_id: conversationId ?? null,
    }),
  conversations: () => api.get<ConversationOut[]>("/chat/conversations"),
  conversation: (id: number) =>
    api.get<ConversationDetailOut>(`/chat/conversations/${id}`),
};

// --- documents (S5 API) -----------------------------------------------------

export type DocumentType =
  | "syllabus"
  | "order"
  | "assignment"
  | "literature"
  | "regulation"
  | "other";

export type AccessLevel =
  | "public"
  | "student"
  | "teacher"
  | "tutor"
  | "staff"
  | "admin";

export interface DocumentListItem {
  id: number;
  title: string;
  doc_type: DocumentType;
  language: string;
  access_level: AccessLevel;
  uploaded_at: string;
}

export interface DocumentDetail extends DocumentListItem {
  text: string;
}

/** Role-angled summary of one document (S6). `parts` > 1 means map-reduce. */
export interface DocumentSummary {
  document_id: number;
  title: string;
  summary: string;
  parts: number;
  truncated: boolean;
  source: ChatSource;
  disclaimer: string;
}

/** One aligned row of the side-by-side view (S7).
 *
 * The original always travels with the translation, so the viewer can put them
 * in the same row and never has to replace the source text (domain rule 4). */
export interface TranslationParagraph {
  index: number;
  original: string;
  translated: string;
}

/** Translation of one document (S7). `cached` = served without an LLM call. */
export interface DocumentTranslation {
  document_id: number;
  title: string;
  source_language: string;
  target_language: string;
  paragraph_count: number;
  paragraphs: TranslationParagraph[];
  cached: boolean;
  truncated: boolean;
  same_language: boolean;
  source: ChatSource;
  disclaimer: string;
}

export const TRANSLATION_LANGUAGES = ["uz", "ru", "en"] as const;

export const documentsApi = {
  list: () => api.get<DocumentListItem[]>("/documents"),
  get: (id: number) => api.get<DocumentDetail>(`/documents/${id}`),
  summary: (id: number) =>
    api.post<DocumentSummary>(`/documents/${id}/summary`),
  translate: (id: number, targetLanguage: string) =>
    api.post<DocumentTranslation>(
      `/documents/${id}/translate?target_language=${encodeURIComponent(targetLanguage)}`,
    ),
};

// --- payments (S8 API) ------------------------------------------------------

/** "uploaded" = student handed in a receipt, still waiting for the tutor. */
export type PaymentStatus = "automatic" | "uploaded" | "confirmed";

/** Contract state of one student: paid / partial / debtor. */
export type PaymentState = "paid" | "partial" | "debtor";

export interface PaymentRow {
  id: number;
  amount: number;
  paid_at: string;
  receipt_number: string | null;
  status: PaymentStatus;
  has_receipt_file: boolean;
}

/** One student's contract. `pending_amount` is money awaiting confirmation —
 * it does NOT reduce `remaining_amount` until a tutor confirms the receipt. */
export interface ContractSummary {
  student_id: number;
  username: string;
  student_name: string;
  group_id: number | null;
  group_name: string | null;
  academic_year: string;
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  remaining_amount: number;
  paid_percent: number;
  state: PaymentState;
  last_payment_at: string | null;
  payments: PaymentRow[];
  source: ChatSource;
  disclaimer: string;
}

export interface GroupPaymentRow {
  student_id: number;
  username: string;
  full_name: string;
  group_id: number | null;
  group_name: string | null;
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  remaining_amount: number;
  paid_percent: number;
  state: PaymentState;
  last_payment_at: string | null;
  pending_count: number;
}

/** Tutor dashboard: every student in scope, biggest debt first. */
export interface GroupPaymentSummary {
  group_ids: number[];
  group_names: string[];
  rows: GroupPaymentRow[];
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  remaining_amount: number;
  debtor_count: number;
  partial_count: number;
  paid_count: number;
  pending_count: number;
  source: ChatSource;
  disclaimer: string;
}

/** Structured receipt. The demo has no receipt image files, so the payment
 * record itself is the receipt (`file_available` is false and says so). */
export interface Receipt {
  payment_id: number;
  student_id: number;
  student_name: string;
  receipt_number: string | null;
  amount: number;
  paid_at: string;
  status: PaymentStatus;
  academic_year: string;
  method: string;
  file_available: boolean;
  note: string;
  source: ChatSource;
  disclaimer: string;
}

export const paymentsApi = {
  contract: () => api.get<ContractSummary>("/payments/contract"),
  studentContract: (studentId: number) =>
    api.get<ContractSummary>(`/payments/contract/${studentId}`),
  group: (groupId?: number | null) =>
    api.get<GroupPaymentSummary>(
      groupId == null ? "/payments/group" : `/payments/group?group_id=${groupId}`,
    ),
  receipt: (paymentId: number) =>
    api.get<Receipt>(`/payments/${paymentId}/receipt`),
  uploadReceipt: (amount: number, receiptNumber?: string | null) =>
    api.post<ContractSummary>("/payments/receipts", {
      amount,
      receipt_number: receiptNumber?.trim() ? receiptNumber.trim() : null,
    }),
  confirm: (paymentId: number) =>
    api.post<ContractSummary>(`/payments/${paymentId}/confirm`),
};

// --- presence / attendance (S9 API) -----------------------------------------

/** Where the turnstile last saw someone today. */
export type PresenceState = "inside" | "left" | "not_arrived";

export type AttendanceStatus = "present" | "absent" | "late";

export type ClassSessionStatus = "held" | "cancelled" | "needs_clarification";

/** The class someone is *supposed* to be in — a schedule-based inference, so
 * the UI always shows it together with the "jadval bo'yicha" note. */
export interface PresenceClass {
  schedule_id: number;
  pair_number: number;
  subject: string;
  room: string;
  group_id: number;
  group_name: string | null;
  teacher_id: number;
  teacher_name: string | null;
  starts_at: string;
  ends_at: string;
  session_status: ClassSessionStatus | null;
  attendance_status: AttendanceStatus | null;
}

export interface DayAttendance {
  total: number;
  present: number;
  late: number;
  absent: number;
  percent: number | null;
}

export interface Presence {
  user_id: number;
  username: string;
  full_name: string;
  role: UserRole;
  group_id: number | null;
  group_name: string | null;
  at: string;
  state: PresenceState;
  state_label: string;
  in_building: boolean;
  entered_at: string | null;
  left_at: string | null;
  last_event_at: string | null;
  current_pair: number | null;
  current_class: PresenceClass | null;
  next_class: PresenceClass | null;
  attendance_status: AttendanceStatus | null;
  attendance_marked: boolean;
  day: DayAttendance;
  summary: string;
  schedule_note: string;
  sources: ChatSource[];
  disclaimer: string;
}

export interface GroupPresenceRow {
  student_id: number;
  username: string;
  full_name: string;
  group_id: number | null;
  group_name: string | null;
  state: PresenceState;
  state_label: string;
  entered_at: string | null;
  left_at: string | null;
  pair_number: number | null;
  subject: string | null;
  room: string | null;
  attendance_status: AttendanceStatus | null;
  attendance_marked: boolean;
  attendance_percent: number | null;
  attended_count: number;
  marked_count: number;
  summary: string;
}

export interface GroupPresence {
  group_ids: number[];
  group_names: string[];
  at: string;
  current_pair: number | null;
  pair_label: string | null;
  rows: GroupPresenceRow[];
  inside_count: number;
  left_count: number;
  absent_count: number;
  in_class_count: number;
  attendance_percent: number | null;
  schedule_note: string;
  source: ChatSource;
  disclaimer: string;
}

export interface TeacherClass {
  schedule_id: number;
  pair_number: number;
  subject: string;
  room: string;
  group_id: number;
  group_name: string | null;
  starts_at: string;
  ends_at: string;
  session_status: ClassSessionStatus | null;
  session_label: string | null;
  student_count: number;
  marked_count: number;
  present_count: number;
  is_current: boolean;
  is_past: boolean;
}

export interface TeacherDay {
  date: string;
  teacher_id: number;
  teacher_name: string;
  current_pair: number | null;
  classes: TeacherClass[];
  disclaimer: string;
}

/** One line of the marking sheet. `suggested` is the turnstile-based hint the
 * "bir klik" button fills in; `status` is what the journal says right now. */
export interface RosterStudent {
  student_id: number;
  username: string;
  full_name: string;
  status: AttendanceStatus | null;
  suggested: AttendanceStatus;
  state: PresenceState;
  state_label: string;
  entered_at: string | null;
  left_at: string | null;
}

export interface ClassRoster {
  schedule_id: number;
  date: string;
  pair_number: number;
  pair_label: string;
  subject: string;
  room: string;
  group_id: number;
  group_name: string | null;
  teacher_id: number;
  teacher_name: string | null;
  starts_at: string;
  ends_at: string;
  session_status: ClassSessionStatus | null;
  session_label: string | null;
  can_mark: boolean;
  students: RosterStudent[];
  marked_count: number;
  present_count: number;
  late_count: number;
  absent_count: number;
  schedule_note: string;
  source: ChatSource;
  disclaimer: string;
}

export interface SubjectAttendance {
  subject: string;
  total: number;
  attended: number;
  absent: number;
  percent: number;
}

export interface AttendanceRow {
  date: string;
  pair_number: number;
  subject: string;
  room: string;
  status: AttendanceStatus;
  status_label: string;
}

export interface AttendanceSummary {
  student_id: number;
  username: string;
  full_name: string;
  group_id: number | null;
  group_name: string | null;
  days: number;
  date_from: string;
  date_to: string;
  total: number;
  present: number;
  late: number;
  absent: number;
  percent: number | null;
  by_subject: SubjectAttendance[];
  recent: AttendanceRow[];
  today: DayAttendance;
  source: ChatSource;
  disclaimer: string;
}

// --- teacher attendance, dean's view (S10 API) ------------------------------

/** Derived state of one scheduled class — a conclusion drawn at a moment in
 * time, not the stored `session_status` (which travels alongside it). */
export type ClassState =
  | "held"
  | "late"
  | "at_risk"
  | "needs_clarification"
  | "upcoming"
  | "cancelled";

export interface TeacherClassState {
  schedule_id: number;
  pair_number: number;
  subject: string;
  room: string;
  group_id: number;
  group_name: string | null;
  starts_at: string;
  ends_at: string;
  session_status: ClassSessionStatus | null;
  session_label: string | null;
  state: ClassState;
  state_label: string;
  teacher_arrived_at: string | null;
  student_count: number;
  marked_count: number;
  present_count: number;
  is_current: boolean;
  is_past: boolean;
  summary: string;
}

export interface TeacherPresenceRow {
  teacher_id: number;
  username: string;
  full_name: string;
  faculty_id: number | null;
  state: PresenceState;
  state_label: string;
  in_building: boolean;
  entered_at: string | null;
  left_at: string | null;
  classes: TeacherClassState[];
  class_count: number;
  held_count: number;
  late_count: number;
  at_risk_count: number;
  unclear_count: number;
  summary: string;
}

export interface TeacherDayOverview {
  date: string;
  at: string;
  current_pair: number | null;
  pair_label: string | null;
  faculty_ids: number[];
  rows: TeacherPresenceRow[];
  teacher_count: number;
  inside_count: number;
  left_count: number;
  absent_count: number;
  class_count: number;
  held_count: number;
  late_count: number;
  at_risk_count: number;
  unclear_count: number;
  schedule_note: string;
  source: ChatSource;
  disclaimer: string;
}

export interface TeacherMonthRow {
  teacher_id: number;
  username: string;
  full_name: string;
  total: number;
  held: number;
  late: number;
  cancelled: number;
  unclear: number;
  percent: number | null;
}

export interface TeacherMonth {
  date_from: string;
  date_to: string;
  days: number;
  rows: TeacherMonthRow[];
  total: number;
  held: number;
  late: number;
  cancelled: number;
  unclear: number;
  percent: number | null;
  source: ChatSource;
  disclaimer: string;
}

function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const attendanceApi = {
  presence: (at?: string | null) =>
    api.get<Presence>(`/attendance/presence${query({ at })}`),
  userPresence: (userId: number, at?: string | null) =>
    api.get<Presence>(`/attendance/presence/${userId}${query({ at })}`),
  group: (groupId?: number | null, at?: string | null) =>
    api.get<GroupPresence>(`/attendance/group${query({ group_id: groupId, at })}`),
  summary: (studentId?: number | null, days?: number | null) =>
    api.get<AttendanceSummary>(
      `/attendance/summary${query({ student_id: studentId, days })}`,
    ),
  myClasses: (onDate?: string | null) =>
    api.get<TeacherDay>(`/attendance/my-classes${query({ on_date: onDate })}`),
  roster: (scheduleId: number, onDate?: string | null) =>
    api.get<ClassRoster>(
      `/attendance/class/${scheduleId}${query({ on_date: onDate })}`,
    ),
  mark: (
    scheduleId: number,
    marks: { student_id: number; status: AttendanceStatus }[],
    onDate?: string | null,
  ) =>
    api.post<ClassRoster>(`/attendance/class/${scheduleId}/mark`, {
      marks,
      on_date: onDate ?? null,
    }),
  // Dean's office only (403 for every other role).
  teachers: (onDate?: string | null, at?: string | null) =>
    api.get<TeacherDayOverview>(
      `/attendance/teachers${query({ on_date: onDate, at })}`,
    ),
  teachersMonthly: (days?: number | null) =>
    api.get<TeacherMonth>(`/attendance/teachers/monthly${query({ days })}`),
};

// --- document flow (S11 API) ------------------------------------------------

export type FlowDocumentType = "application" | "report" | "order" | "letter";

/** The status chain: sent -> seen -> in_progress -> approved | rejected. */
export type FlowStatus =
  | "sent"
  | "seen"
  | "in_progress"
  | "approved"
  | "rejected";

export type FlowBox = "inbox" | "outbox";
export type FlowSort = "new" | "due";

/** One entry of the template catalogue — already filtered by the caller's role. */
export interface FlowTemplate {
  id: string;
  title: string;
  description: string;
  doc_type: FlowDocumentType;
  doc_type_label: string;
  recipient_role: UserRole | null;
  recipient_label: string;
  needs_recipient_user: boolean;
  needs_due_date: boolean;
  body_hint: string;
}

export interface FlowRecipient {
  id: number;
  full_name: string;
  role: UserRole;
  role_label: string;
}

export interface FlowHistoryItem {
  id: number;
  status: FlowStatus;
  status_label: string;
  comment: string | null;
  timestamp: string;
  changed_by_id: number;
  changed_by_name: string;
}

/** One row of an inbox / outbox list. `can_change_status` is the backend's
 * answer, not a role guess: only the recipient of an open document may act. */
export interface FlowItem {
  id: number;
  doc_type: FlowDocumentType;
  doc_type_label: string;
  template_id: string | null;
  title: string;
  sender_id: number;
  sender_name: string;
  sender_role: UserRole;
  recipient_role: UserRole | null;
  recipient_user_id: number | null;
  recipient_label: string;
  status: FlowStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
  due_date: string | null;
  due_in_days: number | null;
  overdue: boolean;
  is_incoming: boolean;
  is_outgoing: boolean;
  can_change_status: boolean;
  last_comment: string | null;
  preview: string;
}

export interface FlowDetail extends FlowItem {
  body_text: string;
  history: FlowHistoryItem[];
  next_statuses: FlowStatus[];
  source: ChatSource;
  disclaimer: string;
}

export interface FlowList {
  box: FlowBox;
  sort: FlowSort;
  rows: FlowItem[];
  total: number;
  new_count: number;
  open_count: number;
  overdue_count: number;
  due_soon_count: number;
  source: ChatSource;
  disclaimer: string;
}

/** Summary of an incoming document — the same S6 service the viewer uses. */
export interface FlowSummary {
  flow_id: number;
  title: string;
  summary: string;
  parts: number;
  truncated: boolean;
  source: ChatSource;
  disclaimer: string;
}

export interface FlowCreateInput {
  template_id: string;
  body_text: string;
  recipient_user_id?: number | null;
  due_date?: string | null;
}

export const docflowApi = {
  templates: () => api.get<FlowTemplate[]>("/docflow/templates"),
  recipients: () => api.get<FlowRecipient[]>("/docflow/recipients"),
  list: (box: FlowBox, sort?: FlowSort | null) =>
    api.get<FlowList>(`/docflow/${box}${query({ sort })}`),
  get: (id: number) => api.get<FlowDetail>(`/docflow/${id}`),
  create: (input: FlowCreateInput) =>
    api.post<FlowDetail>("/docflow", {
      template_id: input.template_id,
      body_text: input.body_text,
      recipient_user_id: input.recipient_user_id ?? null,
      due_date: input.due_date ?? null,
    }),
  changeStatus: (id: number, status: FlowStatus, comment?: string | null) =>
    api.post<FlowDetail>(`/docflow/${id}/status`, {
      status,
      comment: comment?.trim() ? comment.trim() : null,
    }),
  summary: (id: number) => api.post<FlowSummary>(`/docflow/${id}/summary`),
};

// --- notifications (S12) ----------------------------------------------------

/** Backend `notif_type` values (services/notifications.py). */
export type NotificationType =
  | "flow_status"
  | "flow_incoming"
  | "flow_due"
  | "teacher_absence"
  | "payment_uploaded"
  | "payment_confirmed"
  | "payment_debt"
  | "class_absent"
  | "new_assignment";

/** What the notification points at; the UI turns it into a page (labels.ts). */
export type NotificationLink =
  | "flow_document"
  | "schedule"
  | "payment"
  | "contract"
  | "assignment";

export interface NotificationItem {
  id: number;
  user_id: number;
  notif_type: NotificationType | string;
  text: string;
  link_type: NotificationLink | string | null;
  link_id: number | null;
  is_read: boolean;
  created_at: string;
}

/** The bell in one answer: the page **and** the unread counter. */
export interface NotificationList {
  rows: NotificationItem[];
  total: number;
  unread_count: number;
  unread_only: boolean;
  limit: number;
}

export const notificationsApi = {
  list: (unread?: boolean, limit?: number | null) =>
    api.get<NotificationList>(
      `/notifications${query({ unread: unread ? "true" : null, limit })}`,
    ),
  // Both writes answer with the refreshed list, so the bell never needs a
  // second request to update its counter.
  read: (id: number) =>
    api.post<NotificationList>(`/notifications/${id}/read`),
  readAll: () => api.post<NotificationList>("/notifications/read-all"),
};
