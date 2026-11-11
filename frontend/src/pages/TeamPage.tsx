/** Écran Équipe — module C : agrégation pondérée (n°22) et optimisation de Pareto (n°21).
 *
 * Les curseurs changent les poids : le classement est recalculé par l'API (GET /matching).
 * Le client compose son équipe à la main ou applique l'équipe suggérée (POST /team).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { CriterionKey, Matching, Project, Weights } from "../api/types";
import { AppShell } from "../components/AppShell";
import { StepHeader } from "../components/StepHeader";
import { FreelancerCard } from "../components/team/FreelancerCard";
import { ParetoChart } from "../components/team/ParetoChart";
import { Button, ButtonLink, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { CRITERIA, PRESET_NAMES } from "../lib/criteria";
import { formatInt, formatPct } from "../lib/format";
import { stepPath } from "../lib/steps";

const VISIBLE = 8;

export function TeamPage() {
  const projectId = Number(useParams().projectId);
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [matching, setMatching] = useState<Matching | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notScoped, setNotScoped] = useState(false);

  const [preset, setPreset] = useState<string | null>("Équilibré");
  const [weights, setWeights] = useState<Weights | null>(null); // curseurs (0–100), null = préréglage
  const [pareto, setPareto] = useState<CriterionKey[]>(["cost", "speed", "quality"]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(false);
  const [saving, setSaving] = useState(false);
  const [teamMessage, setTeamMessage] = useState<{ warnings: string[]; absorbable: boolean } | null>(null);
  const firstLoad = useRef(true);
  // Position affichée des curseurs (en préréglage : les poids renvoyés par l'API pour ce préréglage).
  const [sliders, setSliderValues] = useState<Weights>({ cost: 0.2, speed: 0.2, quality: 0.2, availability: 0.2, coverage: 0.2 });

  useEffect(() => {
    api.project(projectId).then((p) => {
      setProject(p);
      setSelected(new Set(p.team));
    }).catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [projectId]);

  // Classement : rechargé quand les poids, le préréglage ou les critères de Pareto changent.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      api
        .matching(projectId, { preset: weights ? undefined : (preset ?? undefined), weights: weights ?? undefined, pareto })
        .then((m) => {
          setMatching(m);
          setError(null);
          if (!weights) setSliderValues(m.weights);
          firstLoad.current = false;
        })
        .catch((e: unknown) => {
          if (e instanceof ApiError && e.status === 409) setNotScoped(true);
          else setError(e instanceof Error ? e.message : String(e));
        })
        .finally(() => setLoading(false));
    }, firstLoad.current ? 0 : 300);
    return () => window.clearTimeout(timer);
  }, [projectId, preset, weights, pareto]);

  const sliderSum = Object.values(weights ?? sliders).reduce((s, v) => s + v, 0) || 1;

  function moveSlider(key: CriterionKey, value: number) {
    const base = weights ?? { ...sliders };
    const next = { ...base, [key]: value };
    setWeights(next);
    setSliderValues(next);
    setPreset(null);
  }

  function choosePreset(name: string) {
    setPreset(name);
    setWeights(null);
  }

  function togglePareto(key: CriterionKey) {
    setPareto((p) => (p.includes(key) ? (p.length > 2 ? p.filter((k) => k !== key) : p) : [...p, key]));
  }

  function toggle(id: number) {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function save(body: Parameters<typeof api.setTeam>[1], thenPlan: boolean) {
    setSaving(true);
    setError(null);
    try {
      const out = await api.setTeam(projectId, body);
      setSelected(new Set(out.members.map((m) => m.id)));
      setTeamMessage({ warnings: out.warnings, absorbable: out.absorbable });
      setProject(await api.project(projectId));
      if (thenPlan) navigate(stepPath(projectId, "planning"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const suggestBody = () =>
    weights ? { suggested: true, weights } : { suggested: true, preset: preset ?? "Équilibré" };

  // Couverture des tâches retenues par la sélection (affichage, aucune décision).
  const coverage = useMemo(() => {
    if (!matching) return null;
    const team = matching.ranking.filter((r) => selected.has(r.id));
    const covered = matching.tasks.filter((t) => team.some((r) => (r.skills[t.skill] ?? 0) >= t.min_level));
    const missing = [...new Set(matching.tasks.filter((t) => !covered.includes(t)).map((t) => `${t.skill} niv. ${t.min_level}`))];
    return {
      tasks: covered.length,
      hours: covered.reduce((s, t) => s + t.hours, 0),
      missing,
    };
  }, [matching, selected]);

  const suggestedIds = new Set(matching?.suggested_team.members ?? []);
  const rows = matching?.ranking ?? [];
  const visible = showAll ? rows : rows.filter((r, i) => i < VISIBLE || selected.has(r.id) || suggestedIds.has(r.id));
  const teamSaved = project !== null && project.team.length > 0 && [...selected].sort().join() === [...project.team].sort().join();

  return (
    <AppShell project={project ?? undefined} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Équipe" }]}>
      <div className="flex flex-col gap-space-lg">
        <StepHeader
          step="Étape 3 : Équipe"
          algorithm="Agrégation n°22 · Pareto n°21"
          title="Choisir mon équipe freelance"
          subtitle="Réglez vos priorités : le classement se met à jour. Le front de Pareto montre les compromis qu'aucun autre freelance ne bat sur tous les critères à la fois."
          actions={
            !notScoped && (
              <>
                <Button variant="secondary" icon="auto_awesome" disabled={saving || !matching} onClick={() => void save(suggestBody(), false)}>
                  Équipe suggérée
                </Button>
                <Button iconRight="arrow_forward" disabled={saving || selected.size === 0} onClick={() => void save({ freelancer_ids: [...selected] }, true)}>
                  Valider l'équipe et planifier
                </Button>
              </>
            )
          }
        />

        {error && <ErrorBanner message={error} />}

        {notScoped && project && (
          <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
            <Icon name="inventory_2" className="text-[40px] text-primary" />
            <p className="text-title-md text-on-surface">Le périmètre du sprint 1 n'est pas encore calculé</p>
            <p className="text-body-md text-on-surface-variant">Le matching porte sur les tâches des fonctionnalités retenues.</p>
            <ButtonLink to={stepPath(project.id, "perimetre")} icon="arrow_back">Aller au périmètre</ButtonLink>
          </Card>
        )}

        {!matching && loading && !notScoped && <Spinner label="Calcul du classement…" />}

        {matching && coverage && (
          <>
            {/* Chiffres clés */}
            <section className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Charge à réaliser</span>
                <span className="text-headline-md font-bold text-on-surface">{formatInt(matching.total_hours)} h</span>
                <span className="text-body-sm text-on-surface-variant">{matching.tasks_considered} tâches du sprint 1</span>
              </Card>
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Jours ouvrés disponibles</span>
                <span className="text-headline-md font-bold text-on-surface">{formatInt(matching.working_days)} j</span>
                <span className="text-body-sm text-on-surface-variant">jusqu'à la date limite</span>
              </Card>
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Freelances classés</span>
                <span className="text-headline-md font-bold text-on-surface">{rows.length}</span>
                <span className="text-body-sm text-on-surface-variant">{matching.fronts[0]?.length ?? 0} sur le front de Pareto</span>
              </Card>
              <div className="flex flex-col rounded-xl bg-primary p-space-md text-on-primary shadow-card">
                <span className="flex items-center gap-1.5 text-label-sm uppercase tracking-wider text-primary-fixed">
                  <span className={cx("h-2 w-2 rounded-full", coverage.missing.length ? "bg-tertiary-fixed-dim" : "bg-secondary-fixed")} />
                  Sélection en direct
                </span>
                <span className="text-headline-md font-bold">{selected.size} freelance{selected.size > 1 ? "s" : ""}</span>
                <span className="text-body-sm text-primary-fixed">
                  {coverage.tasks}/{matching.tasks.length} tâches couvertes · {formatInt(coverage.hours)} h / {formatInt(matching.total_hours)} h
                </span>
              </div>
            </section>

            <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
              {/* Priorités */}
              <aside className="flex flex-col gap-space-md lg:sticky lg:top-20 lg:col-span-4 xl:col-span-3">
                <Card className="flex flex-col gap-space-md p-space-lg">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-space-xs text-title-md font-bold text-on-surface">
                      <Icon name="tune" className="text-primary" />
                      Mes priorités
                    </span>
                    <button className="text-label-sm text-primary hover:underline" onClick={() => choosePreset("Équilibré")}>
                      Réinitialiser
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {PRESET_NAMES.map((name) => (
                      <button
                        key={name}
                        onClick={() => choosePreset(name)}
                        className={cx(
                          "rounded-lg px-2.5 py-1.5 text-label-sm transition-all",
                          preset === name && !weights ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface hover:bg-surface-container-high",
                        )}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                  <div className="flex flex-col gap-space-md">
                    {CRITERIA.map((k) => {
                      const raw = (weights ?? sliders)[k.key];
                      return (
                        <label key={k.key} className="flex flex-col gap-1">
                          <span className="flex items-center justify-between text-label-md">
                            <span className="flex items-center gap-1.5 text-on-surface">
                              <span className="h-2 w-2 rounded-sm" style={{ background: k.color }} />
                              {k.label}
                            </span>
                            <span className="text-primary">{formatPct(raw / sliderSum)}</span>
                          </span>
                          <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={raw}
                            onChange={(e) => moveSlider(k.key, Number(e.target.value))}
                            className="h-1.5 w-full cursor-pointer accent-primary"
                            aria-label={`Poids : ${k.label}`}
                          />
                          <span className="text-label-sm font-normal text-outline">Favorise : {k.better}</span>
                        </label>
                      );
                    })}
                  </div>
                  <div className="flex flex-col gap-1.5 border-t border-surface-container-high pt-space-sm">
                    <span className="text-label-sm text-on-surface-variant">Critères du front de Pareto (au moins 2)</span>
                    <div className="flex flex-wrap gap-1">
                      {CRITERIA.map((k) => (
                        <button
                          key={k.key}
                          onClick={() => togglePareto(k.key)}
                          className={cx(
                            "rounded-md px-2.5 py-1 text-label-sm",
                            pareto.includes(k.key) ? "bg-primary text-on-primary" : "bg-surface-container-low text-on-surface hover:bg-surface-container",
                          )}
                          aria-pressed={pareto.includes(k.key)}
                        >
                          {k.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="flex gap-2 rounded-lg bg-surface-container-low p-space-sm text-body-sm text-on-surface-variant">
                    <Icon name="insights" className="text-[16px] text-primary" />
                    Score = Σ poids × critère normalisé (0 à 1). Les poids sont ramenés à 100 %.
                  </p>
                </Card>
              </aside>

              {/* Classement */}
              <section className={cx("flex flex-col gap-space-md lg:col-span-8 xl:col-span-5", loading && "opacity-70")}>
                <Card className="flex items-center justify-between gap-space-sm p-space-sm pl-space-md">
                  <span className="flex items-center gap-2 text-title-md font-bold text-on-surface">
                    Classement pondéré
                    <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-label-sm text-primary">{matching.preset}</span>
                  </span>
                  {loading && <Icon name="progress_activity" className="animate-spin text-primary" />}
                </Card>
                {visible.map((r) => (
                  <FreelancerCard key={r.id} row={r} selected={selected.has(r.id)} suggested={suggestedIds.has(r.id)} onToggle={() => toggle(r.id)} disabled={saving} />
                ))}
                {rows.length > visible.length && (
                  <Button variant="outline" icon="expand_more" onClick={() => setShowAll(true)}>
                    Afficher les {rows.length - visible.length} autres freelances
                  </Button>
                )}
              </section>

              {/* Pareto et sélection */}
              <aside className="flex flex-col gap-space-md lg:col-span-12 xl:col-span-4">
                <Card className="flex flex-col gap-space-md p-space-lg">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="flex items-center gap-1.5 text-title-md font-bold text-on-surface">
                        <Icon name="scatter_plot" className="text-primary" />
                        Front de Pareto
                      </span>
                      <p className="mt-0.5 text-body-sm text-on-surface-variant">
                        Coût × rapidité. Front calculé sur : {pareto.map((k) => CRITERIA.find((c) => c.key === k)?.label).join(", ")}.
                      </p>
                    </div>
                  </div>
                  <ParetoChart rows={rows} selected={selected} />
                  {pareto.length > 2 && (
                    <p className="text-body-sm text-outline">
                      Un point bleu peut sembler dominé sur ce plan : il est alors meilleur sur un autre critère du front.
                    </p>
                  )}
                </Card>

                <Card className="flex flex-col gap-space-sm p-space-lg">
                  <h4 className="text-label-md uppercase tracking-wider text-on-surface">Ma sélection</h4>
                  {selected.size === 0 && <p className="text-body-sm text-on-surface-variant">Cochez des freelances, ou appliquez l'équipe suggérée.</p>}
                  <ul className="flex flex-col gap-1">
                    {rows.filter((r) => selected.has(r.id)).map((r) => (
                      <li key={r.id} className="flex items-center justify-between rounded-lg bg-surface-container-low px-space-sm py-1.5 text-body-sm">
                        <span className="text-on-surface">{r.name}</span>
                        <span className="text-on-surface-variant">{Object.keys(r.skills).join(", ")}</span>
                      </li>
                    ))}
                  </ul>
                  {coverage.missing.length > 0 && selected.size > 0 && (
                    <div className="flex items-start gap-2 rounded-lg bg-tertiary-fixed/50 p-space-sm text-body-sm text-on-tertiary-fixed">
                      <Icon name="warning" className="text-[18px]" />
                      Compétences non couvertes : {coverage.missing.join(", ")}.
                    </div>
                  )}
                  {teamMessage && (
                    <div className={cx("flex items-start gap-2 rounded-lg p-space-sm text-body-sm", teamMessage.absorbable ? "bg-secondary-container/60 text-on-secondary-container" : "bg-tertiary-fixed/50 text-on-tertiary-fixed")}>
                      <Icon name={teamMessage.absorbable ? "check_circle" : "warning"} className="text-[18px]" />
                      <span>
                        {teamMessage.absorbable ? "Équipe enregistrée : la charge est absorbable avant la date limite." : "Équipe enregistrée, mais :"}{" "}
                        {teamMessage.warnings.join(" ")}
                      </span>
                    </div>
                  )}
                  <Button iconRight="calendar_month" disabled={saving || selected.size === 0} onClick={() => void save({ freelancer_ids: [...selected] }, true)} className="mt-1 w-full py-3">
                    Confirmer l'équipe et passer au planning
                  </Button>
                  {teamSaved && (
                    <ButtonLink to={stepPath(projectId, "planning")} variant="ghost" iconRight="arrow_forward">
                      Équipe déjà enregistrée : voir le planning
                    </ButtonLink>
                  )}
                </Card>
              </aside>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
