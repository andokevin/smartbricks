/** Écran Périmètre — module B, sac à dos multidimensionnel (n°29).
 *
 * Affiche le dernier cadrage calculé (GET /scope). Le client peut corriger une estimation
 * (PATCH /features/{id}) : le cadrage est alors relancé automatiquement (POST /scope).
 * Tous les chiffres viennent de l'algorithme ; l'écran ne calcule rien.
 */
import { useState } from "react";
import { useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { FeaturePatch, Project, Scope, ScopeFeature } from "../api/types";
import { AppShell } from "../components/AppShell";
import { StepHeader } from "../components/StepHeader";
import { Button, ButtonLink, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatAr, formatInt, formatPct } from "../lib/format";
import { stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

function Gauge({ label, used, max, format, icon, tone }: {
  label: string;
  used: number;
  max: number;
  format: (n: number) => string;
  icon: string;
  tone: "primary" | "primary-container";
}) {
  const ratio = max > 0 ? used / max : 0;
  return (
    <div className="flex flex-col gap-space-xs rounded-lg bg-surface-container-low p-space-md">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface-variant">
          <Icon name={icon} className="text-[18px] text-primary" />
          {label}
        </span>
        <span className={cx("rounded px-1.5 py-0.5 text-label-sm text-on-primary", tone === "primary" ? "bg-primary" : "bg-primary-container")}>
          {formatPct(ratio)} utilisé
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-2">
        <span className="flex items-baseline gap-space-xs">
          <span className="text-financial-display tracking-tight text-primary">{format(used)}</span>
          <span className="text-body-sm text-on-surface-variant">/ {format(max)}</span>
        </span>
        <span className="rounded bg-secondary-container px-1.5 py-0.5 text-label-sm text-on-secondary-container">
          Reste : {format(Math.max(0, max - used))}
        </span>
      </div>
      <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-surface-container-high">
        <div className={cx("h-full rounded-full transition-all duration-500", tone === "primary" ? "bg-primary" : "bg-primary-container")} style={{ width: `${Math.min(100, ratio * 100)}%` }} />
      </div>
    </div>
  );
}

/** Première phrase de la raison d'exclusion (la partie chiffrée) ; le texte complet reste en infobulle. */
function shortReason(reason: string): string {
  const first = reason.split(". ")[0] ?? reason;
  return first.endsWith(".") ? first : `${first}.`;
}

function ValueBar({ value, muted }: { value: number; muted?: boolean }) {
  return (
    <span className="inline-flex flex-col items-center">
      <span className={cx("text-label-md", muted ? "text-outline" : "text-on-surface")}>
        {value}
        <span className="font-normal text-outline">/100</span>
      </span>
      <span className="mt-0.5 h-1 w-12 overflow-hidden rounded-full bg-surface-container-high">
        <span className={cx("block h-full rounded-full", muted ? "bg-outline-variant" : "bg-secondary")} style={{ width: `${value}%` }} />
      </span>
    </span>
  );
}

function StatusCell({ f }: { f: ScopeFeature }) {
  if (f.selected) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-secondary-container px-2.5 py-1 text-label-sm text-on-secondary-container">
        <Icon name="check_circle" className="text-[16px] text-secondary" />
        Retenue
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-surface-container-highest px-2 py-0.5 text-label-sm text-on-surface-variant">
      <Icon name="remove_circle_outline" className="text-[14px]" />
      Écartée
    </span>
  );
}

/** Champ numérique qui n'envoie la correction qu'en quittant le champ (et seulement si elle change). */
function NumberCell({ value, min, max, onCommit, label, suffix }: {
  value: number;
  min: number;
  max?: number;
  onCommit: (n: number) => void;
  label: string;
  suffix?: string;
}) {
  const [text, setText] = useState(String(value));
  return (
    <span className="inline-flex items-center gap-1">
      <input
        type="number"
        min={min}
        max={max}
        value={text}
        aria-label={label}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          const n = Math.min(max ?? Number.MAX_SAFE_INTEGER, Math.max(min, Math.round(Number(text))));
          if (!Number.isFinite(n)) return setText(String(value));
          setText(String(n));
          if (n !== value) onCommit(n);
        }}
        className="w-16 rounded-md border border-outline-variant bg-surface-container-lowest px-1.5 py-1 text-right text-label-md focus:outline-none focus:ring-2 focus:ring-primary-container/20"
      />
      {suffix}
    </span>
  );
}

