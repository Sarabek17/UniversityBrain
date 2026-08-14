"use client";

// Placeholder rail for the roles that get a dashboard next to the chat
// (teacher / tutor / staff / admin). Later sessions fill it with real widgets;
// students keep the chat centered with no rail.

import type { UserRole } from "@/lib/api";
import uz from "@/i18n/uz.json";

const DASHBOARD_ROLES: UserRole[] = ["teacher", "tutor", "staff", "admin"];

export const hasDashboard = (role: UserRole): boolean =>
  DASHBOARD_ROLES.includes(role);

export default function RoleDashboard({ role }: { role: UserRole }) {
  if (!hasDashboard(role)) return null;
  const item =
    uz.dashboard.items[role as "teacher" | "tutor" | "staff" | "admin"];

  return (
    <div className="flex min-h-0 flex-1 flex-col px-4 py-4">
      <h2 className="text-sm font-semibold">{uz.dashboard.title}</h2>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
        {uz.roles[role]}
      </p>
      <div className="mt-3 flex flex-col gap-2">
        <div className="rounded-lg border border-dashed border-gray-300 px-3 py-4 text-xs text-gray-600 dark:border-gray-600 dark:text-gray-300">
          {item}
        </div>
        <div className="rounded-lg border border-dashed border-gray-300 px-3 py-4 text-xs text-gray-500 dark:border-gray-600 dark:text-gray-400">
          {uz.dashboard.placeholder}
        </div>
      </div>
      <p className="mt-4 text-[11px] text-gray-500 dark:text-gray-400">
        {uz.documents.panelHint}
      </p>
    </div>
  );
}
