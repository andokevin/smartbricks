/** Écran Tournée — module E, voyageur de commerce (n°30).
 *
 * Chaque changement d'option recalcule un APERÇU (GET /tour, rien n'est enregistré).
 * « Valider la tournée » l'enregistre (POST /tour) : c'est elle que cite la synthèse.
 */
import { lazy, Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { Tour, TourOptions } from "../api/types";
import { AppShell } from "../components/AppShell";
import { StepHeader } from "../components/StepHeader";
import { TourSchema } from "../components/tour/TourSchema";
import { Button, ButtonLink, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatAr, formatInt, formatPct } from "../lib/format";
import { stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

// Leaflet n'est chargé que sur cet écran.
const TourMap = lazy(() => import("../components/tour/TourMap").then((m) => ({ default: m.TourMap })));

export function TourPage() {
  const projectId = Number(useParams().projectId);
  const base = useAsync(
    async () => {
      const [project, cities, freelancers] = await Promise.all([api.project(projectId), api.cities(), api.freelancers()]);
      return { project, cities, freelancers };
    },
    [projectId],
  );
  const [options, setOptions] = useState<TourOptions>({ freelancer_id: null, closed: true, cost_per_km: 1200 });
  const [costText, setCostText] = useState("1200");
  const [tour, setTour] = useState<Tour | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // ?vue=schema : ouvre directement le schéma hors ligne (utile en soutenance sans réseau).
  const [params] = useSearchParams();
  const [view, setView] = useState<"carte" | "schema">(params.get("vue") === "schema" ? "schema" : "carte");
  const [offline, setOffline] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .tourPreview(projectId, options)
      .then((t) => {
        setTour(t);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [projectId, options]);

  async function save() {
    setSaving(true);
    try {
      setTour(await api.saveTour(projectId, options));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const project = base.data?.project;
  const cities = base.data?.cities ?? [];
  const team = (base.data?.freelancers ?? []).filter((f) => project?.team.includes(f.id));
  const field = (base.data?.freelancers ?? []).filter(
    (f) => !project?.team.includes(f.id) && ("Réseau" in f.skills || "Maintenance matériel" in f.skills),
  );
  const gainPct = tour && tour.entered_distance_km > 0 ? tour.gain_km / tour.entered_distance_km : 0;
  let cumulative = 0;

  return (
    <AppShell project={project} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Tournée" }]}>
      {base.error && <ErrorBanner message={base.error} onRetry={base.reload} />}
      {base.loading && <Spinner />}
      {project && (
        <div className="flex flex-col gap-space-lg">
          <StepHeader
            step="Étape 5 : Tournée sur site"
            algorithm="Voyageur de commerce n°30"
            title="Tournée des interventions sur site"
            subtitle="L'ordre de visite des agences qui parcourt le moins de kilomètres. Distances estimées : vol d'oiseau × 1,35 (facteur routier)."
            actions={
              tour && (
                <>
                  {tour.saved ? (
                    <span className="inline-flex items-center gap-1 rounded-lg bg-secondary-container px-3 py-2 text-label-md text-on-secondary-container">
                      <Icon name="check_circle" className="text-[18px]" /> Tournée enregistrée
                    </span>
                  ) : (
                    <Button variant="secondary" icon="save" onClick={() => void save()} disabled={saving || loading}>
                      Valider la tournée
                    </Button>
                  )}
                  <ButtonLink to={stepPath(project.id, "synthese")} iconRight="arrow_forward">
                    Voir la synthèse
                  </ButtonLink>
                </>
              )
            }
          />

          {error && <ErrorBanner message={error} />}

          {tour?.planning_order && !tour.planning_order.matches && (
            <div className="flex items-start gap-space-sm rounded-2xl bg-tertiary-fixed/40 p-space-md text-body-md text-on-surface">
              <Icon name="sync_problem" className="mt-0.5 text-tertiary" />
              <p>
                Le planning actuel fait les interventions dans un autre ordre ({tour.planning_order.cities.join(" → ")}).{" "}
                {tour.saved
                  ? "Recalculez le planning pour qu'il suive cette tournée validée."
                  : "Si vous validez cette tournée, recalculez ensuite le planning pour qu'il la suive."}
              </p>
            </div>
          )}

          {tour && (
            <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
              {/* Carte */}
              <Card className="flex flex-col overflow-hidden lg:col-span-7">
                <div className="flex flex-wrap items-center justify-between gap-space-sm p-space-md">
                  <div className="flex items-center gap-space-sm">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-fixed text-on-primary-fixed">
                      <Icon name="explore" />
                    </span>
                    <div>
                      <h3 className="text-title-md font-bold text-on-surface">Itinéraire numéroté</h3>
                      <span className="text-body-sm text-on-surface-variant">
                        {tour.order.length} villes · départ : {tour.start.name}
                      </span>
                    </div>
                  </div>
                  <div className="flex rounded-lg bg-surface-container-low p-1" role="tablist" aria-label="Affichage">
                    {(["carte", "schema"] as const).map((v) => (
                      <button
                        key={v}
                        role="tab"
                        aria-selected={view === v}
                        onClick={() => setView(v)}
                        className={cx("rounded-md px-3 py-1 text-label-md", view === v ? "bg-surface-container-lowest text-primary shadow-card" : "text-on-surface-variant")}
                      >
                        {v === "carte" ? "Carte" : "Schéma hors ligne"}
                      </button>
                    ))}
                  </div>
                </div>
                {offline && view === "schema" && (
                  <div className="flex items-center gap-2 bg-tertiary-fixed/50 px-space-md py-space-xs text-body-sm text-on-tertiary-fixed">
                    <Icon name="wifi_off" className="text-[18px]" />
                    Carte en ligne indisponible : affichage du schéma à partir des coordonnées des villes.
                  </div>
                )}
                <div className={cx("relative h-[440px] bg-surface-container-low sm:h-[560px]", loading && "opacity-60")}>
                  {view === "carte" ? (
                    <Suspense fallback={<Spinner label="Chargement de la carte…" />}>
                      <TourMap
                        tour={tour}
                        cities={cities}
                        onTilesFailed={() => {
                          setOffline(true);
                          setView("schema");
                        }}
                      />
                    </Suspense>
                  ) : (
                    <div className="flex h-full items-center justify-center p-space-md">
                      <TourSchema tour={tour} cities={cities} />
                    </div>
                  )}
                  <div className="absolute right-3 top-3 z-[500] hidden max-w-[260px] rounded-xl bg-surface-container-lowest/95 px-3.5 py-2.5 shadow-card backdrop-blur-md sm:block">
                    <div className="flex items-center gap-1.5 text-label-sm uppercase tracking-wider text-on-surface">
                      <span className="h-2 w-2 rounded-full bg-secondary" />
                      {tour.method.exact ? "Méthode exacte" : "Méthode approchée"}
                    </div>
                    <p className="text-label-md text-primary">{tour.method.method}</p>
                    <p className="text-body-sm text-on-surface-variant">{tour.method.reason}</p>
                  </div>
                </div>
                {/* Méthode, sous la carte sur téléphone (sur ordinateur, elle est en surimpression) */}
                <div className="flex flex-col gap-0.5 border-t border-surface-container-high px-space-md py-space-sm sm:hidden">
                  <span className="text-label-sm uppercase tracking-wider text-on-surface">
                    {tour.method.exact ? "Méthode exacte" : "Méthode approchée"} : <span className="text-primary">{tour.method.method}</span>
                  </span>
                  <p className="text-body-sm text-on-surface-variant">{tour.method.reason}</p>
                </div>
                {/* Options */}
                <div className="flex flex-col gap-space-sm bg-surface-container-low p-space-md sm:flex-row sm:flex-wrap sm:items-end">
                  <label className="flex flex-1 flex-col gap-1 text-label-sm text-on-surface-variant">
                    Technicien (ville de départ)
                    <select
                      value={options.freelancer_id ?? ""}
                      onChange={(e) => setOptions((o) => ({ ...o, freelancer_id: e.target.value ? Number(e.target.value) : null }))}
                      className="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md text-on-surface"
                    >
                      <option value="">Automatique (selon le planning)</option>
                      {team.length > 0 && (
                        <optgroup label="Équipe du projet">
                          {team.map((f) => <option key={f.id} value={f.id}>{f.name} — {f.city}</option>)}
                        </optgroup>
                      )}
                      <optgroup label="Autres techniciens réseau / maintenance">
                        {field.map((f) => <option key={f.id} value={f.id}>{f.name} — {f.city}</option>)}
                      </optgroup>
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-label-sm text-on-surface-variant">
                    Coût par km
                    <span className="relative w-fit">
                      <input
                        type="number"
                        min={1}
                        value={costText}
                        onChange={(e) => setCostText(e.target.value)}
                        onBlur={() => {
                          const n = Math.max(1, Math.round(Number(costText)) || 1200);
                          setCostText(String(n));
                          setOptions((o) => ({ ...o, cost_per_km: n }));
                        }}
                        className="w-32 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 pr-12 text-body-md"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-label-md text-on-surface-variant">Ar/km</span>
                    </span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-surface-container-lowest px-3 py-2.5 text-label-md text-on-surface">
                    <input
                      type="checkbox"
                      checked={options.closed}
                      onChange={(e) => setOptions((o) => ({ ...o, closed: e.target.checked }))}
                      className="h-4 w-4 accent-primary"
                    />
                    Retour à la ville de départ
                  </label>
                </div>
              </Card>

              {/* Détail */}
              <div className="flex flex-col gap-space-md lg:col-span-5">
                <Card className="flex items-start gap-space-sm p-space-md">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-container text-title-md font-bold text-on-primary">
                    {tour.technician ? tour.technician.name.split(" ").map((p) => p[0]).join("").slice(0, 2) : <Icon name="apartment" />}
                  </span>
                  <div className="min-w-0">
                    <span className="text-label-sm uppercase text-on-surface-variant">Départ</span>
                    <h3 className="text-title-md font-bold text-on-surface">{tour.technician?.name ?? tour.start.name}</h3>
                    <p className="text-body-sm text-on-surface-variant">
                      {tour.start.name} · {tour.start.reason}
                    </p>
                  </div>
                </Card>

                <div className="flex items-center gap-space-sm rounded-xl bg-gradient-to-r from-secondary-fixed/40 to-primary-fixed/40 p-space-md shadow-card">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary text-on-secondary">
                    <Icon name="trending_down" className="text-[22px]" />
                  </span>
                  <div>
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="text-headline-sm font-extrabold text-secondary">−{formatPct(gainPct)}</span>
                      <span className="text-title-md font-bold text-on-surface">par rapport à l'ordre saisi</span>
                    </div>
                    <p className="text-body-sm text-on-surface-variant">
                      {formatInt(tour.gain_km)} km et {formatAr(tour.gain_mga)} économisés ({formatInt(tour.entered_distance_km)} km dans l'ordre : {tour.entered_order.join(" → ")}).
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-3">
                  <Card className="flex flex-col p-3.5">
                    <span className="text-label-sm uppercase text-on-surface-variant">Distance</span>
                    <span className="text-financial-display text-primary">{formatInt(tour.distance_km)} km</span>
                    <span className="text-body-sm text-on-surface-variant">{tour.closed ? "boucle fermée" : "chemin ouvert"}</span>
                  </Card>
                  <Card className="flex flex-col p-3.5">
                    <span className="text-label-sm uppercase text-on-surface-variant">Coût</span>
                    <span className="text-financial-display text-on-surface">{formatAr(tour.cost_mga)}</span>
                    <span className="text-body-sm text-on-surface-variant">{formatInt(tour.cost_per_km)} Ar/km</span>
                  </Card>
                  <Card className="flex flex-col p-3.5">
                    <span className="text-label-sm uppercase text-on-surface-variant">Route</span>
                    <span className="text-financial-display text-secondary">{tour.duration_h.toLocaleString("fr-FR")} h</span>
                    <span className="text-body-sm text-on-surface-variant">à 40 km/h de moyenne</span>
                  </Card>
                </div>

                <Card className="flex flex-col p-space-md">
                  <div className="mb-space-md flex items-center justify-between">
                    <span className="flex items-center gap-2 text-title-md font-bold text-on-surface">
                      <Icon name="alt_route" className="text-primary" />
                      Feuille de route
                    </span>
                    <span className="rounded bg-surface-container-high px-2 py-0.5 text-label-sm text-on-surface-variant">
                      {tour.order.length} étapes
                    </span>
                  </div>
                  <ol className="relative flex flex-col">
                    <span className="absolute bottom-4 left-4 top-4 w-0.5 bg-surface-container-highest" aria-hidden="true" />
                    {tour.order.map((stop, i) => {
                      const leg = tour.legs[i - 1];
                      if (leg) cumulative += leg.km;
                      return (
                        <li key={stop.name} className="flex flex-col">
                          {leg && (
                            <span className="my-1.5 ml-10 flex w-fit items-center gap-2 rounded bg-surface-container px-2.5 py-1 text-label-sm text-on-surface-variant">
                              <Icon name="directions_car" className="text-[14px] text-primary" />
                              {formatInt(leg.km)} km depuis {leg.from}
                            </span>
                          )}
                          <div className="relative flex items-start gap-space-sm">
                            <span className={cx("z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-label-md shadow-card", i === 0 ? "bg-primary text-on-primary" : "bg-primary-container text-on-primary")}>
                              {stop.step}
                            </span>
                            <div className="flex flex-1 items-center justify-between rounded-lg bg-surface-container-low p-3">
                              <span className="text-title-md font-bold text-on-surface">{stop.name}</span>
                              <span className="text-label-sm text-on-surface-variant">{i === 0 ? "Départ" : `${formatInt(cumulative)} km cumulés`}</span>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                    {tour.closed && tour.legs.length >= tour.order.length && (
                      <li className="ml-10 mt-1.5 flex w-fit items-center gap-2 rounded bg-surface-container-high px-2.5 py-1 text-label-sm text-on-surface">
                        <Icon name="keyboard_return" className="text-[14px] text-secondary" />
                        Retour à {tour.start.name} : {formatInt(tour.legs.at(-1)?.km ?? 0)} km
                      </li>
                    )}
                  </ol>
                </Card>
              </div>
            </div>
          )}
          {!tour && loading && <Spinner label="Calcul de la tournée…" />}
        </div>
      )}
    </AppShell>
  );
}
