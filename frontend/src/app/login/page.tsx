"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError, type UserRole } from "@/lib/api";
import uz from "@/i18n/uz.json";

const DEMO_PASSWORD = "demo123";

const DEMO_USERS: { username: string; role: UserRole }[] = [
  { username: "aliyev", role: "student" },
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
        <p className="text-gray-500">{uz.common.loading}</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">{uz.login.title}</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-300">
          {uz.login.subtitle}
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="flex w-full max-w-sm flex-col gap-3 rounded-xl border border-gray-200 p-6 shadow-sm dark:border-gray-700"
      >
        <label className="flex flex-col gap-1 text-sm">
          {uz.login.username}
          <input
            className="rounded-md border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
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
            className="rounded-md border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? uz.login.submitting : uz.login.submit}
        </button>
      </form>

      <div className="w-full max-w-sm text-center">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {uz.login.demoTitle}
        </h2>
        <p className="mb-3 text-xs text-gray-500">{uz.login.demoHint}</p>
        <div className="flex flex-wrap justify-center gap-2">
          {DEMO_USERS.map((d) => (
            <button
              key={d.username}
              type="button"
              disabled={submitting}
              onClick={() => void doLogin(d.username, DEMO_PASSWORD)}
              className="rounded-full border border-blue-300 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50 disabled:opacity-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950"
            >
              {uz.roles[d.role]} · {d.username}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
