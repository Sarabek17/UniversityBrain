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
