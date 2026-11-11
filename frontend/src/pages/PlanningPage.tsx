/** Écran Planning — module D, satisfaction de contraintes (n°3).
 *
 * Affiche le dernier planning réel (GET /schedule) en Gantt, avec le rapport de vérification
 * indépendante. Le « scénario impossible » (date limite à 3 semaines) est un TEST : son diagnostic
 * s'affiche, mais le planning réel n'est pas modifié.
 */
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { FreelancerInfo, Schedule } from "../api/types";
import { AppShell } from "../components/AppShell";
import { DelayPanel, RepairSummary } from "../components/planning/DelayPanel";
import { Gantt } from "../components/planning/Gantt";
import { StepHeader } from "../components/StepHeader";
import { Button, ButtonLink, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatDate, formatInt, formatShortDate } from "../lib/format";
import { stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

function Kpi({ label, value, hint, icon, tone = "primary" }: { label: string; value: string; hint: string; icon: string; tone?: "primary" | "secondary" }) {
  return (
    <Card className="flex items-center gap-space-md p-space-md">
      <span className={cx("flex h-12 w-12 shrink-0 items-center justify-center rounded-xl", tone === "secondary" ? "bg-secondary-container text-on-secondary-container" : "bg-surface-container-low text-primary")}>
        <Icon name={icon} className="text-[24px]" />
      </span>
      <div className="min-w-0">
        <span className="text-label-sm uppercase tracking-wider text-outline">{label}</span>
        <div className="text-financial-display text-on-surface">{value}</div>
        <span className="block text-body-sm text-on-surface-variant">{hint}</span>
      </div>
    </Card>
  );
}

export function PlanningPage() {
  const projectId = Number(useParams().projectId);
  const [busy, setBusy] = useState<"normal" | "impossible" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [test, setTest] = useState<Schedule | null>(null);
  const [showDeps, setShowDeps] = useState(true);

  const data = useAsync(async () => {
    const [project, freelancers] = await Promise.all([api.project(projectId), api.freelancers()]);
    let schedule: Schedule | null = null;
    try {
      schedule = await api.schedule(projectId);
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e;
    }
    return { project, schedule, freelancers: new Map<number, FreelancerInfo>(freelancers.map((f) => [f.id, f])) };
  }, [projectId]);
  const project = data.data?.project;
  const schedule = data.data?.schedule ?? null;

  async function solve(scenario: "normal" | "impossible") {
    setBusy(scenario);
    setActionError(null);
    try {
      const result = await api.solve(projectId, scenario);
      if (scenario === "impossible") {
        setTest(result);
      } else {
        setTest(null);
        const p = await api.project(projectId);
        if (data.data) data.setData({ ...data.data, project: p, schedule: result.status === "OK" ? result : data.data.schedule });
        if (result.status !== "OK") setTest(result); // échec réel : on montre le diagnostic
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  // Lien direct vers le scénario de test (?scenario=impossible), pratique pendant la démonstration.
  const [params, setParams] = useSearchParams();
  useEffect(() => {
    if (params.get("scenario") === "impossible" && schedule && busy === null && !test) {
      setParams({}, { replace: true });
      void solve("impossible");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schedule]);

  const titleOf = (ref: string) => schedule?.assignments.find((a) => a.ref === ref)?.title;
  const noTeam = project !== undefined && project.team.length === 0;
  const totalHours = schedule?.assignments.reduce((s, a) => s + a.hours, 0) ?? 0;
  const margin = schedule?.makespan_days != null ? schedule.working_days_available - schedule.makespan_days : null;

  return (
    <AppShell project={project} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Planning" }]}>
      {data.error && <ErrorBanner message={data.error} onRetry={data.reload} />}
      {data.loading && <Spinner />}
      {project && (
        <div className="flex flex-col gap-space-lg">
          <StepHeader
            step="Étape 4 : Planning"
            algorithm="CSP n°3"
            title="Planning et ordonnancement"
            subtitle="Qui fait quoi, et quand : dépendances, compétences, congés, une tâche à la fois par personne et date limite, tout est respecté et revérifié."
            actions={
              !noTeam && (
                <>
                  <Button variant="outline" icon="science" disabled={busy !== null || !schedule} onClick={() => void solve("impossible")}>
                    {busy === "impossible" ? "Calcul…" : "Scénario impossible (3 semaines)"}
                  </Button>
                  <Button icon="calendar_month" disabled={busy !== null} onClick={() => void solve("normal")}>
                    {busy === "normal" ? "Calcul…" : schedule ? "Recalculer le planning" : "Calculer le planning"}
                  </Button>
                </>
              )
            }
          />

          {actionError && <ErrorBanner message={actionError} />}

          {noTeam && (
            <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
              <Icon name="groups" className="text-[40px] text-primary" />
              <p className="text-title-md text-on-surface">Aucune équipe pour ce projet</p>
              <p className="text-body-md text-on-surface-variant">Le planning répartit les tâches entre les freelances de l'équipe.</p>
              <ButtonLink to={stepPath(project.id, "equipe")} icon="arrow_back">Composer l'équipe</ButtonLink>
            </Card>
          )}

          {/* Diagnostic du scénario de test (ou d'un échec réel) */}
          {test && test.status !== "OK" && (
            <div className="flex flex-col gap-space-md rounded-2xl bg-tertiary-fixed/40 p-space-lg md:flex-row md:items-start md:justify-between">
              <div className="flex items-start gap-space-md">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-tertiary text-on-primary">
                  <Icon name="error_outline" />
                </span>
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-space-xs">
                    <span className="rounded bg-tertiary-fixed px-1.5 py-0.5 text-label-sm uppercase tracking-wider text-tertiary">
                      {test.scenario === "impossible" ? "Scénario de test" : "Alerte de faisabilité"}
                    </span>
                    <span className="text-title-md font-bold text-on-surface">
                      Planning impossible avec une date limite au {formatDate(test.deadline)} ({test.working_days_available} jours ouvrés)
                    </span>
                  </div>
                  {test.diagnostics.map((d) => (
                    <p key={d} className="max-w-3xl text-body-md text-on-surface">{d}</p>
                  ))}
                  <p className="text-body-sm text-on-surface-variant">
                    {test.nodes === 0 ? "Impossibilité détectée avant toute recherche (propagation des contraintes)." : `Prouvé après ${formatInt(test.nodes)} nœuds explorés.`}
                    {test.scenario === "impossible" && " Le planning réel ci-dessous n'est pas modifié."}
                  </p>
                </div>
              </div>
              <Button variant="outline" icon="close" onClick={() => setTest(null)} className="shrink-0 bg-surface-container-lowest">
                Masquer
              </Button>
            </div>
          )}

          {!noTeam && !schedule && busy === null && (
            <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
              <Icon name="calendar_month" className="text-[40px] text-primary" />
              <p className="text-title-md text-on-surface">Le planning n'a pas encore été calculé</p>
              <Button icon="calendar_month" onClick={() => void solve("normal")}>Calculer le planning</Button>
            </Card>
          )}
          {busy === "normal" && !schedule && <Spinner label="Recherche du planning (3 s au maximum)…" />}

          {schedule && (
            <>
              {schedule.alerts && schedule.alerts.length > 0 && (
                <div className="flex flex-col gap-space-sm rounded-2xl bg-tertiary-fixed/40 p-space-md md:flex-row md:items-start md:justify-between">
                  <div className="flex items-start gap-space-md">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-tertiary text-on-primary">
                      <Icon name="event_busy" />
                    </span>
                    <div className="flex flex-col gap-1">
                      <span className="text-label-sm uppercase tracking-wider text-tertiary">Nouvelle indisponibilité déclarée</span>
                      {schedule.alerts.map((a) => <p key={a} className="text-body-md text-on-surface">{a}</p>)}
                    </div>
                  </div>
                  <Button icon="calendar_month" disabled={busy !== null} onClick={() => void solve("normal")} className="shrink-0">
                    Recalculer le planning
                  </Button>
                </div>
              )}
              {schedule.repair && (
                <div className="flex items-start gap-space-md rounded-2xl bg-secondary-container/40 p-space-md">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-on-primary">
                    <Icon name="build" />
                  </span>
                  <div className="flex flex-col gap-1">
                    <span className="text-label-sm uppercase tracking-wider text-on-secondary-container">Planning réparé après un retard</span>
                    <RepairSummary repair={schedule.repair} />
                  </div>
                </div>
              )}
              <section className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-4">
                <Kpi label="Durée" value={`${schedule.makespan_days} jours ouvrés`} hint={`Borne du chemin critique : ${schedule.lower_bound_days} j`} icon="hourglass_top" />
                <Kpi
                  label="Fin des travaux"
                  value={formatDate(schedule.end_date)}
                  hint={margin !== null ? `Marge : ${margin} jour(s) ouvré(s) avant le ${formatShortDate(schedule.deadline)}` : ""}
                  icon="event_available"
                />
                <Kpi label="Ressources" value={`${schedule.team.length} freelances`} hint={`${formatInt(totalHours)} h réparties sur ${schedule.assignments.length} tâches`} icon="badge" />
                {schedule.repair ? (
                  <Kpi
                    label="Résolution"
                    value="Réparé (n°11)"
                    hint={`Min-Conflict · ${formatInt(schedule.repair.steps)} étape(s) · ${schedule.elapsed_ms.toLocaleString("fr-FR")} ms`}
                    icon="build"
                    tone="secondary"
                  />
                ) : (
                  <Kpi
                    label="Résolution"
                    value={schedule.optimal ? "Optimale" : "Meilleure trouvée"}
                    hint={`${formatInt(schedule.nodes)} nœuds · ${schedule.elapsed_ms.toLocaleString("fr-FR")} ms`}
                    icon="auto_graph"
                    tone="secondary"
                  />
                )}
              </section>

              <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
                <Card className="flex min-w-0 flex-col gap-space-md p-space-md sm:p-space-lg lg:col-span-8">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-space-sm">
                      <Icon name="stacked_bar_chart" className="text-[22px] text-primary" />
                      <div>
                        <h3 className="text-title-md font-bold text-on-surface">Chronogramme par freelance</h3>
                        <span className="text-body-sm text-on-surface-variant">
                          Du {formatDate(schedule.start_date)} au {formatDate(schedule.end_date)} · jours ouvrés uniquement
                        </span>
                      </div>
                    </div>
                  </div>
                  <Gantt schedule={schedule} freelancers={data.data!.freelancers} showDependencies={showDeps} />
                  <div className="flex flex-wrap items-center gap-x-space-md gap-y-1 rounded-xl bg-surface-container-low p-space-sm text-body-sm text-on-surface-variant">
                    <span className="flex items-center gap-1.5"><span className="h-3 w-5 rounded-sm outline outline-2 outline-inverse-surface" /> Chemin critique</span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-3 w-5 rounded-sm" style={{ backgroundImage: "repeating-linear-gradient(135deg, rgba(115,119,130,.5) 0 3px, transparent 3px 7px)" }} />
                      Indisponibilité
                    </span>
                    <span className="flex items-center gap-1.5"><Icon name="pin_drop" className="text-[16px]" /> Tâche sur site</span>
                    <span className="flex items-center gap-1.5"><span className="h-3 border-l-2 border-dashed border-error" /> Date limite</span>
                    <label className="flex cursor-pointer items-center gap-1.5">
                      <input type="checkbox" checked={showDeps} onChange={(e) => setShowDeps(e.target.checked)} className="h-4 w-4 accent-primary" />
                      Flèches de dépendance
                    </label>
                    <span className="text-outline">Survolez une barre pour le détail.</span>
                  </div>

                  <details className="rounded-xl bg-surface-container-low p-space-sm">
                    <summary className="cursor-pointer text-label-md text-primary">Voir le planning en tableau ({schedule.assignments.length} tâches)</summary>
                    <div className="mt-2 overflow-x-auto">
                      <table className="w-full text-left text-body-sm">
                        <thead className="text-label-sm uppercase text-on-surface-variant">
                          <tr><th className="p-1.5">Tâche</th><th className="p-1.5">Freelance</th><th className="p-1.5">Début</th><th className="p-1.5">Fin</th><th className="p-1.5 text-right">Jours</th><th className="p-1.5">Après</th></tr>
                        </thead>
                        <tbody>
                          {schedule.assignments.map((a) => (
                            <tr key={a.task_id} className="border-t border-surface-container-high">
                              <td className="p-1.5">
                                <strong className="text-primary">{a.ref}</strong> {a.title}
                                {schedule.repair?.changed.includes(a.ref) && (
                                  <span className="ml-1.5 rounded bg-secondary-container px-1 py-0.5 text-label-sm text-on-secondary-container">déplacée</span>
                                )}
                                {schedule.repair?.task_ref === a.ref && (
                                  <span className="ml-1.5 rounded bg-tertiary-fixed px-1 py-0.5 text-label-sm text-tertiary">en retard</span>
                                )}
                              </td>
                              <td className="p-1.5">{a.freelancer}</td>
                              <td className="whitespace-nowrap p-1.5">{formatShortDate(a.start)}</td>
                              <td className="whitespace-nowrap p-1.5">{formatShortDate(a.end)}</td>
                              <td className="p-1.5 text-right">{a.days}</td>
                              <td className="p-1.5 text-on-surface-variant">{a.depends_on.join(", ") || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </Card>

                <aside className="flex flex-col gap-space-md lg:col-span-4">
                  {schedule.verification && (
                    <Card className="flex flex-col gap-space-md p-space-lg">
                      <div className="flex items-center justify-between border-b border-surface-container-high/60 pb-space-xs">
                        <span className="flex items-center gap-space-xs text-title-md font-bold text-on-surface">
                          <Icon name="verified" className="text-secondary" />
                          Vérification des contraintes
                        </span>
                        <span className={cx("rounded px-1.5 py-0.5 text-label-sm", schedule.verification.constraints_passed ? "bg-secondary-container text-on-secondary-container" : "bg-error-container text-on-error-container")}>
                          {schedule.verification.checks.filter((c) => c.passed).length}/{schedule.verification.checks.length} validées
                        </span>
                      </div>
                      <ul className="flex flex-col gap-space-sm">
                        {schedule.verification.checks.map((c) => (
                          <li key={c.name} className="flex items-start gap-space-sm">
                            <Icon name={c.passed ? "check_circle" : "cancel"} className={cx("mt-0.5 text-[18px]", c.passed ? "text-secondary" : "text-error")} />
                            <div>
                              <span className="text-body-md font-medium text-on-surface">{c.name}</span>
                              {c.details.map((d) => <p key={d} className="text-body-sm text-error">{d}</p>)}
                            </div>
                          </li>
                        ))}
                      </ul>
                      <p className="text-body-sm text-on-surface-variant">
                        Contrôle refait par une fonction indépendante du solveur (verify_schedule), à partir des dates réelles.
                      </p>
                    </Card>
                  )}

                  {schedule.site_order && (
                    <Card className="flex flex-col gap-space-xs p-space-lg">
                      <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface">
                        <Icon name="pin_drop" className="text-[18px] text-primary" />
                        Ordre des visites sur site
                      </span>
                      <p className="text-body-sm text-on-surface">
                        {schedule.site_order.cities.map((c, i) => (
                          <span key={c}>
                            {i > 0 && <span className="text-outline"> → </span>}
                            <strong>{c}</strong>
                          </span>
                        ))}
                      </p>
                      <span className="text-body-sm text-on-surface-variant">
                        D'après la {schedule.site_order.source} ; {schedule.site_order.travel_days} jour ouvré de trajet entre deux villes
                        différentes. Le jour de trajet n'est pas réservé : une tâche à distance peut y être placée.
                      </span>
                    </Card>
                  )}

                  <DelayPanel
                    schedule={schedule}
                    onRepaired={(s) => {
                      setTest(null);
                      if (data.data) data.setData({ ...data.data, schedule: s });
                    }}
                  />

                  <Card className="flex flex-col gap-space-xs p-space-lg">
                    <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-primary">
                      <Icon name="alt_route" className="text-[18px]" />
                      Chemin critique
                    </span>
                    <p className="text-body-sm leading-relaxed text-on-surface">
                      {schedule.critical_path.map((r, i) => (
                        <span key={r}>
                          {i > 0 && <span className="text-outline"> → </span>}
                          <strong className="text-primary">{r}</strong> {titleOf(r)}
                        </span>
                      ))}
                    </p>
                    <span className="text-body-sm text-on-surface-variant">
                      Durée minimale théorique : {schedule.lower_bound_days} jours ouvrés. Le planning en demande {schedule.makespan_days} : la
                      différence vient des ressources (une personne ne fait qu'une tâche à la fois) et des congés.
                    </span>
                  </Card>

                  <Card className="flex flex-col gap-space-xs p-space-lg">
                    <span className="flex items-center gap-space-xs text-label-md uppercase tracking-wider text-on-surface">
                      <Icon name="memory" className="text-[18px] text-primary" />
                      Méthode
                    </span>
                    <p className="text-body-sm text-on-surface-variant">{schedule.method.reason}</p>
                  </Card>

                  <ButtonLink to={stepPath(project.id, "tournee")} iconRight="arrow_forward" className="py-3">
                    Voir la tournée sur site
                  </ButtonLink>
                </aside>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
