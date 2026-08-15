"use client";

// Document viewer: metadata + full text (GET /documents/{id}) plus two actions
// that never replace the original:
//   * S6 "Rezyume" (POST /documents/{id}/summary) — a closable block above the
//     text,
//   * S7 "Tarjima" (POST /documents/{id}/translate) — side-by-side mode, where
//     the left column IS the original, paragraph by paragraph. One scroll
//     container holds both columns, so the two sides can never drift apart.

import { useEffect, useState } from "react";
import {
  ApiError,
  documentsApi,
  TRANSLATION_LANGUAGES,
  type DocumentDetail,
  type DocumentSummary,
  type DocumentTranslation,
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
  const [targetLanguage, setTargetLanguage] = useState<string>("uz");
  const [translation, setTranslation] = useState<{
    key: string;
    data: DocumentTranslation;
  } | null>(null);
  const [translationFailed, setTranslationFailed] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [translatingKey, setTranslatingKey] = useState<string | null>(null);

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

  // Derived the same way, but keyed by document *and* language: picking another
  // language simply stops matching and falls back to the plain view.
  const translationKey =
    documentId === null ? null : `${documentId}:${targetLanguage}`;
  const activeTranslation =
    translation !== null && translation.key === translationKey
      ? translation.data
      : null;
  const translationError =
    translationFailed !== null && translationFailed.key === translationKey
      ? translationFailed.message
      : null;
  const translating =
    translatingKey !== null && translatingKey === translationKey;
  const showTranslationBox =
    translating || activeTranslation !== null || translationError !== null;

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

  function handleTranslate() {
    if (document === null || translationKey === null || translating) return;
    const key = translationKey;
    setTranslatingKey(key);
    setTranslation(null);
    setTranslationFailed(null);
    documentsApi
      .translate(document.id, targetLanguage)
      .then((data) => {
        setTranslation({ key, data });
        setTranslatingKey((current) => (current === key ? null : current));
      })
      .catch(() => {
        setTranslationFailed({ key, message: uz.documents.translateError });
        setTranslatingKey((current) => (current === key ? null : current));
      });
  }

  function handleCloseTranslation() {
    setTranslation(null);
    setTranslationFailed(null);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-start justify-between gap-2 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">
            {document?.title ?? uz.documents.title}
          </h2>
          {document && (
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="rounded-full bg-raised px-2 py-0.5 text-ink-soft">
                {docTypeLabel(document.doc_type)}
              </span>
              <span className="rounded-full bg-raised px-2 py-0.5 text-ink-soft">
                {languageLabel(document.language)}
              </span>
              <span className="rounded-full bg-warn-soft px-2 py-0.5 text-warn">
                {accessLabel(document.access_level)}
              </span>
              <span className="text-ink-faint">
                {formatDate(document.uploaded_at)}
              </span>
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          {document && (
            <button
              type="button"
              onClick={handleSummarize}
              disabled={summarizing}
              className="rounded-md border border-line-strong px-2 py-1 text-xs font-medium text-ink-soft hover:bg-raised disabled:cursor-not-allowed disabled:opacity-60"
            >
              {summarizing ? uz.common.loading : uz.documents.summary}
            </button>
          )}
          {document && (
            <>
              <select
                value={targetLanguage}
                onChange={(event) => setTargetLanguage(event.target.value)}
                aria-label={uz.documents.translateLanguage}
                className="rounded-md border border-line-strong bg-transparent px-1.5 py-1 text-xs"
              >
                {TRANSLATION_LANGUAGES.map((code) => (
                  <option key={code} value={code}>
                    {languageLabel(code)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleTranslate}
                disabled={translating}
                className="rounded-md border border-ok-line bg-ok-soft px-2 py-1 text-xs font-medium text-ok hover:bg-ok-soft disabled:cursor-not-allowed disabled:opacity-60"
              >
                {translating ? uz.common.loading : uz.documents.translate}
              </button>
            </>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-line-strong px-2 py-1 text-xs hover:bg-raised"
            >
              {uz.common.close}
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3 text-sm">
        {documentId === null && (
          <p className="text-ink-faint">
            {uz.documents.selectHint}
          </p>
        )}
        {loading && <p className="text-ink-faint">{uz.common.loading}</p>}
        {error && <p className="text-bad">{error}</p>}

        {showSummaryBox && (
          <section className="mb-4 rounded-lg border border-accent-line bg-accent-soft p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-accent-ink">
                {uz.documents.summaryTitle}
              </h3>
              {!summarizing && (
                <button
                  type="button"
                  onClick={handleCloseSummary}
                  className="shrink-0 rounded-md border border-line-strong px-2 py-0.5 text-[11px] text-ink-soft hover:bg-raised"
                >
                  {uz.common.close}
                </button>
              )}
            </div>

            {summarizing && (
              <p className="mt-2 text-ink-soft">
                {uz.documents.summaryLoading}
              </p>
            )}
            {summaryError && <p className="mt-2 text-bad">{summaryError}</p>}

            {activeSummary && !summarizing && (
              <>
                <div className="mt-2">
                  <Markdown text={activeSummary.summary} />
                </div>
                {activeSummary.parts > 1 && (
                  <p className="mt-2 text-[11px] text-ink-faint">
                    {uz.documents.summaryParts} ({activeSummary.parts})
                  </p>
                )}
                {activeSummary.truncated && (
                  <p className="mt-1 text-[11px] text-warn">
                    {uz.documents.summaryTruncated}
                  </p>
                )}
                <p className="mt-2 text-[11px] text-ink-soft">
                  {uz.documents.summarySource}: {activeSummary.source.label}
                </p>
                <p className="mt-1 text-[11px] italic text-ink-faint">
                  {activeSummary.disclaimer}
                </p>
              </>
            )}
          </section>
        )}

        {showTranslationBox && (
          <section className="mb-3 rounded-lg border border-ok-line bg-ok-soft p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ok">
                {uz.documents.translateTitle}
              </h3>
              {!translating && (
                <button
                  type="button"
                  onClick={handleCloseTranslation}
                  className="shrink-0 rounded-md border border-ok-line px-2 py-0.5 text-[11px] text-ok hover:bg-ok-soft"
                >
                  {uz.common.close}
                </button>
              )}
            </div>

            {translating && (
              <p className="mt-2 text-ink-soft">
                {uz.documents.translateLoading}
              </p>
            )}
            {translationError && (
              <p className="mt-2 text-bad">{translationError}</p>
            )}

            {activeTranslation && !translating && (
              <>
                <p className="mt-2 text-[11px] text-ink-soft">
                  {languageLabel(activeTranslation.source_language)} →{" "}
                  {languageLabel(activeTranslation.target_language)} ·{" "}
                  {activeTranslation.paragraph_count}{" "}
                  {uz.documents.translateParagraphs}
                  {activeTranslation.cached
                    ? ` · ${uz.documents.translateCached}`
                    : ""}
                </p>
                <p className="mt-1 text-[11px] text-ink-soft">
                  {activeTranslation.same_language
                    ? uz.documents.translateSameLanguage
                    : uz.documents.translateNote}
                </p>
                {activeTranslation.truncated && (
                  <p className="mt-1 text-[11px] text-warn">
                    {uz.documents.translateTruncated}
                  </p>
                )}
                <p className="mt-1 text-[11px] italic text-ink-faint">
                  {activeTranslation.disclaimer}
                </p>
              </>
            )}
          </section>
        )}

        {document && activeTranslation && !translating ? (
          // Side-by-side. One scroll container, one row per paragraph: the two
          // columns stay aligned by construction, no scroll syncing needed.
          <div>
            <div className="bg-surface sticky top-0 z-10 grid grid-cols-1 gap-x-4 border-b border-line pb-1 text-[10px] font-semibold uppercase tracking-wide text-ink-faint sm:grid-cols-2">
              <span>
                {uz.documents.translateOriginal} (
                {languageLabel(activeTranslation.source_language)})
              </span>
              <span className="hidden sm:block">
                {uz.documents.translateColumn} (
                {languageLabel(activeTranslation.target_language)})
              </span>
            </div>
            <div className="divide-y divide-line">
              {activeTranslation.paragraphs.map((pair) => (
                <div
                  key={pair.index}
                  className="grid grid-cols-1 gap-x-4 gap-y-1 py-2 sm:grid-cols-2"
                >
                  <div className="min-w-0">
                    <Markdown text={pair.original} />
                  </div>
                  <div className="min-w-0 border-l-2 border-ok-line pl-2 sm:border-l-0 sm:pl-0">
                    <Markdown text={pair.translated} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          document && <Markdown text={document.text} />
        )}
      </div>
    </div>
  );
}