export function ScopePage() {
  const projectId = Number(useParams().projectId);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const data = useAsync(async () => {
    const project = await api.project(projectId);
    let scope: Scope | null = null;
    try {
      scope = await api.scope(projectId);
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e;
    }
    return { project, scope };
  }, [projectId]);
  const project: Project | undefined = data.data?.project;
  const scope = data.data?.scope ?? null;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      const s = await api.runScope(projectId); // d'abord le calcul…
      const p = await api.project(projectId); // …puis le projet, avec son nouveau statut
      data.setData({ project: p, scope: s });
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function rerun() {
    if (project && (project.status === "TEAM_SELECTED" || project.status === "PLANNED")) {
      const ok = window.confirm("Relancer le cadrage remet le projet à l'étape Périmètre : l'équipe et le planning devront être refaits. Continuer ?");
      if (!ok) return;
    }
    void run(async () => undefined);
  }

  function patch(f: ScopeFeature, change: FeaturePatch) {
    void run(() => api.patchFeature(f.id, change));
  }

  const features = scope?.features ?? [];
  const kept = features.filter((f) => f.selected);
  const titleOf = (ref: string) => features.find((f) => f.ref === ref)?.title ?? ref;

  return (
    <AppShell project={project} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Périmètre" }]}>
      {data.error && <ErrorBanner message={data.error} onRetry={data.reload} />}
      {data.loading && <Spinner />}
      {project && (
        <div className="flex flex-col gap-space-lg">
          <StepHeader
            step="Étape 2 : Périmètre"
            algorithm="Sac à dos n°29"
            title="Périmètre du sprint 1"
            subtitle="Les fonctionnalités qui apportent le plus de valeur sans dépasser ni votre budget en Ariary, ni vos heures. Corrigez une estimation : le calcul est relancé."
            actions={
              <>
                {scope && (
                  <Button variant="secondary" icon={editing ? "check" : "tune"} onClick={() => setEditing((v) => !v)} disabled={busy}>
                    {editing ? "Terminer les corrections" : "Corriger les estimations"}
                  </Button>
                )}
                <Button icon="auto_fix_high" onClick={rerun} disabled={busy}>
                  {busy ? "Calcul…" : scope ? "Relancer l'arbitrage" : "Calculer le périmètre"}
                </Button>
              </>
            }
          />

          {actionError && <ErrorBanner message={actionError} />}

          {!scope && !busy && (
            <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
              <Icon name="inventory_2" className="text-[40px] text-primary" />
              <p className="text-title-md text-on-surface">Le périmètre n'a pas encore été calculé</p>
              <p className="max-w-lg text-body-md text-on-surface-variant">
                L'algorithme va choisir, parmi les {project.features.length} fonctionnalités, la combinaison la plus utile
                qui tient dans {formatAr(project.budget_mga)} et {formatInt(project.budget_hours)} heures.
              </p>
              <Button icon="auto_fix_high" onClick={rerun}>
                Calculer le périmètre
              </Button>
            </Card>
          )}
          {busy && !scope && <Spinner label="Calcul du périmètre…" />}

          {scope && (
            <>
              {!scope.feasible && (
                <div className="flex items-start gap-space-md rounded-xl bg-tertiary-fixed/40 p-space-lg">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-tertiary text-on-primary">
                    <Icon name="error_outline" />
                  </span>
                  <div>
                    <div className="text-title-md font-bold text-on-surface">Les fonctionnalités obligatoires dépassent déjà vos moyens</div>
                    <p className="mt-1 text-body-md text-on-surface-variant">{scope.message}</p>
                  </div>
                </div>
              )}

              {/* Jauges */}
              <Card className="flex flex-col gap-space-md p-space-lg">
                <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
                  <Gauge label="Budget" used={scope.total_cost_mga} max={scope.budget_mga} format={formatAr} icon="payments" tone="primary" />
                  <Gauge label="Heures" used={scope.total_hours} max={scope.budget_hours} format={(n) => `${formatInt(n)} h`} icon="schedule" tone="primary-container" />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-space-md border-t border-surface-container-high/50 pt-space-xs text-body-sm text-on-surface-variant">
                  <div className="flex flex-wrap items-center gap-space-lg">
                    <span className="flex items-center gap-space-xs">
                      <Icon name="view_in_ar" className="text-[18px] text-primary" />
                      Briques retenues : <strong className="text-on-surface">{kept.length} / {features.length}</strong>
                    </span>
                    <span className="flex items-center gap-space-xs">
                      <Icon name="trending_up" className="text-[18px] text-secondary" />
                      Valeur métier totale : <strong className="text-on-surface">{formatInt(scope.total_value)}</strong>
                    </span>
                  </div>
                  <span className="flex items-center gap-1.5 text-label-sm text-outline">
                    <Icon name={scope.optimal ? "verified" : "speed"} className="text-[16px] text-secondary" />
                    {scope.method.method} · {formatInt(scope.nodes)} nœuds · {scope.elapsed_ms.toLocaleString("fr-FR")} ms
                  </span>
                </div>
              </Card>

              <div className="grid grid-cols-1 items-start gap-space-lg xl:grid-cols-12">
                {/* Tableau des briques */}
                <div className="flex flex-col gap-space-md xl:col-span-8">
                  <Card className="overflow-hidden">
                    <div className="flex flex-wrap items-center justify-between gap-2 p-space-md">
                      <div className="flex items-center gap-space-sm">
                        <h3 className="text-title-md font-bold text-on-surface">Sélection des briques du sprint 1</h3>
                        <span className="rounded-full bg-surface-container px-2 py-0.5 text-label-sm text-primary">{features.length} analysées</span>
                      </div>
                      {editing && <span className="text-label-sm text-tertiary-container">Mode correction : chaque modification relance le calcul</span>}
                    </div>

                    {/* Ordinateur : tableau */}
                    <div className={cx("hidden overflow-x-auto md:block", busy && "pointer-events-none opacity-60")}>
                      <table className="w-full border-collapse text-left text-body-sm">
                        <thead>
                          <tr className="bg-surface-container-low text-label-sm uppercase tracking-wider text-on-surface-variant">
                            <th className="px-space-md py-space-sm">Fonctionnalité</th>
                            <th className="px-space-sm py-space-sm text-center">Valeur</th>
                            <th className="px-space-sm py-space-sm text-right">Heures</th>
                            <th className="px-space-sm py-space-sm text-right">Coût</th>
                            <th className="px-space-sm py-space-sm text-center">Obligatoire</th>
                            <th className="px-space-md py-space-sm text-right">Statut</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-container-high/40">
                          {features.map((f) => (
                            <tr key={`${f.id}-${f.business_value}-${f.estimated_hours}`} className={cx("align-top transition-colors hover:bg-surface-container-low/60", !f.selected && "bg-surface/60")}>
                              <td className="px-space-md py-space-sm">
                                <div className="flex items-center gap-1.5">
                                  <span className={cx("rounded px-1 text-label-sm", f.selected ? "bg-surface-container text-primary" : "bg-surface-container-high text-on-surface-variant")}>
                                    {f.ref}
                                  </span>
                                  <span className={cx("text-body-md", f.selected ? "font-bold text-on-surface" : "text-on-surface-variant")}>{f.title}</span>
                                </div>
                                {f.depends_on.length > 0 && (
                                  <div className="mt-0.5 text-body-sm text-outline">Dépend de : {f.depends_on.map(titleOf).join(", ")}</div>
                                )}
                                {f.reason && (
                                  <div className="mt-1 max-w-md text-body-sm text-tertiary-container" title={f.reason}>
                                    {shortReason(f.reason)}
                                  </div>
                                )}
                              </td>
                              <td className="px-space-sm py-space-sm text-center">
                                {editing ? (
                                  <NumberCell value={f.business_value} min={1} max={100} label={`Valeur de ${f.title}`} onCommit={(n) => patch(f, { business_value: n })} />
                                ) : (
                                  <ValueBar value={f.business_value} muted={!f.selected} />
                                )}
                              </td>
                              <td className="px-space-sm py-space-sm text-right text-on-surface">
                                {editing ? (
                                  <NumberCell value={f.estimated_hours} min={1} label={`Heures de ${f.title}`} suffix="h" onCommit={(n) => patch(f, { estimated_hours: n })} />
                                ) : (
                                  `${f.estimated_hours} h`
                                )}
                              </td>
                              <td className={cx("whitespace-nowrap px-space-sm py-space-sm text-right text-body-md font-bold", f.selected ? "text-primary" : "text-outline")}>
                                {formatAr(f.estimated_cost_mga)}
                              </td>
                              <td className="px-space-sm py-space-sm text-center">
                                {editing ? (
                                  <input type="checkbox" checked={f.is_mandatory} onChange={(e) => patch(f, { is_mandatory: e.target.checked })} className="h-4 w-4 cursor-pointer accent-primary" aria-label={`${f.title} obligatoire`} />
                                ) : f.is_mandatory ? (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5 text-label-sm text-primary">
                                    <Icon name="check" className="text-[14px]" /> Oui
                                  </span>
                                ) : (
                                  <span className="text-label-sm text-outline">Non</span>
                                )}
                              </td>
                              <td className="px-space-md py-space-sm text-right">
                                <StatusCell f={f} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Mobile : cartes */}
                    <ul className={cx("flex flex-col gap-2 p-space-sm md:hidden", busy && "pointer-events-none opacity-60")}>
                      {features.map((f) => (
                        <li key={f.id} className={cx("flex flex-col gap-1.5 rounded-xl p-3", f.selected ? "bg-surface-container-low" : "bg-surface")}>
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-body-md font-bold text-on-surface">
                              <span className="text-primary">{f.ref}</span> {f.title}
                            </span>
                            <StatusCell f={f} />
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-body-sm text-on-surface-variant">
                            <span>Valeur {f.business_value}/100</span>
                            <span>{f.estimated_hours} h</span>
                            <span className="font-bold text-primary">{formatAr(f.estimated_cost_mga)}</span>
                            {f.is_mandatory && <span className="text-secondary">Obligatoire</span>}
                          </div>
                          {f.reason && <p className="text-body-sm text-tertiary-container">{shortReason(f.reason)}</p>}
                        </li>
                      ))}
                    </ul>

                    <div className="flex flex-wrap items-center gap-space-md bg-surface-container-low p-space-md text-label-sm text-on-surface-variant">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-secondary" /> {kept.length} retenue(s) pour le sprint 1
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-outline-variant" /> {features.length - kept.length} écartée(s), avec la raison
                      </span>
                    </div>
                  </Card>
                </div>

                {/* Colonne latérale */}
                <aside className="flex flex-col gap-space-md xl:col-span-4">
                  <Card className="flex flex-col gap-space-sm p-space-md">
                    <div className="flex items-center gap-space-xs border-b border-surface-container-high/60 pb-space-xs">
                      <Icon name="psychology" className="text-primary" />
                      <h3 className="text-title-md font-bold text-primary">Et si ?</h3>
                    </div>
                    {scope.what_if.map((w) => (
                      <div key={w.increase_pct} className="flex flex-col gap-1.5 rounded-lg bg-surface-container-low p-space-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-label-md text-primary">
                            +{w.increase_pct} % · +{formatAr(w.extra_budget_mga)}
                          </span>
                          {w.value_gain > 0 && <span className="text-label-sm text-secondary">+{w.value_gain} de valeur</span>}
                        </div>
                        {w.added.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {w.added.map((r) => (
                              <span key={r} className="rounded bg-secondary-container px-1.5 py-0.5 text-label-sm text-on-secondary-container">
                                + {titleOf(r)}
                              </span>
                            ))}
                            {w.removed.map((r) => (
                              <span key={r} className="rounded bg-surface-container-highest px-1.5 py-0.5 text-label-sm text-on-surface-variant">
                                − {titleOf(r)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-body-sm text-on-surface-variant">{w.message}</p>
                        )}
                        <span className="text-body-sm text-outline">Budget simulé : {formatAr(w.new_budget_mga)}</span>
                      </div>
                    ))}
                    <p className="text-body-sm text-on-surface-variant">
                      Pour adopter un scénario, augmentez le budget du projet : le calcul complet sera refait.
                    </p>
                  </Card>

                  <Card className="flex flex-col gap-space-sm p-space-md">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-space-xs text-title-md font-bold text-on-surface">
                        <Icon name="memory" className="text-primary" />
                        Comment c'est calculé
                      </span>
                      <span className={cx("rounded-full px-2 py-0.5 text-label-sm", scope.optimal ? "bg-secondary-container text-on-secondary-container" : "bg-tertiary-fixed text-on-tertiary-fixed")}>
                        {scope.optimal ? "Optimum prouvé" : "Solution approchée"}
                      </span>
                    </div>
                    <p className="text-body-sm text-on-surface-variant">{scope.method.reason}</p>
                    <div className="flex items-start gap-2 rounded-lg bg-surface-container-low p-space-sm text-body-sm">
                      <Icon name={scope.verification.length === 0 ? "verified_user" : "warning"} className={cx("text-[18px]", scope.verification.length === 0 ? "text-secondary" : "text-error")} />
                      <span className="text-on-surface">
                        {scope.verification.length === 0
                          ? "Vérification indépendante : budget, heures, obligatoires et dépendances respectés."
                          : scope.verification.join(" ")}
                      </span>
                    </div>
                  </Card>

                  <div className="flex flex-col gap-space-md rounded-xl bg-primary p-space-lg text-on-primary shadow-card">
                    <div className="flex items-center gap-space-sm">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-container-lowest/15">
                        <Icon name="rocket_launch" className="text-[24px]" />
                      </span>
                      <div>
                        <span className="text-label-sm uppercase tracking-wider text-primary-fixed">Prochaine étape</span>
                        <div className="text-title-md font-extrabold">Choisir l'équipe</div>
                      </div>
                    </div>
                    <p className="text-body-sm text-primary-fixed">
                      {scope.feasible
                        ? `Le sprint 1 compte ${kept.length} brique(s) pour ${formatInt(scope.total_hours)} h et ${formatAr(scope.total_cost_mga)}.`
                        : "Rendez d'abord le périmètre réalisable."}
                    </p>
                    {scope.feasible && (
                      <ButtonLink to={stepPath(project.id, "equipe")} variant="secondary" iconRight="arrow_forward" className="bg-surface-container-lowest">
                        Choisir mon équipe freelance
                      </ButtonLink>
                    )}
                  </div>
                </aside>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
