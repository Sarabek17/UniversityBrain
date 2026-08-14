"use client";

// Protected area: unauthenticated users are redirected to /login;
// authenticated ones see the header (name + role + logout).

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import uz from "@/i18n/uz.json";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">{uz.common.loading}</p>
      </main>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-gray-200 px-6 py-3 dark:border-gray-700">
        <span className="font-bold">{uz.home.title}</span>
        <div className="flex items-center gap-4">
          <span className="text-sm">
            {user.full_name}
            <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {uz.roles[user.role]}
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {uz.header.logout}
          </button>
        </div>
      </header>
      <div className="flex flex-1 flex-col">{children}</div>
    </div>
  );
}
