"use client";

// The chat itself: message list, composer, waiting/error states.
// Presentational — the conversation state lives in the chat page, so switching
// conversations never runs a setState-inside-effect cascade.
// Every assistant answer shows its source chips and the disclaimer that came
// from the backend (never hardcoded here).

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ViewMessage } from "@/lib/chat";
import Markdown from "@/components/Markdown";
import SourceChips from "@/components/SourceChips";
import uz from "@/i18n/uz.json";

export default function ChatWindow({
  messages,
  disclaimer,
  loading,
  sending,
  error,
  onSend,
  onOpenDocument,
}: {
  messages: ViewMessage[];
  disclaimer: string | null;
  loading: boolean;
  sending: boolean;
  error: string | null;
  onSend: (text: string) => void;
  onOpenDocument: (documentId: number) => void;
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    onSend(text);
  }

  const empty = messages.length === 0 && !loading && !sending;

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
          {loading && messages.length === 0 && (
            <p className="text-sm text-gray-500">{uz.common.loading}</p>
          )}

          {empty && (
            <div className="mt-10 text-center">
              <h2 className="text-lg font-semibold">{uz.chat.emptyTitle}</h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {uz.chat.emptyHint}
              </p>
              <p className="mt-6 text-xs font-semibold text-gray-500 dark:text-gray-400">
                {uz.chat.samplesTitle}
              </p>
              <div className="mt-2 flex flex-wrap justify-center gap-2">
                {uz.chat.samples.map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => onSend(sample)}
                    className="rounded-full border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) =>
            message.role === "user" ? (
              <div key={message.key} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white">
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                </div>
              </div>
            ) : (
              <div key={message.key} className="flex justify-start">
                <div className="max-w-[90%] rounded-2xl rounded-bl-sm border border-gray-200 px-4 py-3 dark:border-gray-700">
                  {message.tools.length > 0 && (
                    <div className="mb-1.5 flex flex-wrap gap-1">
                      {message.tools.map((tool) => (
                        <span
                          key={tool}
                          title={uz.chat.toolUsed}
                          className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  )}
                  <Markdown
                    text={message.content}
                    breaks
                    className="text-sm [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
                  />
                  <SourceChips
                    sources={message.sources}
                    onOpenDocument={onOpenDocument}
                  />
                  {disclaimer && (
                    <p className="mt-2 border-t border-gray-100 pt-2 text-[11px] text-gray-500 dark:border-gray-800 dark:text-gray-400">
                      {disclaimer}
                    </p>
                  )}
                </div>
              </div>
            ),
          )}

          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm border border-gray-200 px-4 py-2 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                <span className="inline-block animate-pulse">
                  {uz.chat.waiting}
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <form
        onSubmit={submit}
        className="border-t border-gray-200 px-4 py-3 dark:border-gray-700"
      >
        <div className="mx-auto flex w-full max-w-3xl gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={uz.chat.placeholder}
            aria-label={uz.chat.placeholder}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          />
          <button
            type="submit"
            disabled={sending || input.trim() === ""}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uz.chat.send}
          </button>
        </div>
      </form>
    </section>
  );
}
