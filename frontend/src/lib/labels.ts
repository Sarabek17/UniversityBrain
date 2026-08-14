// Uzbek labels for backend enums. UI text itself lives in i18n/uz.json.

import type { AccessLevel, DocumentType } from "@/lib/api";
import uz from "@/i18n/uz.json";

const LANGUAGE_LABELS: Record<string, string> = uz.documents.languages;

export const docTypeLabel = (type: DocumentType): string =>
  uz.documents.types[type] ?? type;

export const accessLabel = (level: AccessLevel): string =>
  uz.documents.access[level] ?? level;

export const languageLabel = (code: string): string =>
  LANGUAGE_LABELS[code] ?? code.toUpperCase();

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatDate(iso: string): string {
  return formatDateTime(iso).split(" ")[0];
}
