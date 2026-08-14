"use client";

// Document viewer: metadata + full text (GET /documents/{id}) plus the S6
// "Rezyume" action (POST /documents/{id}/summary) — the summary is rendered as
// its own closable block above the text, and never replaces the original.

import { useEffect, useState } from "react";
import {
  ApiError,
  documentsApi,
  type DocumentDetail,
  type DocumentSummary,
} from "@/lib/api";
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
  const [summary, setSummary] = useState<{
    id: number;
    data: DocumentSummary;
  } | null>(null);
  const [summaryFailed, setSummaryFailed] = useState<{
    id: number;
    message: string;
  } | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);

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

  const activeSummary =
    summary !== null && summary.id === documentId ? summary.data : null;
  const summaryError =
    summaryFailed !== null && summaryFailed.id === documentId
      ? summaryFailed.message
      : null;
  const summarizing = pendingId !== null && pendingId === documentId;
  const showSummaryBox =
    summarizing || activeSummary !== null || summaryError !== null;

  function handleSummarize() {
    if (document === null || summarizing) return;
    const id = document.id;
    setPendingId(id);
    setSummary(null);
    setSummaryFailed(null);
    documentsApi
      .summary(id)
      .then((data) => {
        setSummary({ id, data });
        setPendingId((current) => (current === id ? null : current));
      })
      .catch(() => {
        setSummaryFailed({ id, message: uz.documents.summaryError });
        setPendingId((current) => (current === id ? null : current));
      });
  }

  function handleCloseSummary() {
    setSummary(null);
    setSummaryFailed(null);
  }

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
        <div className="flex shrink-0 items-center gap-1.5">
          {document && (
            <button
              type="button"
              onClick={handleSummarize}
              disabled={summarizing}
              className="rounded-md border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200 dark:hover:bg-blue-900"
            >
              {summarizing ? uz.common.loading : uz.documents.summary}
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
            >
              {uz.common.close}
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3 text-sm">
        {documentId === null && (
          <p className="text-gray-500 dark:text-gray-400">
            {uz.documents.selectHint}
          </p>
        )}
        {loading && <p className="text-gray-500">{uz.common.loading}</p>}
        {error && <p className="text-red-600">{error}</p>}

        {showSummaryBox && (
          <section className="mb-4 rounded-lg border border-blue-200 bg-blue-50/70 p-3 dark:border-blue-900 dark:bg-blue-950/40">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-blue-800 dark:text-blue-200">
                {uz.documents.summaryTitle}
              </h3>
              {!summarizing && (
                <button
                  type="button"
                  onClick={handleCloseSummary}
                  className="shrink-0 rounded-md border border-blue-200 px-2 py-0.5 text-[11px] text-blue-800 hover:bg-blue-100 dark:border-blue-800 dark:text-blue-200 dark:hover:bg-blue-900"
                >
                  {uz.common.close}
                </button>
              )}
            </div>

            {summarizing && (
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                {uz.documents.summaryLoading}
              </p>
            )}
            {summaryError && <p className="mt-2 text-red-600">{summaryError}</p>}

            {activeSummary && !summarizing && (
              <>
                <div className="mt-2">
                  <Markdown text={activeSummary.summary} />
                </div>
                {activeSummary.parts > 1 && (
                  <p className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
                    {uz.documents.summaryParts} ({activeSummary.parts})
                  </p>
                )}
                {activeSummary.truncated && (
                  <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-300">
                    {uz.documents.summaryTruncated}
                  </p>
                )}
                <p className="mt-2 text-[11px] text-gray-600 dark:text-gray-300">
                  {uz.documents.summarySource}: {activeSummary.source.label}
                </p>
                <p className="mt-1 text-[11px] italic text-gray-500 dark:text-gray-400">
                  {activeSummary.disclaimer}
                </p>
              </>
            )}
          </section>
        )}

        {document && <Markdown text={document.text} />}
      </div>
    </div>
  );
}
