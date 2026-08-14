"use client";

// Document viewer: metadata + full text (GET /documents/{id}).
// Used both in the chat right rail (opened by a source chip) and on the
// documents page. S6 adds a "Rezyume" button to the header actions row.

import { useEffect, useState } from "react";
import { ApiError, documentsApi, type DocumentDetail } from "@/lib/api";
import { accessLabel, docTypeLabel, formatDate, languageLabel } from "@/lib/labels";
import Markdown from "@/components/Markdown";
import uz from "@/i18n/uz.json";

export default function DocumentPanel({
  documentId,
  onClose,
}: {
  documentId: number | null;
  onClose?: () => void;
}) {
  const [loaded, setLoaded] = useState<DocumentDetail | null>(null);
  const [failed, setFailed] = useState<{ id: number; message: string } | null>(
    null,
  );

  useEffect(() => {
    if (documentId === null) return;
    let cancelled = false;
    documentsApi
      .get(documentId)
      .then((detail) => {
        if (!cancelled) setLoaded(detail);
      })
      .catch((e) => {
        if (cancelled) return;
        setFailed({
          id: documentId,
          message:
            e instanceof ApiError && e.status === 404
              ? uz.documents.notFound
              : uz.documents.loadError,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  // Derived, so switching documents never needs a setState-in-effect reset.
  const document = loaded !== null && loaded.id === documentId ? loaded : null;
  const error = failed !== null && failed.id === documentId ? failed.message : null;
  const loading = documentId !== null && document === null && error === null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-start justify-between gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">
            {document?.title ?? uz.documents.title}
          </h2>
          {document && (
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {docTypeLabel(document.doc_type)}
              </span>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {languageLabel(document.language)}
              </span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                {accessLabel(document.access_level)}
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                {formatDate(document.uploaded_at)}
              </span>
            </div>
          )}
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {uz.common.close}
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3 text-sm">
        {documentId === null && (
          <p className="text-gray-500 dark:text-gray-400">
            {uz.documents.selectHint}
          </p>
        )}
        {loading && <p className="text-gray-500">{uz.common.loading}</p>}
        {error && <p className="text-red-600">{error}</p>}
        {document && <Markdown text={document.text} />}
      </div>
    </div>
  );
}
