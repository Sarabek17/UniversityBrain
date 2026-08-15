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
      <span className="text-xs text-ink-faint">
        {uz.chat.sources}:
      </span>
      {sources.map((source, index) => {
        const openable = source.type === "document" && source.document_id !== null;
        const key = `${source.type}-${source.document_id ?? "x"}-${source.chunk_id ?? index}`;
        const className =
          "rounded-full border px-2.5 py-1 text-left text-xs leading-tight " +
          (openable
            ? "border-line-strong text-accent-ink hover:bg-raised"
            : "border-line-strong text-ink-soft");

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
