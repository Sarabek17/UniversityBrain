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
