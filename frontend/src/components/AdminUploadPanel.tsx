"use client";

// Document upload + tagging (S13). The backend indexes the file inside the
// request, so the "Bo'laklar" column of the table below is also the proof that
// the new document is already searchable in the chat.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  adminApi,
  errorDetail,
  type AccessLevel,
  type AdminDocument,
  type DocumentType,
} from "@/lib/api";
import { accessLabel, docTypeLabel, languageLabel } from "@/lib/labels";
import uz from "@/i18n/uz.json";

const DOC_TYPES: DocumentType[] = [
  "syllabus",
  "order",
  "assignment",
  "literature",
  "regulation",
  "other",
];

const ACCESS_LEVELS: AccessLevel[] = [
  "public",
  "student",
  "teacher",
  "tutor",
  "staff",
  "admin",
];

const LANGUAGES = ["uz", "ru", "en"] as const;

export default function AdminUploadPanel({
  onUploaded,
}: {
  onUploaded: () => void;
}) {
  const [documents, setDocuments] = useState<AdminDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState<DocumentType>("regulation");
  const [language, setLanguage] = useState<string>("uz");
  const [access, setAccess] = useState<AccessLevel>("public");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(
    () =>
      adminApi
        .documents()
        .then((rows) => {
          setDocuments(rows);
          setError(null);
        })
        .catch(() => setError(uz.admin.loadError)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError(uz.admin.uploadNoFile);
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    adminApi
      .uploadDocument({
        file,
        title: title.trim() || file.name,
        doc_type: docType,
        language,
        access_level: access,
      })
      .then((result) => {
        setNotice(result.message);
        setTitle("");
        if (fileRef.current) fileRef.current.value = "";
        onUploaded();
        return load();
      })
      .catch((e: unknown) => setError(errorDetail(e) ?? uz.admin.uploadError))
      .finally(() => setBusy(false));
  }

  return (
    <section className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
      <h2 className="text-sm font-semibold">{uz.admin.uploadTitle}</h2>
      <p className="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
        {uz.admin.uploadHint}
      </p>

      <form onSubmit={submit} className="mt-2 grid gap-2 sm:grid-cols-2">
        <label className="text-[11px] text-gray-600 sm:col-span-2 dark:text-gray-300">
          {uz.admin.uploadFile}
          <input
            ref={fileRef}
            type="file"
            accept=".md,.txt,.markdown"
            className="mt-0.5 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
          />
        </label>
        <label className="text-[11px] text-gray-600 sm:col-span-2 dark:text-gray-300">
          {uz.admin.uploadName}
          <input
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="mt-0.5 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
          />
        </label>
        <label className="text-[11px] text-gray-600 dark:text-gray-300">
          {uz.admin.uploadType}
          <select
            value={docType}
            onChange={(event) =>
              setDocType(event.target.value as DocumentType)
            }
            className="mt-0.5 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
          >
            {DOC_TYPES.map((type) => (
              <option key={type} value={type}>
                {docTypeLabel(type)}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-[11px] text-gray-600 dark:text-gray-300">
            {uz.admin.uploadLanguage}
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              className="mt-0.5 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
            >
              {LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {languageLabel(code)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[11px] text-gray-600 dark:text-gray-300">
            {uz.admin.uploadAccess}
            <select
              value={access}
              onChange={(event) =>
                setAccess(event.target.value as AccessLevel)
              }
              className="mt-0.5 w-full rounded-md border border-gray-300 bg-transparent px-2 py-1 text-xs dark:border-gray-600"
            >
              {ACCESS_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {accessLabel(level)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? uz.admin.uploadLoading : uz.admin.uploadSubmit}
          </button>
        </div>
      </form>

      {notice && (
        <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
          {notice}
        </p>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      <h3 className="mt-4 text-xs font-semibold">{uz.admin.documentsTitle}</h3>
      <div className="mt-1.5 max-h-64 overflow-y-auto rounded-md border border-gray-200 dark:border-gray-700">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colDocument}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colType}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colAccess}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colChunks}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colSource}</th>
            </tr>
          </thead>
          <tbody>
            {documents?.map((row) => (
              <tr
                key={row.id}
                className="border-t border-gray-100 dark:border-gray-800"
              >
                <td className="px-2 py-1.5">
                  {row.title}
                  <span className="ml-1 text-gray-400">
                    ({languageLabel(row.language)})
                  </span>
                </td>
                <td className="px-2 py-1.5 text-gray-500 dark:text-gray-400">
                  {docTypeLabel(row.doc_type)}
                </td>
                <td className="px-2 py-1.5 text-gray-500 dark:text-gray-400">
                  {accessLabel(row.access_level)}
                </td>
                <td className="px-2 py-1.5">
                  {row.indexed ? (
                    row.chunk_count
                  ) : (
                    <span className="text-amber-700 dark:text-amber-300">
                      {uz.admin.notIndexed}
                    </span>
                  )}
                </td>
                <td className="px-2 py-1.5 text-gray-500 dark:text-gray-400">
                  {row.uploaded
                    ? uz.admin.sourceUploaded
                    : uz.admin.sourceSeed}
                </td>
              </tr>
            ))}
            {documents && documents.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-2 py-3 text-center text-gray-500 dark:text-gray-400"
                >
                  {uz.admin.documentsEmpty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!documents && !error && (
          <p className="px-2 py-3 text-xs text-gray-500">{uz.common.loading}</p>
        )}
      </div>
    </section>
  );
}
