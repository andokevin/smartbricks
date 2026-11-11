/** Tableau de bord : les projets du client et leur avancement dans le parcours.
 *
 * Tous les chiffres viennent de l'API (GET /projects, GET /health) : rien n'est saisi en dur.
 */
import { useState } from "react";

import { api } from "../api/client";
import type { Health, ProjectSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { BrickProgress, ButtonLink, Card, ErrorBanner, Icon, Spinner, StatusBadge, Button, cx } from "../components/ui";
import { firstName, formatAr, formatDate, formatInt } from "../lib/format";
import { nextStep, STEPS, stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

const PROVIDER_LABEL: Record<Health["llm_provider"], string> = {
  mock: "Simulé",
  claude: "Claude",
  gemini: "Gemini",
};

function Kpi({ label, value, hint, icon, tone = "primary" }: {
  label: string;
  value: string;
  hint?: string;
  icon: string;
  tone?: "primary" | "secondary";
}) {
  return (
    <Card className="flex items-center justify-between gap-space-md p-space-md">
      <div className="flex min-w-0 flex-col">
        <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">{label}</span>
        <span className="mt-0.5 truncate text-financial-display text-on-surface">{value}</span>
        {hint && <span className="mt-0.5 truncate text-body-sm text-on-surface-variant">{hint}</span>}
      </div>
      <span
        className={cx(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-surface-container-low",
          tone === "primary" ? "text-primary" : "text-secondary",
        )}
      >
        <Icon name={icon} className="text-[22px]" />
      </span>
    </Card>
  );
}

function ProjectCard({ project }: { project: ProjectSummary }) {
  const next = nextStep(project.status);
  const stepIndex = STEPS.findIndex((s) => s.key === next.key);
  return (
    <Card className="flex flex-col gap-space-md p-space-lg transition-shadow hover:shadow-active hover:ring-1 hover:ring-primary-container">
      <div className="flex items-start justify-between gap-space-sm">
        <div className="flex min-w-0 items-start gap-space-sm">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-container text-on-primary">
            <Icon name="storefront" />
          </span>
          <div className="min-w-0">
            <h3 className="text-title-md font-bold text-on-surface">{project.title}</h3>
            <span className="text-body-sm text-on-surface-variant">
              Projet n°{project.id}
              {project.base_city ? ` · ${project.base_city}` : ""}
            </span>
          </div>
        </div>
        <StatusBadge status={project.status} />
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-label-sm text-on-surface-variant">
          <span>
            Étape {stepIndex + 1}/6 : {next.label}
          </span>
          <span>Algorithme {next.algorithm}</span>
        </div>
        <BrickProgress status={project.status} />
      </div>

      <dl className="grid grid-cols-2 gap-space-sm">
        <div className="rounded-lg bg-surface-container-low p-space-sm">
          <dt className="text-label-sm text-on-surface-variant">Budget</dt>
          <dd className="text-title-md font-bold text-primary">{formatAr(project.budget_mga)}</dd>
        </div>
        <div className="rounded-lg bg-surface-container-low p-space-sm">
          <dt className="text-label-sm text-on-surface-variant">Heures du sprint 1</dt>
          <dd className="text-title-md font-bold text-on-surface">{formatInt(project.budget_hours)} h</dd>
        </div>
        <div className="rounded-lg bg-surface-container-low p-space-sm">
          <dt className="text-label-sm text-on-surface-variant">Début</dt>
          <dd className="text-label-md text-on-surface">{formatDate(project.start_date)}</dd>
        </div>
        <div className="rounded-lg bg-surface-container-low p-space-sm">
          <dt className="text-label-sm text-on-surface-variant">Date limite</dt>
          <dd className="text-label-md text-on-surface">{formatDate(project.target_deadline)}</dd>
        </div>
      </dl>

      <ButtonLink to={stepPath(project.id, next.key)} iconRight="arrow_forward" className="self-stretch sm:self-end">
        Continuer : {next.label}
      </ButtonLink>
    </Card>
  );
}

export function DashboardPage() {
  const { user, logout } = useAuth();
  const projects = useAsync(() => api.projects(), []);
  const health = useAsync(() => api.health(), []);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const list = projects.data ?? [];
  const planned = list.filter((p) => p.status === "PLANNED").length;
  const totalBudget = list.reduce((sum, p) => sum + p.budget_mga, 0);

  async function resetDemo() {
    if (!window.confirm("Remettre la base de démonstration à zéro ? Les projets créés seront supprimés.")) return;
    setResetting(true);
    setResetError(null);
    try {
      await api.resetDemo();
      logout(); // les comptes sont recréés : on se reconnecte proprement
    } catch (e) {
      setResetError(e instanceof Error ? e.message : String(e));
      setResetting(false);
    }
  }

  return (
    <AppShell crumbs={[{ label: "Tableau de bord" }]}>
      <div className="flex flex-col gap-space-lg">
        <section className="flex flex-col justify-between gap-space-md md:flex-row md:items-end">
          <div>
            <h2 className="text-headline-lg-mobile tracking-tight text-on-surface md:text-headline-lg">
              Bonjour {user ? firstName(user.name) : ""}
            </h2>
            <p className="mt-1 max-w-2xl text-body-md text-on-surface-variant">
              Suivez vos projets brique par brique : copilote, périmètre, équipe, planning, tournée et synthèse.
            </p>
          </div>
          <ButtonLink to="/copilote" icon="auto_awesome">
            Décrire un nouveau projet
          </ButtonLink>
        </section>

        {projects.error && <ErrorBanner message={projects.error} onRetry={projects.reload} />}

        <section className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
          <Kpi label="Projets" value={formatInt(list.length)} hint={`${planned} planifié(s)`} icon="folder_open" />
          <Kpi label="Budget total déclaré" value={formatAr(totalBudget)} hint="Somme des budgets saisis" icon="payments" />
          <Kpi
            label="Étapes franchies"
            value={list.length ? `${formatInt(list.reduce((s, p) => s + STEPS.findIndex((x) => x.key === nextStep(p.status).key), 0))}` : "0"}
            hint={`sur ${list.length * 6} au total`}
            icon="view_in_ar"
            tone="secondary"
          />
          <Kpi
            label="Copilote"
            value={health.data ? PROVIDER_LABEL[health.data.llm_provider] : "…"}
            hint={
              health.data?.llm_provider === "mock"
                ? "Démo sans clé ni réseau"
                : health.data?.database === "ok"
                  ? "API et base opérationnelles"
                  : undefined
            }
            icon="smart_toy"
            tone="secondary"
          />
        </section>

        <section className="grid grid-cols-1 items-start gap-space-lg xl:grid-cols-12">
          <div className="flex flex-col gap-space-md xl:col-span-8">
            <div className="flex items-center gap-space-sm">
              <h3 className="text-headline-sm text-on-surface">Mes projets</h3>
              <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-label-sm text-primary">{list.length}</span>
            </div>
            {projects.loading && <Spinner />}
            {!projects.loading && list.length === 0 && !projects.error && (
              <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
                <Icon name="construction" className="text-[40px] text-primary" />
                <p className="text-title-md text-on-surface">Aucun projet pour l'instant</p>
                <p className="max-w-md text-body-md text-on-surface-variant">
                  Décrivez votre besoin avec vos mots : le copilote pose quelques questions puis prépare un brouillon.
                </p>
                <ButtonLink to="/copilote" icon="auto_awesome">
                  Commencer avec le copilote
                </ButtonLink>
              </Card>
            )}
            <div className="grid grid-cols-1 gap-space-md 2xl:grid-cols-2">
              {list.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </div>
          </div>

          <aside className="flex flex-col gap-space-md xl:col-span-4">
            <Card className="flex flex-col gap-space-sm p-space-lg">
              <div className="flex items-center gap-space-sm">
                <Icon name="insights" className="text-primary" />
                <h3 className="text-title-md font-bold text-on-surface">Qui décide quoi ?</h3>
              </div>
              <p className="text-body-sm text-on-surface-variant">
                Le copilote comprend et explique ; chaque décision chiffrée est prise par un algorithme du cours, puis
                revérifiée.
              </p>
              <ol className="flex flex-col gap-1.5">
                {STEPS.map((s, i) => (
                  <li key={s.key} className="flex items-center justify-between rounded-lg bg-surface-container-low px-space-sm py-1.5">
                    <span className="flex items-center gap-space-sm text-body-md text-on-surface">
                      <Icon name={s.icon} className="text-[18px] text-primary" />
                      {i + 1}. {s.label}
                    </span>
                    <span className="text-label-sm text-on-surface-variant">{s.algorithm}</span>
                  </li>
                ))}
              </ol>
            </Card>

            {health.data && health.data.environment !== "production" && (
              <Card className="flex flex-col gap-space-sm p-space-lg">
                <div className="flex items-center gap-space-sm">
                  <Icon name="restart_alt" className="text-tertiary-container" />
                  <h3 className="text-title-md font-bold text-on-surface">Démonstration</h3>
                </div>
                <p className="text-body-sm text-on-surface-variant">
                  Recrée les 25 freelances, les 12 villes et le projet Boutique Soa (données reproductibles).
                </p>
                {resetError && <ErrorBanner message={resetError} />}
                <Button variant="outline" icon="restart_alt" disabled={resetting} onClick={() => void resetDemo()}>
                  {resetting ? "Réinitialisation…" : "Réinitialiser la démo"}
                </Button>
              </Card>
            )}
          </aside>
        </section>
      </div>
    </AppShell>
  );
}
