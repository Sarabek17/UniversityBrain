"use client";

// The chat itself: message list, composer, waiting/error states.
// Presentational — the conversation state lives in the chat page, so switching
// conversations never runs a setState-inside-effect cascade.
// Every assistant answer shows its source chips and the disclaimer that came
// from the backend (never hardcoded here).

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ViewMessage } from "@/lib/chat";
import { useAuth } from "@/lib/auth";
import Markdown from "@/components/Markdown";
import SourceChips from "@/components/SourceChips";
import ToolCard from "@/components/ToolCard";
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
  onOpenDocument: (documentId: number, heading?: string | null) => void;
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  // Auto-scroll only while the reader is already at the bottom — scrolling up
  // to re-read must never be fought by the typewriter ticks.
  const nearBottom = () => {
    const el = scrollerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };
  const { user } = useAuth();
  // "Aliyev Jasur" -> "Jasur"; falls back to the full name
  const firstName = user?.full_name.split(" ")[1] ?? user?.full_name ?? "";

  // Typewriter for the freshly received answer. Keyed by CONTENT, not by
  // message key: the page re-reads the conversation right after the POST and
  // the keys change while the text stays the same — typing continues smoothly.
  const [typing, setTyping] = useState<{ content: string; n: number } | null>(
    null,
  );
  const wasSendingRef = useRef(false);

  useEffect(() => {
    const last = messages[messages.length - 1];
    const justAnswered =
      wasSendingRef.current && !sending && last?.role === "assistant";
    wasSendingRef.current = sending;
    if (!justAnswered || !last) return;
    const content = last.content;
    Promise.resolve().then(() => setTyping({ content, n: 0 }));
  }, [messages, sending]);

  const typingContent = typing !== null ? typing.content : null;
  useEffect(() => {
    if (typingContent === null) return;
    const id = window.setInterval(() => {
      setTyping((t) => {
        if (!t || t.content !== typingContent) return t;
        if (t.n >= t.content.length) return t;
        return { ...t, n: Math.min(t.content.length, t.n + 5) };
      });
      if (nearBottom()) bottomRef.current?.scrollIntoView({ block: "end" });
    }, 16);
    return () => window.clearInterval(id);
  }, [typingContent]);

  useEffect(() => {
    if (sending || nearBottom()) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
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
      <div ref={scrollerRef} className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
          {loading && messages.length === 0 && (
            <p className="text-sm text-ink-faint">{uz.common.loading}</p>
          )}

          {empty && (
            <div className="mt-[14vh] flex flex-col items-center text-center">
              {/* terracotta spark — the same mark as the header logo */}
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                className="h-10 w-10 text-accent-ink"
              >
                <path d="M12 3v5M12 16v5M3 12h5M16 12h5M5.6 5.6l3.5 3.5M14.9 14.9l3.5 3.5M18.4 5.6l-3.5 3.5M9.1 14.9l-3.5 3.5" />
              </svg>
              <h2 className="mt-5 text-2xl font-semibold tracking-tight">
                {firstName
                  ? uz.chat.greeting.replace("{name}", firstName)
                  : uz.chat.emptyTitle}
              </h2>
              <p className="mt-1.5 text-sm text-ink-faint">{uz.chat.emptyHint}</p>
              <div className="mt-8 grid w-full max-w-2xl gap-2.5 sm:grid-cols-3">
                {uz.chat.samples.map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => onSend(sample)}
                    className="group flex flex-col justify-between gap-3 rounded-xl border border-line bg-surface p-3.5 text-left text-sm text-ink-soft transition-colors hover:border-accent-line hover:bg-raised"
                  >
                    <span>{sample}</span>
                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-raised text-ink-faint transition-colors group-hover:bg-accent-soft group-hover:text-accent-ink">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-3.5 w-3.5"
                      >
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </span>
                  </button>
                ))}
              </div>
              {/* Staff roles already have the Virtaks card in the dashboard
                  rail — this contextual line is for students only. */}
              {user?.role === "student" && (
                <p className="mt-7 text-sm text-ink-faint">
                  {uz.common.teacherHelpHint}{" "}
                  <a
                    href="https://twin.virtaks.uz"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-accent-ink hover:underline"
                  >
                    {uz.common.teacherHelpLink} ↗
                  </a>
                </p>
              )}
            </div>
          )}

          {messages.map((message) =>
            message.role === "user" ? (
              <div key={message.key} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-raised px-4 py-2 text-ink">
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                </div>
              </div>
            ) : (
              <div key={message.key} className="flex justify-start">
                {(() => {
                  const isLast =
                    messages[messages.length - 1]?.key === message.key;
                  const inTyping =
                    isLast &&
                    typing !== null &&
                    typing.content === message.content &&
                    typing.n < typing.content.length;
                  return (
                    <div className="flex w-full max-w-[90%] flex-col gap-2">
                      {message.tools.map((tool, index) => (
                        <div key={`${message.key}-t${index}`} className="fade-up">
                          <ToolCard name={tool.name} content={tool.content} />
                        </div>
                      ))}
                      <div className="fade-up rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3">
                        <Markdown
                          text={
                            inTyping
                              ? typing.content.slice(0, typing.n) + " ▍"
                              : message.content
                          }
                          breaks
                          className="text-sm [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
                        />
                        {!inTyping && (
                          <SourceChips
                            sources={message.sources}
                            onOpenDocument={onOpenDocument}
                          />
                        )}
                        {!inTyping && disclaimer && (
                          <p className="mt-2 border-t border-line pt-2 text-[11px] text-ink-faint">
                            {disclaimer}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>
            ),
          )}

          {sending && (
            <div className="flex justify-start">
              <div className="fade-up flex items-center gap-2.5 rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-2.5 text-sm text-ink-faint">
                {/* the spark "thinks" while tools are being called */}
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  className="h-4 w-4 animate-spin text-accent-ink [animation-duration:2.5s]"
                >
                  <path d="M12 3v5M12 16v5M3 12h5M16 12h5M5.6 5.6l3.5 3.5M14.9 14.9l3.5 3.5M18.4 5.6l-3.5 3.5M9.1 14.9l-3.5 3.5" />
                </svg>
                <span>{uz.chat.waiting}</span>
                <span className="flex gap-0.5">
                  <span className="typing-dot">●</span>
                  <span className="typing-dot [animation-delay:0.2s]">●</span>
                  <span className="typing-dot [animation-delay:0.4s]">●</span>
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-md border border-bad-line bg-bad-soft px-3 py-2 text-sm text-bad">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <form
        onSubmit={submit}
        className="border-t border-line px-4 py-3"
      >
        <div className="mx-auto flex w-full max-w-3xl gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={uz.chat.placeholder}
            aria-label={uz.chat.placeholder}
            className="flex-1 rounded-md border border-line-strong px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={sending || input.trim() === ""}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
          >
            {uz.chat.send}
          </button>
        </div>
      </form>
    </section>
  );
}
