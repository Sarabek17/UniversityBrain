// View model for the chat: stored messages flattened for rendering.

import type { ChatMessageOut, ChatSource } from "@/lib/api";

export interface ViewMessage {
  key: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[];
  tools: string[]; // tools called while producing this answer
}

/** Tool rows become badges on the answer they fed, not messages of their own. */
export function toViewMessages(messages: ChatMessageOut[]): ViewMessage[] {
  const view: ViewMessage[] = [];
  let tools: string[] = [];

  for (const message of messages) {
    if (message.role === "tool") {
      if (message.tool_name) tools.push(message.tool_name);
      continue;
    }
    view.push({
      key: `m${message.id}`,
      role: message.role,
      content: message.content,
      sources: message.sources ?? [],
      tools: message.role === "assistant" ? tools : [],
    });
    tools = [];
  }
  return view;
}
