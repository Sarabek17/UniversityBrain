"use client";

// Documents page: role-filtered list on the left, the selected document on the
// right (same viewer the chat source chips open).

import { useEffect, useState } from "react";
import { documentsApi, type DocumentListItem } from "@/lib/api";
import DocumentList from "@/components/DocumentList";
import DocumentPanel from "@/components/DocumentPanel";
import uz from "@/i18n/uz.json";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    documentsApi
      .list()
      .then((loaded) => {
        if (cancelled) return;
        setDocuments(loaded);
        setActiveId((current) => current ?? loaded[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setError(uz.documents.listError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-0 flex-1">
      <aside className="flex w-72 shrink-0 flex-col border-r border-line bg-sidebar">
        <DocumentList
          documents={documents}
          activeId={activeId}
          loading={loading}
          error={error}
          onSelect={(id) => setActiveId(id)}
        />
      </aside>
      <section className="flex min-h-0 flex-1 flex-col">
        <DocumentPanel documentId={activeId} />
      </section>
    </div>
  );
}
