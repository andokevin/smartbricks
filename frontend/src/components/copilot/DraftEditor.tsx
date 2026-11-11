/** Brouillon extrait par le copilote, relu et corrigé par le client avant confirmation.
 *
 * Le client peut corriger : intitulé, budget, heures du sprint, date limite, ville de base,
 * et pour chaque fonctionnalité sa valeur métier, ses heures et son caractère obligatoire.
 * Corriger les heures d'une fonctionnalité met ses tâches à l'échelle (même règle que PATCH /features).
 * Le serveur revérifie tout le brouillon à la confirmation.
 */
import { useState } from "react";

import type { City, Draft, DraftFeature, ReqType } from "../../api/types";
import { formatAr, formatDate, formatInt } from "../../lib/format";
import { Button, cx, Icon } from "../ui";

export const REQ_TYPE_LABEL: Record<ReqType, string> = {
  FUNCTIONAL: "Fonctionnelle",
  TECHNICAL: "Technique",
  SECURITY: "Sécurité",
  COMPLIANCE: "Conformité",
};

const input =
  "w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-md " +
  "focus:outline-none focus:ring-2 focus:ring-primary-container/20 disabled:bg-surface-container-low";

function clampInt(value: string, min: number, max = Number.MAX_SAFE_INTEGER): number {
  const n = Math.round(Number(value));
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : min;
}

/** Nouvelles heures d'une fonctionnalité : on met ses tâches à l'échelle (au moins 1 h chacune). */
function scaleFeatureHours(draft: Draft, ref: string, hours: number): Draft {
  const own = draft.tasks.filter((t) => t.feature_ref === ref);
  const old = own.reduce((s, t) => s + t.estimated_hours, 0);
  if (!own.length || old <= 0) {
    return { ...draft, features: draft.features.map((f) => (f.ref === ref ? { ...f, estimated_hours: hours } : f)) };
  }
  const tasks = draft.tasks.map((t) =>
    t.feature_ref === ref ? { ...t, estimated_hours: Math.max(1, Math.ceil((t.estimated_hours * hours) / old)) } : t,
  );
  const total = tasks.filter((t) => t.feature_ref === ref).reduce((s, t) => s + t.estimated_hours, 0);
  return { ...draft, tasks, features: draft.features.map((f) => (f.ref === ref ? { ...f, estimated_hours: total } : f)) };
}

function FeatureBrick({
  feature,
  taskCount,
  readOnly,
  onChange,
  onHours,
}: {
  feature: DraftFeature;
  taskCount: number;
  readOnly: boolean;
  onChange: (patch: Partial<DraftFeature>) => void;
  onHours: (hours: number) => void;
}) {
  const [hours, setHours] = useState(String(feature.estimated_hours));
  return (
    <div className={cx("flex flex-col gap-2 rounded-xl p-3 transition-colors", feature.is_mandatory ? "bg-surface-container-low" : "bg-surface-container-low/60")}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className={cx("flex h-7 min-w-7 shrink-0 items-center justify-center rounded px-1 text-label-sm", feature.is_mandatory ? "bg-primary-container text-on-primary" : "bg-surface-container-highest text-on-surface-variant")}>
            {feature.ref}
          </span>
          <div className="min-w-0">
            <div className="truncate text-body-md font-bold text-on-surface" title={feature.title}>{feature.title}</div>
            <div className="text-body-sm text-on-surface-variant">
              {REQ_TYPE_LABEL[feature.req_type]} · {taskCount} tâche(s)
              {feature.depends_on.length > 0 && ` · après ${feature.depends_on.join(", ")}`}
            </div>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3">
        <label className="flex items-center gap-2 text-label-sm text-on-surface-variant">
          Valeur
          <input
            type="range"
            min={1}
            max={100}
            value={feature.business_value}
            disabled={readOnly}
            onChange={(e) => onChange({ business_value: clampInt(e.target.value, 1, 100) })}
            className="h-1.5 w-full cursor-pointer accent-primary"
            aria-label={`Valeur métier de ${feature.title}`}
          />
          <span className="w-7 text-right text-label-md text-primary">{feature.business_value}</span>
        </label>
        <label className="flex items-center gap-1 text-label-md text-on-surface">
          <input
            type="number"
            min={1}
            value={hours}
            disabled={readOnly}
            onChange={(e) => setHours(e.target.value)}
            onBlur={() => {
              const h = clampInt(hours, 1);
              onHours(h);
              setHours(String(h));
            }}
            className="w-16 rounded-md border border-outline-variant bg-surface-container-lowest px-1.5 py-1 text-right text-label-md focus:outline-none focus:ring-2 focus:ring-primary-container/20"
            aria-label={`Heures de ${feature.title}`}
          />
          h
        </label>
        <label className="inline-flex cursor-pointer items-center gap-1">
          <span className={cx("text-label-sm", feature.is_mandatory ? "text-secondary" : "text-outline")}>
            {feature.is_mandatory ? "Obligatoire" : "Optionnelle"}
          </span>
          <input
            type="checkbox"
            checked={feature.is_mandatory}
            disabled={readOnly}
            onChange={(e) => onChange({ is_mandatory: e.target.checked })}
            className="h-4 w-4 cursor-pointer rounded accent-primary"
          />
        </label>
      </div>
    </div>
  );
}

