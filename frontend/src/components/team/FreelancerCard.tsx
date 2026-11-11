/** Carte d'un freelance dans le classement pondéré (n°22), avec sa position de Pareto (n°21). */
import type { MatchingRow } from "../../api/types";
import { CRITERIA } from "../../lib/criteria";
import { formatAr, formatInt, formatPct } from "../../lib/format";
import { cx, Icon } from "../ui";

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function FreelancerCard({
  row,
  selected,
  suggested,
  onToggle,
  disabled,
}: {
  row: MatchingRow;
  selected: boolean;
  suggested: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  const c = row.criteria;
  return (
    <article
      className={cx(
        "flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-space-md shadow-card transition-shadow hover:shadow-active",
        selected && "ring-2 ring-primary-container",
      )}
    >
      <div className="flex items-start justify-between gap-space-md">
        <div className="flex min-w-0 items-center gap-space-md">
          <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-fixed text-title-md font-bold text-on-primary-fixed">
            {initials(row.name)}
            <span className="absolute -left-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-surface-container-lowest px-1 text-label-sm text-on-surface-variant shadow-card">
              {row.rank}
            </span>
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <h4 className="text-title-md font-bold text-on-surface">{row.name}</h4>
              {row.front === 1 && (
                <span className="rounded bg-primary-fixed px-1.5 py-0.5 text-label-sm text-on-primary-fixed" title="Personne ne fait mieux sur tous les critères à la fois">
                  Front de Pareto
                </span>
              )}
              {row.best_compromise && (
                <span className="inline-flex items-center gap-0.5 rounded bg-secondary-container px-1.5 py-0.5 text-label-sm text-on-secondary-container">
                  <Icon name="star" filled className="text-[14px]" /> Meilleur compromis
                </span>
              )}
              {suggested && (
                <span className="inline-flex items-center gap-0.5 rounded bg-tertiary-fixed px-1.5 py-0.5 text-label-sm text-on-tertiary-fixed">
                  <Icon name="auto_awesome" className="text-[14px]" /> Suggéré
                </span>
              )}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-body-sm text-on-surface-variant">
              <span className="flex items-center gap-1">
                <Icon name="location_on" className="text-[14px]" />
                {row.city}
              </span>
              <span>{row.hours_per_day} h/jour</span>
              <span>Front n°{row.front}</span>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end">
          <span className="flex items-baseline gap-0.5">
            <span className="text-headline-sm font-black text-primary">{Math.round(row.score * 100)}</span>
            <span className="text-label-sm text-on-surface-variant">/100</span>
          </span>
          <span className="text-title-md font-bold text-on-surface">{formatAr(row.hourly_rate_mga)}</span>
          <span className="text-label-sm text-outline">par heure</span>
        </div>
      </div>

      {/* Contribution de chaque critère au score : longueur totale = score */}
      <div className="flex flex-col gap-1.5 rounded-lg bg-surface-container-low p-space-sm" title="Contribution de chaque critère au score">
        <div className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full bg-surface-container-high" role="img" aria-label="Contributions au score">
          {CRITERIA.map((k) => {
            const w = row.contributions[k.key] * 100;
            return w > 0 ? <span key={k.key} className="h-full first:rounded-l-full" style={{ width: `${w}%`, background: k.color }} title={`${k.label} : ${w.toFixed(1)} points`} /> : null;
          })}
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-label-sm text-on-surface-variant">
          {CRITERIA.map((k) => (
            <span key={k.key} className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm" style={{ background: k.color }} />
              {k.label} {(row.contributions[k.key] * 100).toFixed(0)}
            </span>
          ))}
        </div>
      </div>

      {/* Valeurs brutes des critères */}
      <dl className="grid grid-cols-3 gap-x-3 gap-y-1 text-body-sm sm:grid-cols-5">
        <div><dt className="text-outline">Coût</dt><dd className="font-bold text-on-surface">{formatAr(c.cost)}</dd></div>
        <div><dt className="text-outline">Rapidité</dt><dd className="font-bold text-on-surface">{c.speed === null ? "—" : `${c.speed.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} j`}</dd></div>
        <div><dt className="text-outline">Qualité</dt><dd className="font-bold text-on-surface">{c.quality.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} / 5</dd></div>
        <div><dt className="text-outline">Disponibilité</dt><dd className="font-bold text-on-surface">{formatInt(c.availability)} j</dd></div>
        <div><dt className="text-outline">Couverture</dt><dd className="font-bold text-on-surface">{formatPct(c.coverage)}</dd></div>
      </dl>

      <div className="flex flex-wrap items-center gap-1.5">
        {Object.entries(row.skills).map(([s, lvl]) => (
          <span key={s} className="rounded-md bg-surface-container px-2 py-0.5 text-label-sm text-primary">
            {s} <span className="text-outline">niv. {lvl}</span>
          </span>
        ))}
      </div>

      <label className={cx("flex cursor-pointer select-none items-center gap-space-sm", disabled && "pointer-events-none opacity-60")}>
        <input type="checkbox" checked={selected} onChange={onToggle} className="h-4 w-4 cursor-pointer rounded accent-primary" />
        <span className={cx("text-body-md", selected ? "font-bold text-primary" : "text-on-surface-variant")}>
          {selected ? "Retenu dans l'équipe" : "Ajouter à l'équipe"}
        </span>
      </label>
    </article>
  );
}
