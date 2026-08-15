"use client";

// Protected area: unauthenticated users are redirected to /login;
// authenticated ones see the header (nav + name + role + logout).
// Fixed viewport height — each page scrolls its own columns.

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/api";
import uz from "@/i18n/uz.json";

// `roles: null` = everyone. Money pages follow the backend rule: the student
// sees their own contract, the tutor/dean office the group summary, teachers
// neither (FUNKSIONALLIK 3.6).
const NAV: { href: string; label: string; roles: UserRole[] | null }[] = [
  { href: "/chat", label: uz.nav.chat, roles: null },
  { href: "/documents", label: uz.nav.documents, roles: null },
  { href: "/contract", label: uz.nav.contract, roles: ["student"] },
  { href: "/group", label: uz.nav.group, roles: ["tutor", "staff", "admin"] },
  // Presence + attendance: the same page answers a different question per role
  // (teacher marks, tutor/dean watch the group, student sees their own record).
  { href: "/attendance", label: uz.nav.attendance, roles: null },
  // Document flow: the student tracks their application, the teacher hands in
  // reports, the dean's office decides — one page, three questions.
  { href: "/docflow", label: uz.nav.docflow, roles: null },
];

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

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
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-3 dark:border-gray-700">
        <div className="flex items-center gap-6">
          <span className="font-bold">{uz.home.title}</span>
          <nav className="flex items-center gap-1">
            {NAV.filter(
              (item) => item.roles === null || item.roles.includes(user.role),
            ).map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "rounded-md px-3 py-1.5 text-sm " +
                  (pathname === item.href
                    ? "bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                    : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800")
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
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
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
