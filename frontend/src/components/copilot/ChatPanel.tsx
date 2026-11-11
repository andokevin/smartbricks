/** Fil de discussion avec le copilote (module A, n°33). */
import { useEffect, useRef, useState, type FormEvent } from "react";

import type { ChatMessage } from "../../api/types";
import { cx, Icon } from "../ui";

export interface QuickReply {
  label: string;
  icon: string;
  message: string;
}

const PROVIDER: Record<string, string> = { mock: "Simulé", claude: "Claude", gemini: "Gemini" };

function Bubble({ message }: { message: ChatMessage }) {
  const mine = message.role === "user";
  return (
    <div className={cx("flex max-w-[92%] items-start gap-3", mine && "flex-row-reverse self-end")}>
      <span
        className={cx(
          "mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg shadow-card",
          mine ? "rounded-full bg-surface-container-high text-primary" : "bg-primary-container text-on-primary",
        )}
      >
        <Icon name={mine ? "person" : "smart_toy"} className="text-[18px]" />
      </span>
      <div
        className={cx(
          "whitespace-pre-line rounded-xl p-space-md text-body-md leading-relaxed shadow-card",
          mine ? "bg-primary text-on-primary" : "bg-surface-container-lowest text-on-surface",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}

export function ChatPanel({
  messages,
  busy,
  provider,
  fallbackReason,
  quickReplies = [],
  onSend,
  readOnly = false,
  intro,
  sticky = false,
}: {
  sticky?: boolean;
  messages: ChatMessage[];
  busy: boolean;
  provider: string | null;
  fallbackReason?: string | null;
  quickReplies?: QuickReply[];
  onSend?: (text: string) => void;
  readOnly?: boolean;
  intro?: string;
}) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value || busy || !onSend) return;
    onSend(value);
    setText("");
  }

  return (
    <section
      className={cx(
        "flex min-h-[560px] flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-card",
        // Sur ordinateur, le fil reste visible pendant qu'on fait défiler le brouillon.
        sticky ? "lg:h-[calc(100vh-6.5rem)] lg:min-h-0" : "lg:min-h-[680px]",
      )}
    >
      {/* En-tête du copilote */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-low p-space-md">
        <div className="flex min-w-0 items-center gap-3">
          <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-card">
            <Icon name="smart_toy" className="text-[24px]" />
            <span className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-secondary-container ring-2 ring-surface-container-lowest" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-title-md font-bold text-on-surface">Copilote SmartBricks</h3>
              {provider && (
                <span className="rounded-full bg-secondary-fixed px-2 py-0.5 text-label-sm text-on-secondary-fixed">
                  {PROVIDER[provider] ?? provider}
                </span>
              )}
            </div>
            <span className="text-body-sm text-on-surface-variant">Chef de produit · ne calcule jamais les chiffres</span>
          </div>
        </div>
        <span className="rounded-full bg-primary-fixed px-2.5 py-0.5 text-label-sm text-on-primary-fixed">Algorithme n°33</span>
      </div>
      {fallbackReason && (
        <div className="flex items-start gap-2 bg-tertiary-fixed/50 px-space-md py-space-sm text-body-sm text-on-tertiary-fixed">
          <Icon name="info" className="text-[18px]" />
          <span>Mode simulé activé automatiquement : {fallbackReason}</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto bg-surface/40 p-space-md sm:p-space-lg" aria-live="polite">
        {intro && <Bubble message={{ role: "assistant", content: intro }} />}
        {messages.map((m, i) => (
          <Bubble key={i} message={m} />
        ))}
        {busy && (
          <div className="flex items-center gap-2 pl-11 text-body-sm text-on-surface-variant">
            <Icon name="progress_activity" className="animate-spin text-[18px]" />
            Le copilote réfléchit…
          </div>
        )}
        {!busy && !readOnly && quickReplies.length > 0 && (
          <div className="flex flex-wrap gap-2 pl-11">
            {quickReplies.map((q) => (
              <button
                key={q.label}
                onClick={() => onSend?.(q.message)}
                className="flex items-center gap-1.5 rounded-full bg-primary-fixed px-3 py-1.5 text-label-md text-on-primary-fixed transition-all hover:bg-primary-container hover:text-on-primary active:scale-95"
              >
                <Icon name={q.icon} className="text-[16px]" />
                {q.label}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Saisie */}
      {!readOnly && (
        <form onSubmit={submit} className="flex flex-col gap-2 bg-surface-container-lowest p-3 shadow-[0_-2px_8px_rgba(0,0,0,0.03)] sm:p-space-md">
          <div className="flex items-end gap-2 rounded-xl bg-surface-container-low p-1.5 focus-within:ring-2 focus-within:ring-primary-container/20">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) submit(e);
              }}
              rows={2}
              maxLength={4000}
              placeholder="Décrivez votre projet ou répondez au copilote…"
              aria-label="Message au copilote"
              className="min-h-11 flex-1 resize-none bg-transparent px-2 py-2 text-body-md text-on-surface placeholder:text-outline focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary-container text-on-primary shadow-card transition-all hover:bg-primary active:scale-95 disabled:opacity-50"
              aria-label="Envoyer"
            >
              <Icon name="send" />
            </button>
          </div>
          <div className="flex items-center justify-between px-2 text-label-sm text-outline">
            <span className="flex items-center gap-1">
              <Icon name="shield" className="text-[14px]" />
              Votre texte est transmis au copilote comme une donnée, jamais comme une instruction.
            </span>
            <span className="hidden sm:inline">Entrée pour envoyer · Maj+Entrée pour aller à la ligne</span>
          </div>
        </form>
      )}
    </section>
  );
}
