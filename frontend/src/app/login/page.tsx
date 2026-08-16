"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError, type UserRole } from "@/lib/api";
import uz from "@/i18n/uz.json";
import ThemeToggle from "@/components/ThemeToggle";

const DEMO_PASSWORD = "demo123";

// Both demo teachers are one click away: umarov marks attendance, tursunov is
// the "dars xavf ostida" case the dean's office sees.
const DEMO_USERS: { username: string; role: UserRole }[] = [
  { username: "aliyev", role: "student" },
  { username: "umarov", role: "teacher" },
  { username: "tursunov", role: "teacher" },
  { username: "nazarova", role: "tutor" },
  { username: "rashidova", role: "staff" },
  { username: "admin", role: "admin" },
];

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [loading, user, router]);

  async function doLogin(u: string, p: string) {
    setError(null);
    setSubmitting(true);
    try {
      await login(u, p);
      router.replace("/");
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? uz.login.error
          : String(e),
      );
      setSubmitting(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void doLogin(username, password);
  }

  if (loading || user) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-ink-faint">{uz.common.loading}</p>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="absolute right-6 top-6">
        <ThemeToggle />
      </div>
      <div className="text-center">
        <h1 className="text-3xl font-bold">{uz.login.title}</h1>
        <p className="mt-2 text-ink-soft">
          {uz.login.subtitle}
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="flex w-full max-w-sm flex-col gap-3 rounded-xl border border-line bg-surface p-6 shadow-sm"
      >
        <label className="flex flex-col gap-1 text-sm">
          {uz.login.username}
          <input
            className="rounded-md border border-line-strong px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          {uz.login.password}
          <input
            type="password"
            className="rounded-md border border-line-strong px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="text-sm text-bad">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded-md bg-accent px-4 py-2 font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
        >
          {submitting ? uz.login.submitting : uz.login.submit}
        </button>
      </form>

      <div className="w-full max-w-sm text-center">
        <h2 className="text-sm font-semibold text-ink-soft">
          {uz.login.demoTitle}
        </h2>
        <p className="mb-3 text-xs text-ink-faint">{uz.login.demoHint}</p>
        <div className="grid grid-cols-2 gap-2">
          {DEMO_USERS.map((d) => (
            <button
              key={d.username}
              type="button"
              disabled={submitting}
              onClick={() => void doLogin(d.username, DEMO_PASSWORD)}
              className="rounded-lg border border-line bg-surface px-3 py-2 text-left transition-colors hover:bg-raised disabled:opacity-50"
            >
              <span className="block text-sm font-medium text-ink">
                {uz.roles[d.role]}
              </span>
              <span className="block text-xs text-ink-faint">{d.username}</span>
            </button>
          ))}
        </div>
        <p className="mt-6 text-xs text-ink-faint">
          {uz.common.teacherHelpHint}{" "}
          <a
            href="https://twin.bmslab.uz/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-accent-ink hover:underline"
          >
            {uz.common.teacherHelpLink} ↗
          </a>
        </p>
      </div>
    </main>
  );
}
