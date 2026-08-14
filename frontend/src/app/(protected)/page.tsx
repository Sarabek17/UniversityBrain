"use client";

import { useAuth } from "@/lib/auth";
import uz from "@/i18n/uz.json";

export default function Home() {
  const { user } = useAuth();

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-4xl font-bold">{uz.home.title}</h1>
      <p className="text-lg text-gray-600 dark:text-gray-300">
        {uz.home.subtitle}
      </p>
      {user && (
        <p className="text-lg">
          {uz.home.welcome}, {user.full_name} ({uz.roles[user.role]})
        </p>
      )}
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {uz.home.status}
      </p>
    </main>
  );
}
