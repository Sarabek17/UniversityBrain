"use client";

// Sidebar: own conversations (GET /chat/conversations) + "new conversation".

import type { ConversationOut } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";
import uz from "@/i18n/uz.json";

export default function ConversationList({
  conversations,
  activeId,
  loading,
  error,
  onSelect,
  onNew,
}: {
  conversations: ConversationOut[];
  activeId: number | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: number) => void;
  onNew: () => void;
}) {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-sidebar">
      <div className="flex items-center justify-between px-3 py-3">
        <h2 className="text-sm font-semibold">{uz.chat.conversations}</h2>
        <button
          type="button"
          onClick={onNew}
          className="rounded-md px-2 py-1 text-xs text-ink-soft hover:bg-raised"
        >
          + {uz.chat.newConversation}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && (
          <p className="px-1 text-xs text-ink-faint">{uz.common.loading}</p>
        )}
        {error && <p className="px-1 text-xs text-bad">{error}</p>}
        {!loading && !error && conversations.length === 0 && (
          <p className="px-1 text-xs text-ink-faint">{uz.chat.noConversations}</p>
        )}
        <ul className="flex flex-col gap-1">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                type="button"
                onClick={() => onSelect(conversation.id)}
                className={
                  "w-full rounded-md px-2 py-2 text-left text-xs " +
                  (conversation.id === activeId
                    ? "bg-raised text-ink"
                    : "hover:bg-raised")
                }
              >
                <span className="line-clamp-2 block font-medium">
                  {conversation.title ?? uz.chat.untitled}
                </span>
                <span className="mt-0.5 block text-[10px] text-ink-faint">
                  {formatDateTime(conversation.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
