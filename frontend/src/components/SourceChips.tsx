"use client";

// Citation chips under an assistant answer — Claude-style compact citations:
// a numbered badge + document title + (truncated) section, the FULL backend
// `label` stays available in the tooltip. The frontend still never composes
// citation text (schemas.ChatSource), it only trims what it shows.

import type { ChatSource } from "@/lib/api";
import uz from "@/i18n/uz.json";

export default function SourceChips({
  sources,
  onOpenDocument,
}: {
  sources: ChatSource[];
  onOpenDocument: (documentId: number, heading?: string | null) => void;
}) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-ink-faint">{uz.chat.sources}:</span>
      {sources.map((source, index) => {
        const openable =
          source.type === "document" && source.document_id !== null;
        const key = `${source.type}-${source.document_id ?? "x"}-${source.chunk_id ?? index}`;
        // heading may chain several sections with "·" — the first one is
        // where the chunk starts, enough for a compact chip
        const section = source.heading?.split("·")[0].trim() ?? null;
        const title = source.title ?? source.label;

        const inner = (
          <>
            <span
              className={
                "flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold " +
                (openable
                  ? "bg-accent-soft text-accent-ink"
                  : "bg-raised text-ink-faint")
              }
            >
              {index + 1}
            </span>
            <span className="max-w-[16rem] truncate text-ink-soft">
              {title}
            </span>
            {section && (
              <span className="hidden max-w-[11rem] truncate text-ink-faint sm:inline">
                {section}
              </span>
            )}
          </>
        );

        const className =
          "inline-flex max-w-full items-center gap-1.5 rounded-full border border-line-strong px-2 py-1 text-left text-xs leading-tight" +
          (openable ? " transition-colors hover:border-accent-line hover:bg-raised" : "");

        if (!openable) {
          return (
            <span key={key} title={source.label} className={className}>
              {inner}
            </span>
          );
        }
        return (
          <button
            key={key}
            type="button"
            title={source.label}
            onClick={() =>
              onOpenDocument(source.document_id as number, source.heading)
            }
            className={className}
          >
            {inner}
          </button>
        );
      })}
    </div>
  );
}
