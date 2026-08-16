"use client";

// Rich UI for a tool result inside the chat. The backend's format_*_for_tool
// helpers emit deterministic "Key: value" / bullet lines — this component
// parses those lines into a structured card (definition rows, lists, section
// heads) instead of dumping raw text. Unknown shapes safely fall back to
// plain paragraphs, so a new tool never breaks the chat.

import { useState, type ReactNode } from "react";
import uz from "@/i18n/uz.json";

type Block =
  | { type: "kv"; k: string; v: string }
  | { type: "head"; text: string }
  | { type: "li"; text: string }
  | { type: "p"; text: string };

const KV_RE = /^([^:]{2,44}):\s+(.+)$/;

function parseBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  for (const raw of content.split("\n")) {
    let t = raw.trim();
    if (!t) continue;
    // "(Manba: ...)" style wrapping parens — unwrap before structuring
    if (t.startsWith("(") && t.endsWith(")")) t = t.slice(1, -1);
    const li = t.match(/^(?:[-•]|\d+[.)])\s+(.+)$/);
    if (li) {
      blocks.push({ type: "li", text: li[1] });
      continue;
    }
    const kv = t.match(KV_RE);
    if (kv) {
      blocks.push({ type: "kv", k: kv[1], v: kv[2] });
      continue;
    }
    if (t.endsWith(":") && t.length <= 60) {
      blocks.push({ type: "head", text: t.slice(0, -1) });
      continue;
    }
    blocks.push({ type: "p", text: t });
  }
  return blocks;
}

/* Tools whose result is long prose — collapsed by default, the structured
   ones (numbers, statuses) stay open: they ARE the wow. */
const COLLAPSED = new Set(["hujjat_qidir", "hujjat_rezyume", "tarjima_qil"]);

const ICONS: Record<string, ReactNode> = {
  hujjat_qidir: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  hujjat_rezyume: (
    <>
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M9 11h7M9 15h7" />
    </>
  ),
  tarjima_qil: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18" />
    </>
  ),
  jadval_kor: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M4 10h16M8 3v4M16 3v4" />
    </>
  ),
  tolov_holati: (
    <>
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18M7 15h4" />
    </>
  ),
  mavjudlik_tekshir: (
    <>
      <path d="M12 21s-6-5.2-6-10a6 6 0 1 1 12 0c0 4.8-6 10-6 10z" />
      <circle cx="12" cy="11" r="2.2" />
    </>
  ),
  davomat_kor: (
    <>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="m9 13 2 2 4-4" />
    </>
  ),
  oqituvchi_davomat: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 20c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5M16 4.5a3 3 0 0 1 0 6M17.5 15c1.9.5 3.2 2 3.7 4.5" />
    </>
  ),
  ariza_holati: (
    <>
      <path d="M6 3h9l4 4v14H6z" />
      <path d="m9.5 14 2 2 3.5-3.5" />
    </>
  ),
  bildirishnomalar: (
    <>
      <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </>
  ),
};

const DEFAULT_ICON = (
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v4l2.5 2.5" />
  </>
);

export default function ToolCard({
  name,
  content,
}: {
  name: string;
  content: string;
}) {
  const [open, setOpen] = useState(!COLLAPSED.has(name));
  const labels = uz.chat.toolNames as Record<string, string>;
  const label = labels[name] ?? name;
  const blocks = parseBlocks(content);
  const kvCount = blocks.filter((b) => b.type === "kv").length;

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2.5 px-3 py-2 text-left hover:bg-raised"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent-ink">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            {ICONS[name] ?? DEFAULT_ICON}
          </svg>
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-ink">
            {label}
          </span>
          <span className="block font-mono text-[10px] text-ink-faint">
            {name}
          </span>
        </span>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          className={
            "h-3.5 w-3.5 shrink-0 text-ink-faint transition-transform " +
            (open ? "rotate-180" : "")
          }
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-line px-3 py-2.5">
          <div className="flex flex-col gap-1">
            {blocks.map((b, i) => {
              if (b.type === "kv") {
                return (
                  <div
                    key={i}
                    className="flex items-baseline justify-between gap-4 text-sm"
                  >
                    <span className="shrink-0 text-ink-faint">{b.k}</span>
                    <span className="text-right font-medium text-ink">
                      {b.v}
                    </span>
                  </div>
                );
              }
              if (b.type === "head") {
                return (
                  <p
                    key={i}
                    className="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-faint first:mt-0"
                  >
                    {b.text}
                  </p>
                );
              }
              if (b.type === "li") {
                return (
                  <p key={i} className="flex gap-2 text-sm text-ink-soft">
                    <span className="text-ink-faint">•</span>
                    <span>{b.text}</span>
                  </p>
                );
              }
              return (
                <p key={i} className="text-sm text-ink-soft">
                  {b.text}
                </p>
              );
            })}
            {blocks.length === 0 && (
              <p className="text-sm text-ink-faint">—</p>
            )}
          </div>
          {kvCount > 0 && <div className="mt-1" />}
        </div>
      )}
    </div>
  );
}
