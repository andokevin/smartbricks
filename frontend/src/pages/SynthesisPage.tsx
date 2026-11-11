/** Écran Synthèse — l'explication du copilote (module A, n°33) et le récapitulatif du plan.
 *
 * Tout est relu depuis l'API : cadrage mémorisé, planning réel, tournée validée, équipe.
 * Les seuls calculs faits ici sont des additions d'affichage (heures × taux, totaux), indiquées comme telles.
 */
import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api, orNull } from "../api/client";
import type { Explanation, Project } from "../api/types";
import { AppShell } from "../components/AppShell";
import { StepHeader } from "../components/StepHeader";
import { Button, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatAr, formatDate, formatInt, formatShortDate } from "../lib/format";
import { stepPath, type StepKey } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

const PROVIDER: Record<string, string> = { mock: "copilote simulé", claude: "Claude", gemini: "Gemini" };

function Section({ n, title, subtitle, children }: { n: number; title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-space-md break-inside-avoid">
      <div className="flex items-center gap-space-sm">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-fixed text-label-md text-on-primary-fixed">{n}</span>
        <div>
          <h3 className="text-headline-sm font-bold text-on-surface">{title}</h3>
          <span className="text-body-sm text-on-surface-variant">{subtitle}</span>
        </div>
      </div>
      {children}
    </section>
  );
}

function Missing({ projectId, step, label }: { projectId: number; step: StepKey; label: string }) {
  return (
    <Link to={stepPath(projectId, step)} className="flex items-center gap-2 rounded-xl bg-surface-container-low p-space-md text-body-md text-primary hover:bg-surface-container">
      <Icon name="pending" /> {label}
      <Icon name="arrow_forward" className="ml-auto" />
    </Link>
  );
}

