"use client";

// Minimal markdown renderer for the document corpus (headings, tables, lists,
// code, bold/italic). Deliberately dependency-free: the corpus is small and a
// full markdown engine would be the heaviest thing in the bundle.

import { createElement, type ReactNode } from "react";

const INLINE_RE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;

const HEADING_CLASSES = [
  "mt-2 mb-3 text-xl font-bold",
  "mt-5 mb-2 text-lg font-bold",
  "mt-4 mb-2 text-base font-semibold",
  "mt-3 mb-1 text-sm font-semibold",
  "mt-3 mb-1 text-sm font-semibold",
  "mt-3 mb-1 text-sm font-semibold",
];

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text
    .split(INLINE_RE)
    .filter((part) => part !== "")
    .map((part, index) => {
      const key = `${keyPrefix}-i${index}`;
      if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
        return <strong key={key}>{part.slice(2, -2)}</strong>;
      }
      if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={key}
            className="rounded bg-gray-100 px-1 py-0.5 font-mono text-[0.85em] dark:bg-gray-800"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.length > 2 && part.startsWith("*") && part.endsWith("*")) {
        return <em key={key}>{part.slice(1, -1)}</em>;
      }
      return <span key={key}>{part}</span>;
    });
}

function cells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

const BLOCK_START_RE = /^(#{1,6}\s|[-*+]\s|\d+\.\s|\||```|(-{3,}|\*{3,}|_{3,})$)/;

function renderBlocks(source: string): ReactNode[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i += 1;
      continue;
    }

    // fenced code
    if (line.trim().startsWith("```")) {
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        body.push(lines[i]);
        i += 1;
      }
      i += 1;
      out.push(
        <pre
          key={`b${key++}`}
          className="my-3 overflow-x-auto rounded-md bg-gray-100 p-3 font-mono text-xs dark:bg-gray-800"
        >
          {body.join("\n")}
        </pre>,
      );
      continue;
    }

    // heading
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      out.push(
        createElement(
          `h${level}`,
          { key: `b${key++}`, className: HEADING_CLASSES[level - 1] },
          renderInline(heading[2], `h${key}`),
        ),
      );
      i += 1;
      continue;
    }

    // horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      out.push(
        <hr
          key={`b${key++}`}
          className="my-4 border-gray-200 dark:border-gray-700"
        />,
      );
      i += 1;
      continue;
    }

    // table: a pipe row followed by a |---|---| separator
    if (
      line.trim().startsWith("|") &&
      i + 1 < lines.length &&
      /^\|[\s:|-]+\|?$/.test(lines[i + 1].trim())
    ) {
      const header = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(cells(lines[i]));
        i += 1;
      }
      out.push(
        <div key={`b${key++}`} className="my-3 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100 dark:bg-gray-800">
                {header.map((cell, c) => (
                  <th
                    key={c}
                    className="border border-gray-200 px-2 py-1 text-left font-semibold dark:border-gray-700"
                  >
                    {renderInline(cell, `th${key}-${c}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td
                      key={c}
                      className="border border-gray-200 px-2 py-1 align-top dark:border-gray-700"
                    >
                      {renderInline(cell, `td${key}-${r}-${c}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // list (bullet or numbered); indented continuation lines join the item
    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i];
        const isItem = /^\s*([-*+]|\d+\.)\s+/.test(current);
        if (isItem) {
          items.push(current.replace(/^\s*([-*+]|\d+\.)\s+/, ""));
          i += 1;
          continue;
        }
        const isContinuation =
          current.trim() !== "" &&
          /^\s+/.test(current) &&
          !BLOCK_START_RE.test(current.trim());
        if (isContinuation && items.length > 0) {
          items[items.length - 1] += ` ${current.trim()}`;
          i += 1;
          continue;
        }
        break;
      }
      const listItems = items.map((item, index) => (
        <li key={index} className="my-0.5">
          {renderInline(item, `li${key}-${index}`)}
        </li>
      ));
      out.push(
        ordered ? (
          <ol key={`b${key++}`} className="my-2 list-decimal pl-5">
            {listItems}
          </ol>
        ) : (
          <ul key={`b${key++}`} className="my-2 list-disc pl-5">
            {listItems}
          </ul>
        ),
      );
      continue;
    }

    // paragraph
    const paragraph: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !BLOCK_START_RE.test(lines[i].trim())
    ) {
      paragraph.push(lines[i].trim());
      i += 1;
    }
    if (paragraph.length > 0) {
      out.push(
        <p key={`b${key++}`} className="my-2 leading-relaxed">
          {renderInline(paragraph.join(" "), `p${key}`)}
        </p>,
      );
    } else {
      i += 1; // safety: never loop forever on an unexpected line
    }
  }

  return out;
}

export default function Markdown({
  text,
  className = "",
}: {
  text: string;
  className?: string;
}) {
  return <div className={className}>{renderBlocks(text)}</div>;
}
