/** Écran Copilote — nouveau projet : conversation, puis brouillon modifiable, puis confirmation.
 *
 * L'identifiant de conversation est gardé dans l'URL (?conversation=…) : un rechargement
 * de la page reprend la conversation là où elle en était.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { ChatMessage, Draft } from "../api/types";
import { AppShell } from "../components/AppShell";
import { ChatPanel, type QuickReply } from "../components/copilot/ChatPanel";
import { DraftEditor } from "../components/copilot/DraftEditor";
import { Card, ErrorBanner, Icon } from "../components/ui";
import { formatAr, formatDate } from "../lib/format";
import { stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

const DEMO_TEXT =
  "Boutique Soa veut un site e-commerce avec paiement MVola, une application mobile de suivi des commandes, " +
  "et l'installation du réseau dans ses agences de Tana, Antsirabe, Toamasina et Fianarantsoa. " +
  "Budget 6 000 000 Ar, livraison dans 8 semaines.";

const INTRO =
  "Bonjour ! Décrivez-moi votre projet avec vos mots : ce que vous voulez obtenir, votre budget en Ariary, " +
  "votre date limite et la ville de votre entreprise. Je vous poserai quelques questions, puis je préparerai " +
  "un brouillon que vous pourrez corriger.";

function quickRepliesFor(messages: ChatMessage[], ready: boolean): QuickReply[] {
  if (ready) return [];
  if (messages.length === 0) {
    return [{ label: "Utiliser l'exemple Boutique Soa", icon: "storefront", message: DEMO_TEXT }];
  }
  const last = messages.at(-1);
  if (last?.role !== "assistant" || !last.content.trim().endsWith("?")) return [];
  if (/livraison/i.test(last.content)) {
    return [
      { label: "Oui, livraison à domicile", icon: "local_shipping", message: "Oui, la livraison à domicile est importante." },
      { label: "Non, retrait en boutique", icon: "storefront", message: "Non, pas besoin : les clients retirent en boutique." },
    ];
  }
  return [
    { label: "Oui", icon: "check", message: "Oui." },
    { label: "Non", icon: "close", message: "Non." },
  ];
}

export function CopilotPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const conversationId = params.get("conversation") ? Number(params.get("conversation")) : null;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [fallback, setFallback] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const cities = useAsync(() => api.cities(), []);
  const health = useAsync(() => api.health(), []);

  // Reprise d'une conversation existante (rechargement de la page).
  useEffect(() => {
    if (conversationId === null || messages.length > 0) return;
    api
      .conversation(conversationId)
      .then((c) => {
        if (c.status === "CONFIRMED" && c.project_id) {
          navigate(stepPath(c.project_id, "copilote"), { replace: true });
          return;
        }
        setMessages(c.messages);
        setDraft(c.draft);
        setWarnings(c.warnings);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  async function send(text: string) {
    setBusy(true);
    setError(null);
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const out = await api.chat(text, conversationId);
      setMessages((m) => [...m, { role: "assistant", content: out.reply }]);
      setProvider(out.provider);
      setFallback(out.fallback_reason);
      if (out.draft) {
        setDraft(out.draft);
        setWarnings(out.warnings);
      }
      if (conversationId !== out.conversation_id) setParams({ conversation: String(out.conversation_id) }, { replace: true });
    } catch (e) {
      setMessages((m) => m.slice(0, -1)); // le message n'a pas été pris en compte
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!draft || conversationId === null) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      const out = await api.confirm(conversationId, draft);
      navigate(stepPath(out.project_id, "perimetre"));
    } catch (e) {
      setConfirmError(e instanceof Error ? e.message : String(e));
      setConfirming(false);
    }
  }

  const quickReplies = useMemo(() => quickRepliesFor(messages, draft !== null), [messages, draft]);

  return (
    <AppShell crumbs={[{ label: "Projets", to: "/" }, { label: "Nouveau projet — Copilote" }]}>
      <div className="flex flex-col gap-space-lg">
        {/* Bandeau de contexte */}
        <Card className="flex flex-col justify-between gap-4 p-space-md sm:p-5 md:flex-row md:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-card">
              <Icon name="foundation" className="text-[26px]" />
            </span>
            <div className="min-w-0">
              <span className="rounded-full bg-tertiary-fixed px-2 py-0.5 text-label-sm uppercase tracking-wider text-on-tertiary-fixed">
                {draft ? "Brouillon prêt" : "Conversation en cours"}
              </span>
              <h2 className="mt-1 truncate text-headline-sm text-on-surface">{draft?.project.title ?? "Nouveau projet"}</h2>
            </div>
          </div>
          {draft && (
            <div className="flex shrink-0 flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 rounded-lg bg-surface-container-low px-3 py-2">
                <Icon name="payments" className="text-primary" />
                <div className="leading-tight">
                  <div className="text-label-sm text-on-surface-variant">Budget</div>
                  <div className="text-title-md font-bold text-primary">{formatAr(draft.project.budget_mga)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-surface-container-low px-3 py-2">
                <Icon name="event" className="text-secondary" />
                <div className="leading-tight">
                  <div className="text-label-sm text-on-surface-variant">Date limite</div>
                  <div className="text-title-md font-bold text-on-surface">{formatDate(draft.project.deadline)}</div>
                </div>
              </div>
            </div>
          )}
        </Card>

        {error && <ErrorBanner message={error} />}

        <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
          <div className="lg:sticky lg:top-20 lg:col-span-7">
            <ChatPanel
              sticky
              messages={messages}
              busy={busy}
              provider={provider ?? health.data?.llm_provider ?? null}
              fallbackReason={fallback}
              quickReplies={quickReplies}
              onSend={(t) => void send(t)}
              intro={INTRO}
            />
          </div>
          <div className="lg:col-span-5">
            {draft ? (
              <DraftEditor
                draft={draft}
                warnings={warnings}
                cities={cities.data ?? []}
                onChange={setDraft}
                onConfirm={() => void confirm()}
                confirming={confirming}
                error={confirmError}
              />
            ) : (
              <Card className="flex flex-col gap-4 p-space-lg">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon name="draw" />
                  </span>
                  <h3 className="text-title-md font-bold text-on-surface">Brouillon du projet</h3>
                </div>
                <p className="text-body-md text-on-surface-variant">
                  Le brouillon apparaîtra ici dès que le copilote aura assez d'informations. Vous pourrez alors
                  corriger chaque estimation avant de lancer les calculs.
                </p>
                <ul className="flex flex-col gap-2">
                  {[
                    { icon: "widgets", text: "Les fonctionnalités que vous souhaitez" },
                    { icon: "payments", text: "Votre budget en Ariary" },
                    { icon: "event", text: "Votre date limite" },
                    { icon: "location_on", text: "La ville de votre entreprise" },
                  ].map((i) => (
                    <li key={i.text} className="flex items-center gap-2 rounded-lg bg-surface-container-low px-3 py-2 text-body-md text-on-surface">
                      <Icon name={i.icon} className="text-primary" />
                      {i.text}
                    </li>
                  ))}
                </ul>
                <div className="flex gap-1" aria-hidden="true">
                  {[0, 1, 2, 3].map((i) => (
                    <span key={i} className={i < Math.min(messages.length / 2, 4) ? "h-2.5 flex-1 rounded-full bg-secondary" : "h-2.5 flex-1 rounded-full bg-surface-container-highest"} />
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