export function DraftEditor({
  draft,
  warnings,
  cities,
  readOnly = false,
  confirming = false,
  error,
  onChange,
  onConfirm,
}: {
  draft: Draft;
  warnings: string[];
  cities: City[];
  readOnly?: boolean;
  confirming?: boolean;
  error?: string | null;
  onChange?: (draft: Draft) => void;
  onConfirm?: () => void;
}) {
  const [showTasks, setShowTasks] = useState(false);
  const p = draft.project;
  const totalHours = draft.features.reduce((s, f) => s + f.estimated_hours, 0);
  const mandatory = draft.features.filter((f) => f.is_mandatory).length;
  const setProject = (patch: Partial<Draft["project"]>) => onChange?.({ ...draft, project: { ...p, ...patch } });

  return (
    <section className="flex flex-col gap-5 rounded-xl bg-surface-container-lowest p-space-md shadow-card sm:p-space-lg">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon name="draw" />
        </span>
        <div>
          <h3 className="text-title-md font-bold text-on-surface">Brouillon du projet</h3>
          <span className="flex items-center gap-1 text-label-sm text-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-secondary" />
            {readOnly ? "Confirmé" : "Extrait et vérifié · modifiable"}
          </span>
        </div>
      </div>

      {/* Projet */}
      <div className="flex flex-col gap-3 rounded-xl bg-surface-container-low p-space-md">
        <label className="flex flex-col gap-1 text-label-sm uppercase tracking-wider text-outline">
          Intitulé
          <input className={cx(input, "text-title-md font-bold normal-case tracking-normal")} value={p.title} disabled={readOnly} onChange={(e) => setProject({ title: e.target.value })} />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-label-sm text-on-surface-variant">
            Budget
            <span className="relative">
              <input type="number" min={0} step={100000} className={cx(input, "pr-9 font-bold text-primary")} value={p.budget_mga} disabled={readOnly} onChange={(e) => setProject({ budget_mga: clampInt(e.target.value, 0) })} />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-label-md text-on-surface-variant">Ar</span>
            </span>
          </label>
          <label className="flex flex-col gap-1 text-label-sm text-on-surface-variant">
            Heures max. du sprint 1
            <span className="relative">
              <input type="number" min={1} className={cx(input, "pr-7")} value={p.budget_hours ?? ""} placeholder="Calculé" disabled={readOnly} onChange={(e) => setProject({ budget_hours: e.target.value ? clampInt(e.target.value, 1) : null })} />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-label-md text-on-surface-variant">h</span>
            </span>
          </label>
          <label className="flex flex-col gap-1 text-label-sm text-on-surface-variant">
            Date limite
            <input type="date" className={input} value={p.deadline} disabled={readOnly} onChange={(e) => setProject({ deadline: e.target.value })} />
          </label>
          <label className="flex flex-col gap-1 text-label-sm text-on-surface-variant">
            Ville de base
            <select className={input} value={p.base_city ?? ""} disabled={readOnly} onChange={(e) => setProject({ base_city: e.target.value || null })}>
              <option value="">—</option>
              {p.base_city && !cities.some((c) => c.name === p.base_city) && <option value={p.base_city}>{p.base_city}</option>}
              {cities.map((c) => (
                <option key={c.id} value={c.name}>{c.name}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="text-body-sm text-on-surface-variant">
          {formatAr(p.budget_mga)} · échéance le {formatDate(p.deadline)}
          {p.budget_hours === null && " · heures calculées à la création (jours ouvrés × 6 h × 2 personnes)"}
        </p>
      </div>

      {/* Résumé chiffré du brouillon (sommes des estimations, aucun calcul d'optimisation) */}
      <dl className="grid grid-cols-3 gap-2">
        {[
          { label: "Fonctionnalités", value: formatInt(draft.features.length), hint: `${mandatory} obligatoire(s)` },
          { label: "Tâches", value: formatInt(draft.tasks.length), hint: `${draft.sites.length} site(s)` },
          { label: "Heures estimées", value: `${formatInt(totalHours)} h`, hint: "à corriger si besoin" },
        ].map((m) => (
          <div key={m.label} className="rounded-lg bg-surface-container-low p-2.5">
            <dt className="text-label-sm text-on-surface-variant">{m.label}</dt>
            <dd className="text-title-md font-bold text-on-surface">{m.value}</dd>
            <dd className="text-body-sm text-on-surface-variant">{m.hint}</dd>
          </div>
        ))}
      </dl>

      {warnings.length > 0 && (
        <div className="flex flex-col gap-1.5 rounded-xl bg-surface-container-high/50 p-3">
          <span className="flex items-center gap-1.5 text-label-md text-primary">
            <Icon name="verified" className="text-[18px]" />
            Corrections automatiques (sans IA)
          </span>
          <ul className="list-disc pl-5 text-body-sm text-on-surface-variant">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Fonctionnalités */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-title-md font-bold text-on-surface">
            <Icon name="layers" className="text-primary" />
            Briques identifiées ({draft.features.length})
          </span>
          {!readOnly && <span className="text-label-sm text-outline">Valeur, heures, obligatoire</span>}
        </div>
        {draft.features.map((f) => (
          <FeatureBrick
            key={`${f.ref}-${f.estimated_hours}`}
            feature={f}
            readOnly={readOnly}
            taskCount={draft.tasks.filter((t) => t.feature_ref === f.ref).length}
            onChange={(patch) => onChange?.({ ...draft, features: draft.features.map((x) => (x.ref === f.ref ? { ...x, ...patch } : x)) })}
            onHours={(h) => onChange?.(scaleFeatureHours(draft, f.ref, h))}
          />
        ))}
      </div>

      {/* Tâches (repliées) */}
      <div className="flex flex-col gap-2">
        <button onClick={() => setShowTasks((v) => !v)} className="flex items-center justify-between rounded-lg px-1 text-left text-title-md font-bold text-on-surface" aria-expanded={showTasks}>
          <span className="flex items-center gap-1.5">
            <Icon name="checklist" className="text-primary" />
            Tâches ({draft.tasks.length})
          </span>
          <Icon name={showTasks ? "expand_less" : "expand_more"} className="text-outline" />
        </button>
        {showTasks && (
          <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto rounded-lg bg-surface-container-low p-2">
            {draft.tasks.map((t) => (
              <li key={t.ref} className="flex items-center justify-between gap-2 rounded px-2 py-1 text-body-sm">
                <span className="min-w-0 truncate text-on-surface">
                  <span className="font-bold text-primary">{t.ref}</span> {t.title}
                  {t.depends_on.length > 0 && <span className="text-outline"> · après {t.depends_on.join(", ")}</span>}
                </span>
                <span className="shrink-0 text-on-surface-variant">
                  {t.required_skill} niv. {t.min_level} · {t.estimated_hours} h{t.on_site_city ? ` · ${t.on_site_city}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Sites */}
      <div className="flex flex-col gap-2">
        <span className="flex items-center gap-1.5 text-title-md font-bold text-on-surface">
          <Icon name="near_me" className="text-secondary" />
          Interventions sur site ({draft.sites.length} ville{draft.sites.length > 1 ? "s" : ""})
        </span>
        <div className="flex flex-wrap gap-2">
          {draft.sites.length === 0 && <span className="text-body-sm text-on-surface-variant">Aucune.</span>}
          {draft.sites.map((s) => (
            <span key={s} className="inline-flex items-center gap-1 rounded-lg bg-surface-container px-2.5 py-1 text-label-md text-on-surface">
              <Icon name={s === p.base_city ? "apartment" : "pin_drop"} className="text-[14px] text-secondary" />
              {s}
              {s === p.base_city && " (base)"}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-error-container p-3 text-body-sm text-on-error-container">
          <Icon name="error" className="text-[18px]" />
          {error}
        </div>
      )}

      {!readOnly && onConfirm && (
        <div className="flex flex-col gap-2">
          <Button onClick={onConfirm} disabled={confirming} iconRight="arrow_forward" className="w-full py-3.5 text-body-lg font-bold">
            {confirming ? "Création du projet…" : "Valider le brouillon et passer au Périmètre"}
          </Button>
          <span className="flex items-center justify-center gap-1 text-label-sm text-outline">
            <Icon name="lock" className="text-[14px]" />
            Le serveur revérifie tout le brouillon avant de créer le projet.
          </span>
        </div>
      )}
    </section>
  );
}
