"use client";

// Citation chips under an assistant answer. `label` arrives ready-made from the
// backend (schemas.ChatSource) — the frontend never composes citation text.

import type { ChatSource } from "@/lib/api";
import uz from "@/i18n/uz.json";

export default function SourceChips({
  sources,
  onOpenDocument,
}: {
  sources: ChatSource[];
  onOpenDocument: (documentId: number) => void;
}) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-gray-500 dark:text-gray-400">
        {uz.chat.sources}:
      </span>
      {sources.map((source, index) => {
        const openable = source.type === "document" && source.document_id !== null;
        const key = `${source.type}-${source.document_id ?? "x"}-${source.chunk_id ?? index}`;
        const className =
          "rounded-full border px-2.5 py-1 text-left text-xs leading-tight " +
          (openable
            ? "border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950"
            : "border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-300");

        if (!openable) {
          return (
            <span key={key} className={className}>
              {source.label}
            </span>
          );
        }
        return (
          <button
            key={key}
            type="button"
            title={source.heading ?? source.title ?? undefined}
            onClick={() => onOpenDocument(source.document_id as number)}
            className={className}
          >
            {source.label}
          </button>
        );
      })}
    </div>
  );
}
