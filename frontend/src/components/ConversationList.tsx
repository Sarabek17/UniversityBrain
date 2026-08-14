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
    <aside className="flex w-64 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between px-3 py-3">
        <h2 className="text-sm font-semibold">{uz.chat.conversations}</h2>
        <button
          type="button"
          onClick={onNew}
          className="rounded-md border border-blue-300 px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950"
        >
          + {uz.chat.newConversation}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && (
          <p className="px-1 text-xs text-gray-500">{uz.common.loading}</p>
        )}
        {error && <p className="px-1 text-xs text-red-600">{error}</p>}
        {!loading && !error && conversations.length === 0 && (
          <p className="px-1 text-xs text-gray-500">{uz.chat.noConversations}</p>
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
                    ? "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800")
                }
              >
                <span className="line-clamp-2 block font-medium">
                  {conversation.title ?? uz.chat.untitled}
                </span>
                <span className="mt-0.5 block text-[10px] text-gray-500 dark:text-gray-400">
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
