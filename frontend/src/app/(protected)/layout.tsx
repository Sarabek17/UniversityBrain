"use client";

// Protected area: unauthenticated users are redirected to /login;
// authenticated ones see the header (nav + name + role + logout).
// Fixed viewport height — each page scrolls its own columns.

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/api";
import NotifBell from "@/components/NotifBell";
import ThemeToggle from "@/components/ThemeToggle";
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
  // Management panel: users, document upload and the demo reset (S13).
  { href: "/admin", label: uz.nav.admin, roles: ["admin"] },
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
        <p className="text-ink-faint">{uz.common.loading}</p>
      </main>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-line px-3 py-2 md:px-6 md:py-3">
        <div className="flex min-w-0 items-center gap-2 md:gap-6">
          <span className="flex items-center gap-2 font-bold">
            {/* terracotta spark mark — the product logo */}
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              className="h-4.5 w-4.5 text-accent-ink"
            >
              <path d="M12 3v5M12 16v5M3 12h5M16 12h5M5.6 5.6l3.5 3.5M14.9 14.9l3.5 3.5M18.4 5.6l-3.5 3.5M9.1 14.9l-3.5 3.5" />
            </svg>
            {uz.home.title}
          </span>
          <nav className="flex items-center gap-1 overflow-x-auto whitespace-nowrap">
            {NAV.filter(
              (item) => item.roles === null || item.roles.includes(user.role),
            ).map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "rounded-md px-3 py-1.5 text-sm " +
                  (pathname === item.href
                    ? "bg-raised font-medium text-ink"
                    : "text-ink-soft hover:bg-raised")
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          {/* Virtaks — the teacher's digital twin (external help resource) */}
          <a
            href="https://twin.virtaks.uz"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-ink-soft hover:bg-raised"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <path d="M12 4 2 9l10 5 10-5-10-5z" />
              <path d="M6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5" />
            </svg>
            <span className="hidden md:inline">{uz.common.teacherHelp}</span>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-3 w-3 text-ink-faint"
            >
              <path d="M7 17 17 7M9 7h8v8" />
            </svg>
          </a>
          <ThemeToggle />
          <NotifBell role={user.role} />
          <span className="hidden text-sm md:inline">
            {user.full_name}
            <span className="ml-2 rounded-full bg-raised px-2 py-0.5 text-xs text-ink-soft">
              {uz.roles[user.role]}
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="rounded-md border border-line-strong px-3 py-1.5 text-sm hover:bg-raised"
          >
            {uz.header.logout}
          </button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
