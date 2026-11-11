/** Écran « Comparaison des méthodes » (administrateur) : exact contre approché, mesuré par GET /benchmark.
 *
 * Valeur, écart et temps sur le projet choisi, puis sur des instances aléatoires reproductibles
 * de tailles croissantes, qui justifient les seuils du sélecteur de méthode (n°33).
 */
import { useEffect, useState, type ReactNode } from "react";

import { api } from "../api/client";
import type { Benchmark } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { StepHeader } from "../components/StepHeader";
import { AlgoTag, Button, Card, cx, ErrorBanner, Icon, Spinner } from "../components/ui";
import { formatAr, formatInt } from "../lib/format";
import { useAsync } from "../lib/useAsync";

// Ordre fixe de la palette vérifiée : exact, approché 1, approché 2.
const C_EXACT = "#1e5aa8";
const C_A1 = "#eb6834";
const C_A2 = "#1baf7a";

function ms(n: number): string {
  if (n >= 1000) return `${(n / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} s`;
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: n < 1 ? 3 : 1 })} ms`;
}

function pct(n: number): string {
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} %`;
}

function GapBadge({ gap }: { gap: number }) {
  return (
    <span className={cx("rounded px-2 py-0.5 text-label-sm", gap === 0 ? "bg-secondary-container text-on-secondary-container" : "bg-tertiary-fixed text-on-tertiary-fixed")}>
      {gap === 0 ? "Optimum atteint" : `+${pct(gap)} d'écart`}
    </span>
  );
}

/** Barres horizontales comparables (même échelle), valeur affichée à droite. */
function Bars({ title, items }: { title: string; items: { label: string; value: number; display: string; color: string }[] }) {
  const max = Math.max(...items.map((i) => i.value), 1e-9);
  return (
    <div className="flex flex-col gap-1.5 rounded-lg bg-surface-container-lowest p-3 shadow-card">
      <span className="text-body-sm font-semibold text-on-surface">{title}</span>
      {items.map((i) => (
        <div key={i.label} className="flex items-center gap-2">
          <span className="w-24 shrink-0 truncate text-label-sm text-on-surface-variant" title={i.label}>{i.label}</span>
          <div className="h-4 flex-1 overflow-hidden rounded-full bg-surface-container-high">
            <div className="h-full rounded-full" style={{ width: `${Math.max(2, (i.value / max) * 100)}%`, background: i.color }} />
          </div>
          <span className="w-20 shrink-0 text-right text-label-sm text-on-surface">{i.display}</span>
        </div>
      ))}
    </div>
  );
}

