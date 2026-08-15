"use client";

// Documents the current user may see (GET /documents — role filter is applied
// on the backend, so this list simply shows what came back).

import type { DocumentListItem } from "@/lib/api";
import { accessLabel, docTypeLabel, languageLabel } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function DocumentList({
  documents,
  activeId,
  loading,
  error,
  onSelect,
}: {
  documents: DocumentListItem[];
  activeId: number | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h2 className="px-3 py-3 text-sm font-semibold">
        {uz.documents.listTitle}
      </h2>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && (
          <p className="px-1 text-xs text-ink-faint">{uz.common.loading}</p>
        )}
        {error && <p className="px-1 text-xs text-bad">{error}</p>}
        {!loading && !error && documents.length === 0 && (
          <p className="px-1 text-xs text-ink-faint">{uz.documents.empty}</p>
        )}
        <ul className="flex flex-col gap-1">
          {documents.map((document) => (
            <li key={document.id}>
              <button
                type="button"
                onClick={() => onSelect(document.id)}
                className={
                  "w-full rounded-md px-2 py-2 text-left " +
                  (document.id === activeId
                    ? "bg-raised text-ink"
                    : "hover:bg-raised")
                }
              >
                <span className="block text-xs font-medium">
                  {document.title}
                </span>
                <span className="mt-0.5 block text-[10px] text-ink-faint">
                  {docTypeLabel(document.doc_type)} ·{" "}
                  {languageLabel(document.language)} ·{" "}
                  {accessLabel(document.access_level)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