export function SynthesisPage() {
  const projectId = Number(useParams().projectId);
  const data = useAsync(async () => {
    const [project, scope, schedule, tour, freelancers] = await Promise.all([
      api.project(projectId),
      orNull(api.scope(projectId)),
      orNull(api.schedule(projectId)),
      orNull(api.tourRun(projectId)),
      api.freelancers(),
    ]);
    return { project, scope, schedule, tour, freelancers };
  }, [projectId]);

  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");

  async function explain(q: string | null) {
    setExplaining(true);
    setExplainError(null);
    try {
      setExplanation(await api.explain(projectId, q));
    } catch (e) {
      setExplainError(e instanceof Error ? e.message : String(e));
    } finally {
      setExplaining(false);
    }
  }

  useEffect(() => {
    if (data.data && !explanation && !explaining) void explain(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.data]);

  const d = data.data;
  const project: Project | undefined = d?.project;

  // ----- données dérivées (affichage)
  const kept = d?.scope?.features.filter((f) => f.selected) ?? [];
  const dropped = d?.scope?.features.filter((f) => !f.selected) ?? [];
  const team = d ? d.freelancers.filter((f) => d.project.team.includes(f.id)) : [];
  const hoursBy = new Map<number, number>();
  d?.schedule?.assignments.forEach((a) => hoursBy.set(a.freelancer_id, (hoursBy.get(a.freelancer_id) ?? 0) + a.hours));
  const teamCost = team.reduce((s, f) => s + (hoursBy.get(f.id) ?? 0) * f.hourly_rate_mga, 0);
  const tourCost = d?.tour?.cost_mga ?? 0;
  const total = teamCost + tourCost;
  const featureEnd = (ref: string): string | null => {
    if (!d?.schedule) return null;
    const taskRefs = new Set(d.project.tasks.filter((t) => t.feature_ref === ref).map((t) => t.ref));
    const ends = d.schedule.assignments.filter((a) => taskRefs.has(a.ref)).map((a) => a.end).sort();
    return ends.at(-1) ?? null;
  };
  const margin = d?.schedule?.makespan_days != null ? d.schedule.working_days_available - d.schedule.makespan_days : null;

  return (
    <AppShell project={project} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Synthèse" }]}>
      {data.error && <ErrorBanner message={data.error} onRetry={data.reload} />}
      {data.loading && <Spinner />}
      {d && project && (
        <div className="flex flex-col gap-space-lg">
          <StepHeader
            step="Étape 6 : Synthèse"
            algorithm="Copilote n°33"
            title="Synthèse de votre projet"
            subtitle="Le plan complet, expliqué en français simple. Chaque chiffre vient des algorithmes des étapes précédentes."
            actions={
              <Button variant="secondary" icon="print" onClick={() => window.print()} className="print:hidden">
                Imprimer / PDF
              </Button>
            }
          />

          {/* Chiffres clés */}
          <section className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
            <Card className="flex flex-col p-space-md">
              <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Valeur livrée</span>
              <span className="text-headline-lg text-on-surface">{d.scope ? formatInt(d.scope.total_value) : "—"}</span>
              <span className="text-body-sm text-on-surface-variant">
                {d.scope ? `${kept.length} brique(s) sur ${d.scope.features.length} · ${d.scope.optimal ? "optimum prouvé" : "approché"}` : "Périmètre à calculer"}
              </span>
            </Card>
            <Card className="flex flex-col p-space-md">
              <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Budget engagé</span>
              <span className="text-financial-display text-on-surface">{total ? formatAr(total) : d.scope ? formatAr(d.scope.total_cost_mga) : "—"}</span>
              <span className="text-body-sm text-on-surface-variant">Plafond : {formatAr(project.budget_mga)}</span>
            </Card>
            <Card className="flex flex-col p-space-md">
              <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Livraison</span>
              <span className="text-financial-display text-on-surface">{d.schedule?.end_date ? formatDate(d.schedule.end_date) : "—"}</span>
              <span className="text-body-sm text-on-surface-variant">
                {d.schedule ? `${d.schedule.makespan_days} jours ouvrés · marge ${margin} j` : "Planning à calculer"}
              </span>
            </Card>
            <Card className="flex flex-col p-space-md">
              <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Équipe</span>
              <span className="text-financial-display text-on-surface">{team.length ? `${team.length} freelances` : "—"}</span>
              <span className="truncate text-body-sm text-on-surface-variant">{team.map((f) => f.name.split(" ")[0]).join(", ") || "Équipe à composer"}</span>
            </Card>
          </section>

          <Card className="flex flex-col gap-space-xl p-space-md md:p-space-xl">
            {/* Lettre du copilote */}
            <div className="-m-space-md flex flex-col gap-space-md rounded-t-xl bg-surface-container-low p-space-md md:-m-space-xl md:p-space-lg">
              <div className="flex flex-wrap items-center justify-between gap-space-md">
                <div className="flex items-center gap-space-md">
                  <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-card">
                    <Icon name="smart_toy" className="text-[32px]" />
                  </span>
                  <div>
                    <h3 className="text-title-md font-bold text-on-surface">Explication du copilote</h3>
                    <span className="text-body-sm text-on-surface-variant">
                      Pour {project.title}
                      {explanation && ` · rédigée par ${PROVIDER[explanation.provider] ?? explanation.provider}`}
                    </span>
                  </div>
                </div>
                {explanation && (
                  <span
                    className={cx(
                      "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-label-sm",
                      explanation.replaced ? "bg-tertiary-fixed text-on-tertiary-fixed" : "bg-secondary-container text-on-secondary-container",
                    )}
                    title={explanation.replaced ? `Nombres absents des données : ${explanation.unknown_numbers.join(", ")}` : undefined}
                  >
                    <Icon name={explanation.replaced ? "rule" : "verified"} className="text-[14px]" />
                    {explanation.replaced ? "Texte remplacé : un chiffre n'était pas dans les données" : "Chaque chiffre vérifié dans les données"}
                  </span>
                )}
              </div>
              {explanation?.fallback_reason && (
                <p className="text-body-sm text-on-tertiary-fixed">Mode simulé activé automatiquement : {explanation.fallback_reason}</p>
              )}
              <div className="rounded-xl bg-surface-container-lowest p-space-md shadow-card md:p-space-lg">
                {explaining && <Spinner label="Le copilote rédige l'explication…" />}
                {explainError && <ErrorBanner message={explainError} onRetry={() => void explain(null)} />}
                {explanation && !explaining && (
                  <div className="flex gap-space-md">
                    <Icon name="format_quote" className="text-[28px] text-primary" />
                    <div className="flex flex-col gap-space-sm">
                      {explanation.text.split(/\n\s*\n/).map((p, i) => (
                        <p key={i} className={cx("leading-relaxed text-on-surface", i === 0 ? "text-body-lg font-medium" : "text-body-md")}>
                          {p}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <form
                className="flex flex-col gap-2 sm:flex-row print:hidden"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  if (question.trim()) void explain(question.trim());
                }}
              >
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  maxLength={1000}
                  placeholder="Une question sur votre plan ? Par exemple : pourquoi le paiement MVola n'est pas dans le sprint 1 ?"
                  className="flex-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-body-md focus:outline-none focus:ring-2 focus:ring-primary-container/20"
                  aria-label="Question au copilote"
                />
                <Button type="submit" icon="send" disabled={explaining || !question.trim()}>Demander</Button>
                <Button type="button" variant="outline" icon="refresh" disabled={explaining} onClick={() => void explain(null)}>Régénérer</Button>
              </form>
            </div>

            {/* 1. Périmètre */}
            <Section n={1} title="Ce qui sera livré" subtitle="Le sprint 1 choisi par le sac à dos multidimensionnel (n°29)">
              {!d.scope ? (
                <Missing projectId={project.id} step="perimetre" label="Calculer le périmètre du sprint 1" />
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-space-md md:grid-cols-2">
                    {kept.map((f) => {
                      const end = featureEnd(f.ref);
                      const desc = project.features.find((x) => x.id === f.id)?.description;
                      return (
                        <div key={f.id} className="flex flex-col gap-2 rounded-xl bg-surface-container-low p-space-md">
                          <div className="flex items-center justify-between gap-2">
                            <span className="rounded-full bg-secondary-container px-2.5 py-0.5 text-label-sm text-on-secondary-container">
                              {f.ref}{f.is_mandatory ? " · obligatoire" : ""}
                            </span>
                            <span className="text-label-sm text-outline">{f.estimated_hours} h · valeur {f.business_value}</span>
                          </div>
                          <h4 className="text-title-md font-bold text-on-surface">{f.title}</h4>
                          {desc && <p className="text-body-md text-on-surface-variant">{desc}</p>}
                          <div className="flex items-center justify-between text-label-sm text-on-surface-variant">
                            <span>Estimé au cadrage : {formatAr(f.estimated_cost_mga)}</span>
                            <span className="text-secondary">{end ? `Prête le ${formatShortDate(end)}` : "Compris au sprint 1"}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {dropped.length > 0 && (
                    <div className="flex items-start gap-2 rounded-lg bg-surface-container-high/40 p-space-sm text-body-sm text-on-surface-variant">
                      <Icon name="inventory_2" className="text-[18px] text-tertiary-container" />
                      <span>
                        <strong className="text-on-surface">Reportées à un prochain sprint :</strong> {dropped.map((f) => f.title).join(", ")}.
                      </span>
                    </div>
                  )}
                </>
              )}
            </Section>

            {/* 2. Équipe */}
            <Section n={2} title="Qui réalise les travaux" subtitle="L'équipe choisie à l'étape 3 (agrégation n°22 et Pareto n°21)">
              {team.length === 0 ? (
                <Missing projectId={project.id} step="equipe" label="Composer l'équipe" />
              ) : (
                <div className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-4">
                  {team.map((f) => {
                    const h = hoursBy.get(f.id) ?? 0;
                    return (
                      <div key={f.id} className="flex flex-col justify-between gap-2 rounded-xl bg-surface-container-low p-space-md">
                        <div>
                          <div className="text-title-md font-bold text-on-surface">{f.name}</div>
                          <div className="flex items-center gap-1 text-body-sm text-outline">
                            <Icon name="location_on" className="text-[14px]" /> {f.city} · {f.hours_per_day} h/jour
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {Object.entries(f.skills).map(([s, l]) => (
                              <span key={s} className="rounded bg-surface-container px-1.5 py-0.5 text-label-sm text-primary">{s} niv. {l}</span>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-surface-container-lowest p-2 text-label-sm">
                          <span className="text-on-surface-variant">{h ? `${h} h × ${formatAr(f.hourly_rate_mga)}` : `${formatAr(f.hourly_rate_mga)} / h`}</span>
                          {h > 0 && <span className="font-bold text-primary">{formatAr(h * f.hourly_rate_mga)}</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>

            {/* 3. Calendrier et tournée */}
            <Section n={3} title="Quand et comment" subtitle="Le planning sous contraintes (n°3) et la tournée sur site (n°30)">
              <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
                <div className="flex flex-col gap-space-sm lg:col-span-7">
                  {!d.schedule ? (
                    <Missing projectId={project.id} step="planning" label="Calculer le planning" />
                  ) : (
                    <>
                      <div className="flex items-start gap-space-md rounded-xl bg-surface-container-low p-space-md">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-container text-primary">
                          <Icon name="calendar_month" />
                        </span>
                        <div className="text-body-md text-on-surface">
                          Du <strong>{formatDate(d.schedule.start_date)}</strong> au <strong>{formatDate(d.schedule.end_date)}</strong> :{" "}
                          {d.schedule.makespan_days} jours ouvrés, pour une date limite au {formatDate(d.schedule.deadline)}.
                          <div className="mt-1 flex items-center gap-1 text-body-sm text-secondary">
                            <Icon name="verified" className="text-[16px]" />
                            {d.schedule.verification?.constraints_passed
                              ? "Toutes les contraintes vérifiées : dépendances, compétences, congés, une tâche à la fois, date limite."
                              : "Vérification non disponible."}
                          </div>
                        </div>
                      </div>
                      <ul className="flex flex-col gap-1.5">
                        {kept.map((f) => (
                          <li key={f.id} className="flex items-center justify-between rounded-lg bg-surface-container-low px-space-md py-2 text-body-md">
                            <span className="text-on-surface"><strong className="text-primary">{f.ref}</strong> {f.title}</span>
                            <span className="text-label-sm text-on-surface-variant">{featureEnd(f.ref) ? `fin le ${formatShortDate(featureEnd(f.ref) as string)}` : "—"}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
                <div className="flex flex-col gap-space-sm rounded-xl bg-surface-container-low p-space-md lg:col-span-5">
                  <span className="flex items-center gap-1.5 text-title-md font-bold text-on-surface">
                    <Icon name="alt_route" className="text-primary" /> Tournée sur site
                  </span>
                  {!d.tour ? (
                    <Missing projectId={project.id} step="tournee" label="Valider la tournée" />
                  ) : (
                    <>
                      <p className="text-body-sm text-on-surface-variant">
                        {d.tour.technician ? `${d.tour.technician.name}, depuis ${d.tour.technician.city}` : `Depuis ${d.tour.order[0]}`} · {d.tour.method}
                      </p>
                      <ol className="flex flex-col gap-1">
                        {d.tour.order.map((c, i) => (
                          <li key={c} className="flex items-center gap-2 text-body-md text-on-surface">
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-container text-label-sm text-on-primary">{i + 1}</span>
                            {c}
                          </li>
                        ))}
                      </ol>
                      <div className="mt-1 flex items-center justify-between rounded-lg bg-surface-container-lowest p-2 text-label-md">
                        <span>{formatInt(d.tour.distance_km)} km</span>
                        <span className="text-primary">{formatAr(d.tour.cost_mga)}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </Section>

            {/* 4. Budget */}
            <Section n={4} title="Combien ça coûte" subtitle="Additions faites à partir des résultats ci-dessus">
              <div className="overflow-x-auto rounded-xl bg-surface-container-low p-space-md">
                <table className="w-full text-left text-body-md">
                  <thead className="text-label-sm uppercase tracking-wider text-on-surface-variant">
                    <tr><th className="pb-space-sm">Poste</th><th className="hidden pb-space-sm sm:table-cell">Détail</th><th className="pb-space-sm text-right">Montant</th></tr>
                  </thead>
                  <tbody className="text-on-surface">
                    {team.map((f) => {
                      const h = hoursBy.get(f.id) ?? 0;
                      return (
                        <tr key={f.id}>
                          <td className="py-2 font-semibold">{f.name}</td>
                          <td className="hidden py-2 text-on-surface-variant sm:table-cell">{h} h planifiées × {formatAr(f.hourly_rate_mga)}</td>
                          <td className="py-2 text-right font-bold text-primary">{formatAr(h * f.hourly_rate_mga)}</td>
                        </tr>
                      );
                    })}
                    {d.tour && (
                      <tr>
                        <td className="py-2 font-semibold">Tournée sur site</td>
                        <td className="hidden py-2 text-on-surface-variant sm:table-cell">{formatInt(d.tour.distance_km)} km</td>
                        <td className="py-2 text-right font-bold text-primary">{formatAr(d.tour.cost_mga)}</td>
                      </tr>
                    )}
                    <tr className="bg-surface-container-high/60">
                      <td className="rounded-l-lg px-2 py-3 font-bold">Total</td>
                      <td className="hidden px-2 py-3 text-on-surface-variant sm:table-cell">Plafond du projet : {formatAr(project.budget_mga)}</td>
                      <td className="rounded-r-lg px-2 py-3 text-right text-headline-sm font-extrabold">{formatAr(total)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              {total > 0 && (
                <div className={cx("flex items-start gap-2 rounded-xl p-space-md text-body-md", total <= project.budget_mga ? "bg-secondary-container/50 text-on-secondary-container" : "bg-tertiary-fixed/50 text-on-tertiary-fixed")}>
                  <Icon name={total <= project.budget_mga ? "check_circle" : "warning"} />
                  <span>
                    {total <= project.budget_mga
                      ? `Reste ${formatAr(project.budget_mga - total)} sur le budget.`
                      : `Dépassement de ${formatAr(total - project.budget_mga)} : le cadrage portait sur le coût des fonctionnalités (taux moyens du marché) ; les taux réels de l'équipe et les frais de tournée s'y ajoutent.`}
                    {d.scope && ` Coût estimé au cadrage : ${formatAr(d.scope.total_cost_mga)}.`}
                  </span>
                </div>
              )}
            </Section>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
