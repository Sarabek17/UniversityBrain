"use client";

// "Yangi hujjat": pick a template, edit the prefilled text, send.
//
// The catalogue itself comes from the backend already filtered by role, so a
// student is never offered an order form. The body is *derived* from the
// template (state `null` = untouched) instead of being reset by an effect —
// Next 16 forbids a synchronous setState inside useEffect.

import { useState } from "react";
import type { FlowCreateInput, FlowRecipient, FlowTemplate } from "@/lib/api";
import uz from "@/i18n/uz.json";

function inDays(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export default function FlowComposer({
  templates,
  recipients,
  sending,
  error,
  onSubmit,
  onCancel,
}: {
  templates: FlowTemplate[];
  recipients: FlowRecipient[];
  sending: boolean;
  error: string | null;
  onSubmit: (input: FlowCreateInput) => void;
  onCancel: () => void;
}) {
  const [templateId, setTemplateId] = useState<string>("");
  const [body, setBody] = useState<string | null>(null);
  const [recipientId, setRecipientId] = useState<number | null>(null);
  const [dueDate, setDueDate] = useState<string>(inDays(7));

  const selected =
    templates.find((t) => t.id === templateId) ?? templates[0] ?? null;
  const text = body ?? selected?.body_hint ?? "";
  const recipient = recipientId ?? recipients[0]?.id ?? null;

  if (!selected) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <p className="text-sm text-ink-faint">{uz.common.loading}</p>
      </div>
    );
  }

  return (
    <form
      className="flex min-h-0 flex-1 flex-col overflow-y-auto"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({
          template_id: selected.id,
          body_text: text,
          recipient_user_id: selected.needs_recipient_user ? recipient : null,
          due_date: selected.needs_due_date ? dueDate : null,
        });
      }}
    >
      <h2 className="text-base font-semibold">{uz.docflow.composeTitle}</h2>

      <label className="mt-3 block text-xs text-ink-soft">
        {uz.docflow.template}
        <select
          value={selected.id}
          onChange={(event) => {
            setTemplateId(event.target.value);
            setBody(null); // the new template brings its own prefilled text
          }}
          className="mt-1 w-full rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
        >
          {templates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.title}
            </option>
          ))}
        </select>
      </label>
      <p className="mt-1 text-[11px] text-ink-faint">
        {selected.description} · {uz.docflow.templateHint}
      </p>

      {selected.needs_recipient_user && (
        <label className="mt-3 block text-xs text-ink-soft">
          {uz.docflow.recipient}
          <select
            value={recipient ?? ""}
            onChange={(event) => setRecipientId(Number(event.target.value))}
            className="mt-1 w-full rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
          >
            {recipients.map((person) => (
              <option key={person.id} value={person.id}>
                {person.full_name} ({person.role_label})
              </option>
            ))}
          </select>
          <span className="mt-0.5 block text-[11px] text-ink-faint">
            {uz.docflow.recipientHint}
          </span>
        </label>
      )}

      {!selected.needs_recipient_user && (
        <p className="mt-3 text-xs text-ink-soft">
          {uz.docflow.to}: {selected.recipient_label}
        </p>
      )}

      {selected.needs_due_date && (
        <label className="mt-3 block text-xs text-ink-soft">
          {uz.docflow.dueDate}
          <input
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
            className="mt-1 w-full rounded-md border border-line-strong bg-transparent px-2 py-1.5 text-sm"
          />
        </label>
      )}

      <label className="mt-3 block flex-1 text-xs text-ink-soft">
        {uz.docflow.bodyLabel}
        <textarea
          value={text}
          rows={12}
          placeholder={uz.docflow.bodyPlaceholder}
          onChange={(event) => setBody(event.target.value)}
          className="mt-1 w-full rounded-md border border-line-strong bg-transparent px-2.5 py-2 text-sm"
        />
      </label>

      {error && <p className="mt-2 text-sm text-bad">{error}</p>}

      <div className="mt-3 flex gap-2">
        <button
          type="submit"
          disabled={sending || text.trim().length < 10}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
        >
          {sending ? uz.docflow.sending : uz.docflow.send}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-line-strong px-3 py-1.5 text-sm hover:bg-raised"
        >
          {uz.docflow.cancel}
        </button>
      </div>
    </form>
  );
}
