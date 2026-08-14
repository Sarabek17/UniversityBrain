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