function AlgoSection({ icon, number, name, title, subtitle, legend, children }: {
  icon: string; number: string; name: string; title: string; subtitle: string;
  legend: { label: string; color: string }[]; children: ReactNode;
}) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex flex-col justify-between gap-space-md bg-surface-container-low p-space-lg lg:flex-row lg:items-center">
        <div className="flex items-start gap-space-md">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-card">
            <Icon name={icon} className="text-[26px]" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <AlgoTag>Algorithme {number}</AlgoTag>
              <span className="rounded bg-surface-container-high px-2 py-0.5 text-label-sm text-on-surface-variant">{name}</span>
            </div>
            <h2 className="mt-1 text-headline-sm font-bold text-on-surface">{title}</h2>
            <p className="text-body-md text-on-surface-variant">{subtitle}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 rounded-lg bg-surface-container-lowest px-3 py-2 shadow-card">
          {legend.map((l) => (
            <span key={l.label} className="flex items-center gap-1.5 text-label-sm text-on-surface">
              <span className="h-3 w-3 rounded-sm" style={{ background: l.color }} /> {l.label}
            </span>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-space-lg p-space-lg">{children}</div>
    </Card>
  );
}

const th = "px-space-sm py-2.5 text-label-sm uppercase";
const td = "px-space-sm py-2.5";

export function BenchmarkPage() {
  const { user } = useAuth();
  const projects = useAsync(() => api.projects(), []);
  // undefined = pas encore choisi ; null = instances aléatoires seulement.
  const [projectId, setProjectId] = useState<number | null | undefined>(undefined);
  const [bench, setBench] = useState<Benchmark | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Projet par défaut : le premier de la liste (choisi AVANT la première mesure).
  useEffect(() => {
    if (projects.data && projectId === undefined) setProjectId(projects.data[0]?.id ?? null);
  }, [projects.data, projectId]);

  async function run(pid: number | null) {
    setLoading(true);
    setError(null);
    try {
      setBench(await api.benchmark(pid));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (projectId !== undefined) void run(projectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function exportJson() {
    if (!bench) return;
    const blob = new Blob([JSON.stringify(bench, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "smartbricks_benchmark.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (user && user.role !== "ADMIN") {
    return (
      <AppShell crumbs={[{ label: "Comparaison des méthodes" }]}>
        <ErrorBanner message="Cet écran est réservé à l'administrateur." />
      </AppShell>
    );
  }

  const b = bench;
  const k = b?.knapsack.project;
  const c = b?.csp.project;
  const t = b?.tsp.project ?? b?.tsp.national;
  const gaps = b ? b.knapsack.random.map((s) => s.swaps_gap_avg_pct) : [];
  const avgGap = gaps.length ? gaps.reduce((s, x) => s + x, 0) / gaps.length : 0;
  const instances = b
    ? b.knapsack.random.reduce((s, x) => s + x.instances, 0) + b.csp.random.reduce((s, x) => s + x.instances, 0) + b.tsp.random.reduce((s, x) => s + x.instances, 0)
    : 0;

  return (
    <AppShell crumbs={[{ label: "Administration" }, { label: "Comparaison des méthodes" }]}>
      <div className="flex flex-col gap-space-lg">
        <StepHeader
          step="Administration · benchmark"
          title="Comparaison des méthodes"
          subtitle="Méthodes exactes contre méthodes approchées, mesurées sur le projet choisi et sur des instances aléatoires reproductibles."
          actions={
            <>
              <select
                value={projectId ?? ""}
                onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
                className="max-w-xs rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md"
                aria-label="Projet mesuré"
              >
                <option value="">Instances aléatoires seulement</option>
                {(projects.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
              <Button variant="secondary" icon="download" onClick={exportJson} disabled={!b}>Exporter (JSON)</Button>
              <Button icon="refresh" onClick={() => void run(projectId ?? null)} disabled={loading}>
                {loading ? "Mesure en cours…" : "Relancer le benchmark"}
              </Button>
            </>
          }
        />

        {error && <ErrorBanner message={error} />}
        {loading && !b && <Spinner label="Mesure des méthodes (quelques secondes)…" />}

        {b && (
          <div className={cx("flex flex-col gap-space-xl", loading && "opacity-60")}>
            {/* Synthèse */}
            <section className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-4">
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Instance du projet</span>
                <span className="mt-1 truncate text-title-md font-bold text-on-surface">{b.project?.title ?? "Aucune"}</span>
                <span className="text-body-sm text-on-surface-variant">
                  {c ? `${c.tasks} tâches · ${c.team} freelances` : "Planning non mesuré"} · {t?.cities.length ?? 0} villes
                </span>
              </Card>
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Instances mesurées</span>
                <span className="text-financial-display text-on-surface">{instances}</span>
                <span className="text-body-sm text-on-surface-variant">aléatoires, graine {b.seed} (reproductibles)</span>
              </Card>
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Écart moyen glouton + échanges</span>
                <span className="text-financial-display text-on-surface">{pct(avgGap)}</span>
                <span className="text-body-sm text-on-surface-variant">sac à dos, 10 à 40 fonctionnalités</span>
              </Card>
              <Card className="flex flex-col p-space-md">
                <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Durée totale du benchmark</span>
                <span className="text-financial-display text-on-surface">{ms(b.total_ms)}</span>
                <span className="text-body-sm text-on-surface-variant">dont {ms(c?.optimized.time_ms ?? 0)} pour l'optimisation du planning</span>
              </Card>
            </section>

            {/* Sac à dos */}
            <AlgoSection
              icon="inventory_2" number="n°29" name="Sac à dos multidimensionnel"
              title="Sélection du périmètre du sprint"
              subtitle={`Exact : ${b.knapsack.exact_method} · approché : ${b.knapsack.approx_methods.join(", ")} · ${b.knapsack.threshold}`}
              legend={[{ label: "Exact", color: C_EXACT }, { label: "Glouton", color: C_A1 }, { label: "Glouton + échanges", color: C_A2 }]}
            >
              {k && (
                <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
                  <div className="overflow-x-auto lg:col-span-7">
                    <table className="w-full text-left text-body-md">
                      <thead className="bg-surface-container-low text-on-surface-variant">
                        <tr><th className={th}>Projet</th><th className={th} style={{ color: C_EXACT }}>Exact</th><th className={th}>Glouton</th><th className={th}>+ échanges</th></tr>
                      </thead>
                      <tbody className="divide-y divide-surface-container-high">
                        <tr><td className={td}>Valeur métier</td><td className={cx(td, "font-bold text-primary")}>{k.exact.value}</td><td className={td}>{k.greedy.value}</td><td className={td}>{k.swaps.value}</td></tr>
                        <tr><td className={td}>Coût</td><td className={td}>{formatAr(k.exact.cost_mga)}</td><td className={td}>{formatAr(k.greedy.cost_mga)}</td><td className={td}>{formatAr(k.swaps.cost_mga)}</td></tr>
                        <tr><td className={td}>Heures</td><td className={td}>{k.exact.hours} h</td><td className={td}>{k.greedy.hours} h</td><td className={td}>{k.swaps.hours} h</td></tr>
                        <tr><td className={td}>Temps</td><td className={td}>{ms(k.exact.time_ms)}</td><td className={td}>{ms(k.greedy.time_ms)}</td><td className={td}>{ms(k.swaps.time_ms)}</td></tr>
                        <tr><td className={td}>Nœuds explorés</td><td className={td}>{formatInt(k.exact.nodes)}</td><td className={td}>—</td><td className={td}>—</td></tr>
                        <tr><td className={td}>Écart</td><td className={td}><GapBadge gap={0} /></td><td className={td}><GapBadge gap={k.greedy.gap_pct ?? 0} /></td><td className={td}><GapBadge gap={k.swaps.gap_pct ?? 0} /></td></tr>
                      </tbody>
                    </table>
                    <p className="mt-2 text-body-sm text-on-surface-variant">Coûts actuels des fonctionnalités (recalculés avec les taux de l'équipe si elle est choisie).</p>
                  </div>
                  <div className="flex flex-col gap-space-sm rounded-xl bg-surface-container-low p-space-md lg:col-span-5">
                    <Bars title="Valeur métier obtenue" items={[
                      { label: "Exact", value: k.exact.value, display: String(k.exact.value), color: C_EXACT },
                      { label: "Glouton", value: k.greedy.value, display: String(k.greedy.value), color: C_A1 },
                      { label: "+ échanges", value: k.swaps.value, display: String(k.swaps.value), color: C_A2 },
                    ]} />
                    <Bars title="Temps de calcul moyen à 40 fonctionnalités (seuil)" items={(() => {
                      const s = b.knapsack.random.find((x) => x.n === 40);
                      return s ? [
                        { label: "Exact", value: s.exact_ms_avg, display: ms(s.exact_ms_avg), color: C_EXACT },
                        { label: "Glouton", value: s.greedy_ms_avg, display: ms(s.greedy_ms_avg), color: C_A1 },
                        { label: "+ échanges", value: s.swaps_ms_avg, display: ms(s.swaps_ms_avg), color: C_A2 },
                      ] : [];
                    })()} />
                  </div>
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-body-sm">
                  <thead className="bg-surface-container-low text-on-surface-variant">
                    <tr><th className={th}>Fonctionnalités</th><th className={th}>Instances</th><th className={th}>Exact (moy. / max)</th><th className={th}>Nœuds max</th><th className={th}>Glouton : écart moy. / max</th><th className={th}>+ échanges : écart moy. / max</th><th className={th}>Glouton optimal</th></tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-high">
                    {b.knapsack.random.map((s) => (
                      <tr key={s.n}>
                        <td className={cx(td, "font-bold")}>{s.n}</td>
                        <td className={td}>{s.instances}</td>
                        <td className={td}>{ms(s.exact_ms_avg)} / {ms(s.exact_ms_max)}</td>
                        <td className={td}>{formatInt(s.nodes_max)}</td>
                        <td className={td}>{pct(s.greedy_gap_avg_pct)} / {pct(s.greedy_gap_max_pct)}</td>
                        <td className={td}>{pct(s.swaps_gap_avg_pct)} / {pct(s.swaps_gap_max_pct)}</td>
                        <td className={td}>{s.greedy_optimal_count}/{s.instances}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AlgoSection>

            {/* Planning */}
            <AlgoSection
              icon="calendar_month" number="n°3" name="Satisfaction de contraintes (CSP)"
              title="Planning et ordonnancement"
              subtitle={`Exact : ${b.csp.exact_method} · approché : ${b.csp.approx_methods.join(", ")}`}
              legend={[{ label: "Optimisé", color: C_EXACT }, { label: "Première solution", color: C_A1 }]}
            >
              {b.csp.note && <p className="text-body-md text-on-surface-variant">{b.csp.note}</p>}
              {c && (
                <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
                  <div className="overflow-x-auto lg:col-span-7">
                    <table className="w-full text-left text-body-md">
                      <thead className="bg-surface-container-low text-on-surface-variant">
                        <tr><th className={th}>Projet</th><th className={th} style={{ color: C_EXACT }}>Optimisé</th><th className={th}>Première solution</th></tr>
                      </thead>
                      <tbody className="divide-y divide-surface-container-high">
                        <tr><td className={td}>Durée</td><td className={cx(td, "font-bold text-primary")}>{c.optimized.makespan_days} j ouvrés</td><td className={td}>{c.first.makespan_days} j ouvrés</td></tr>
                        <tr><td className={td}>Borne du chemin critique</td><td className={td} colSpan={2}>{c.lower_bound_days} j ouvrés</td></tr>
                        <tr><td className={td}>Temps</td><td className={td}>{ms(c.optimized.time_ms)}</td><td className={td}>{ms(c.first.time_ms)}</td></tr>
                        <tr><td className={td}>Nœuds explorés</td><td className={td}>{formatInt(c.optimized.nodes)}</td><td className={td}>{formatInt(c.first.nodes)}</td></tr>
                        <tr><td className={td}>Optimalité</td><td className={td}>{c.optimized.optimal ? "Prouvée" : "Limite de temps atteinte"}</td><td className={td}><GapBadge gap={c.gap_pct} /></td></tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="rounded-xl bg-surface-container-low p-space-md lg:col-span-5">
                    <Bars title="Temps de calcul sur le projet" items={[
                      { label: "Optimisé", value: c.optimized.time_ms, display: ms(c.optimized.time_ms), color: C_EXACT },
                      { label: "1re solution", value: c.first.time_ms, display: ms(c.first.time_ms), color: C_A1 },
                    ]} />
                    <p className="mt-2 text-body-sm text-on-surface-variant">
                      L'essentiel du temps de l'optimisation sert à <strong>prouver</strong> qu'aucun planning plus court n'existe.
                    </p>
                  </div>
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-body-sm">
                  <thead className="bg-surface-container-low text-on-surface-variant">
                    <tr><th className={th}>Tâches</th><th className={th}>Instances</th><th className={th}>1re solution (moy.)</th><th className={th}>Optimisé (moy.)</th><th className={th}>Écart 1re solution : moy. / max</th><th className={th}>Optimum prouvé</th></tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-high">
                    {b.csp.random.map((s) => (
                      <tr key={s.n}>
                        <td className={cx(td, "font-bold")}>{s.n}</td>
                        <td className={td}>{s.instances}</td>
                        <td className={td}>{ms(s.first_ms_avg)}</td>
                        <td className={td}>{ms(s.optimized_ms_avg)}</td>
                        <td className={td}>{pct(s.gap_avg_pct)} / {pct(s.gap_max_pct)}</td>
                        <td className={td}>{s.optimal_count}/{s.instances}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AlgoSection>

            {/* Tournée */}
            <AlgoSection
              icon="route" number="n°30" name="Voyageur de commerce"
              title="Tournée des interventions sur site"
              subtitle={`Exact : ${b.tsp.exact_method} · approché : ${b.tsp.approx_methods.join(", ")} · ${b.tsp.threshold}`}
              legend={[{ label: "Held-Karp", color: C_EXACT }, { label: "Plus proche voisin", color: C_A1 }, { label: "+ 2-opt", color: C_A2 }]}
            >
              <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
                <div className="flex flex-col gap-space-md overflow-x-auto lg:col-span-7">
                  {[{ label: "Projet", run: b.tsp.project }, { label: "Les 12 villes de la base", run: b.tsp.national }]
                    .filter((x) => x.run)
                    .map(({ label, run }) => (
                      <table key={label} className="w-full text-left text-body-md">
                        <thead className="bg-surface-container-low text-on-surface-variant">
                          <tr><th className={th}>{label} ({run!.cities.length} villes)</th><th className={th} style={{ color: C_EXACT }}>Held-Karp</th><th className={th}>Plus proche voisin</th><th className={th}>+ 2-opt</th></tr>
                        </thead>
                        <tbody className="divide-y divide-surface-container-high">
                          <tr><td className={td}>Distance</td><td className={cx(td, "font-bold text-primary")}>{formatInt(run!.held_karp.km)} km</td><td className={td}>{formatInt(run!.nearest_neighbor.km)} km</td><td className={td}>{formatInt(run!.two_opt.km)} km</td></tr>
                          <tr><td className={td}>Temps</td><td className={td}>{ms(run!.held_karp.time_ms)}</td><td className={td}>{ms(run!.nearest_neighbor.time_ms)}</td><td className={td}>{ms(run!.two_opt.time_ms)}</td></tr>
                          <tr><td className={td}>Écart</td><td className={td}><GapBadge gap={0} /></td><td className={td}><GapBadge gap={run!.nearest_neighbor.gap_pct} /></td><td className={td}><GapBadge gap={run!.two_opt.gap_pct} /></td></tr>
                        </tbody>
                      </table>
                    ))}
                </div>
                <div className="rounded-xl bg-surface-container-low p-space-md lg:col-span-5">
                  <Bars
                    title="Temps de Held-Karp selon le nombre de sites (O(n² · 2ⁿ))"
                    items={b.tsp.random.map((s) => ({ label: `${s.sites} sites`, value: s.held_karp_ms_avg, display: ms(s.held_karp_ms_avg), color: s.sites > 12 ? C_A1 : C_EXACT }))}
                  />
                  <p className="mt-2 text-body-sm text-on-surface-variant">
                    Chaque site supplémentaire multiplie environ par 2,5 le temps de calcul : au-delà de 12 sites, le sélecteur passe à 2-opt.
                  </p>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-body-sm">
                  <thead className="bg-surface-container-low text-on-surface-variant">
                    <tr><th className={th}>Sites</th><th className={th}>Instances</th><th className={th}>Held-Karp (moy.)</th><th className={th}>2-opt (moy.)</th><th className={th}>Écart plus proche voisin</th><th className={th}>Écart 2-opt : moy. / max</th></tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-high">
                    {b.tsp.random.map((s) => (
                      <tr key={s.sites}>
                        <td className={cx(td, "font-bold")}>{s.sites}</td>
                        <td className={td}>{s.instances}</td>
                        <td className={td}>{ms(s.held_karp_ms_avg)}</td>
                        <td className={td}>{ms(s.two_opt_ms_avg)}</td>
                        <td className={td}>{pct(s.nn_gap_avg_pct)}</td>
                        <td className={td}>{pct(s.two_opt_gap_avg_pct)} / {pct(s.two_opt_gap_max_pct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AlgoSection>

            {/* Matrice de décision */}
            <Card className="flex flex-col gap-space-md p-space-lg">
              <div className="flex items-center gap-2">
                <Icon name="balance" className="text-primary" />
                <h3 className="text-headline-sm font-bold text-on-surface">Règles du sélecteur de méthode</h3>
                <AlgoTag>n°{b.selector.course_number}</AlgoTag>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-body-md">
                  <thead className="bg-surface-container-low text-label-sm uppercase text-on-surface-variant">
                    <tr><th className={th}>Problème</th><th className={th}>Méthode exacte</th><th className={th}>Méthode approchée</th><th className={th}>Seuil</th></tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-high">
                    {b.selector.rules.map((r) => (
                      <tr key={r.problem}>
                        <td className={cx(td, "font-bold")}>{r.problem}</td>
                        <td className={cx(td, "text-primary")}>{r.exact}</td>
                        <td className={td}>{r.approx}</td>
                        <td className={td}>{r.threshold}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="flex items-start gap-2 rounded-lg bg-surface-container-low p-space-sm text-body-sm text-on-surface-variant">
                <Icon name="info" className="text-[16px] text-primary" />
                Mesures faites à l'instant sur ce serveur (Python), avec des instances aléatoires reproductibles : relancer donne les
                mêmes valeurs et des temps proches.
              </p>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
