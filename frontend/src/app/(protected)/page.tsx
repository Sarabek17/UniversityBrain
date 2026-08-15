"use client";

// The chat is the landing screen after login; "/" only forwards to it.
// Later sessions may turn this route into a role dashboard.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import uz from "@/i18n/uz.json";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/chat");
  }, [router]);

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <p className="text-sm text-ink-faint">{uz.common.loading}</p>
    </main>
  );
}
