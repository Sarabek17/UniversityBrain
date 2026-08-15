"use client";

// Chat workspace: conversations rail · chat · document panel.
// Conversation state lives here (loading happens in event handlers, not in
// effects). The right rail shows the opened document; with nothing opened it
// falls back to the (still empty) role dashboard for teacher/tutor/staff/admin.

import { useCallback, useEffect, useState } from "react";
import { chatApi, type ConversationOut } from "@/lib/api";
import { toViewMessages, type ViewMessage } from "@/lib/chat";
import { useAuth } from "@/lib/auth";
import ChatWindow from "@/components/ChatWindow";
import ConversationList from "@/components/ConversationList";
import DocumentPanel from "@/components/DocumentPanel";
import RoleDashboard, { hasDashboard } from "@/components/RoleDashboard";
import uz from "@/i18n/uz.json";

export default function ChatPage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ViewMessage[]>([]);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const [openDocumentId, setOpenDocumentId] = useState<number | null>(null);

  const refreshConversations = useCallback(
    () =>
      chatApi
        .conversations()
        .then((list) => {
          setConversations(list);
          setListError(null);
        })
        .catch(() => setListError(uz.chat.listError))
        .finally(() => setListLoading(false)),
    [],
  );

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  function selectConversation(id: number) {
    if (id === activeId) return;
    setActiveId(id);
    setMessages([]);
    setDisclaimer(null);
    setChatError(null);
    setHistoryLoading(true);
    chatApi
      .conversation(id)
      .then((detail) => {
        setMessages(toViewMessages(detail.messages));
        setDisclaimer(detail.disclaimer);
      })
      .catch(() => setChatError(uz.chat.loadError))
      .finally(() => setHistoryLoading(false));
  }

  function startNewConversation() {
    setActiveId(null);
    setMessages([]);
    setDisclaimer(null);
    setChatError(null);
  }

  async function send(text: string) {
    const wasNew = activeId === null;
    const optimistic: ViewMessage = {
      key: `local-u-${Date.now()}`,
      role: "user",
      content: text,
      sources: [],
      tools: [],
    };
    setChatError(null);
    setSending(true);
    setMessages((prev) => [...prev, optimistic]);
    try {
      const answer = await chatApi.send(text, activeId);
      setDisclaimer(answer.disclaimer);
      setMessages((prev) => [
        ...prev,
        {
          key: `local-a-${Date.now()}`,
          role: "assistant",
          content: answer.text,
          sources: answer.sources,
          tools: [],
        },
      ]);
      setActiveId(answer.conversation_id);
      // Re-read the stored conversation: adds the tool badges (audit trail)
      // that the POST response does not carry.
      chatApi
        .conversation(answer.conversation_id)
        .then((detail) => {
          setMessages(toViewMessages(detail.messages));
          setDisclaimer(detail.disclaimer);
        })
        .catch(() => {
          // The answer is already on screen; the badges are a nice-to-have.
        });
      if (wasNew) void refreshConversations();
    } catch {
      setMessages((prev) => prev.filter((m) => m.key !== optimistic.key));
      setChatError(uz.chat.sendError);
    } finally {
      setSending(false);
    }
  }

  const showDashboard =
    user !== null && hasDashboard(user.role) && openDocumentId === null;

  return (
    <div className="flex min-h-0 flex-1">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        loading={listLoading}
        error={listError}
        onSelect={selectConversation}
        onNew={startNewConversation}
      />

      <ChatWindow
        messages={messages}
        disclaimer={disclaimer}
        loading={historyLoading}
        sending={sending}
        error={chatError}
        onSend={(text) => void send(text)}
        onOpenDocument={(documentId) => setOpenDocumentId(documentId)}
      />

      {(openDocumentId !== null || showDashboard) && (
        <aside className="hidden w-96 shrink-0 border-l border-line lg:flex lg:min-h-0 lg:flex-col">
          {openDocumentId !== null ? (
            <DocumentPanel
              documentId={openDocumentId}
              onClose={() => setOpenDocumentId(null)}
            />
          ) : (
            user && <RoleDashboard role={user.role} />
          )}
        </aside>
      )}
    </div>
  );
}
