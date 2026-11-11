/** Structure commune des écrans : barre latérale (ordinateur), tiroir et barre du bas (mobile), en-tête.
 *
 * Dans un projet, la barre latérale affiche les 6 étapes du parcours avec leur état
 * (fait / en cours / à venir), déduit du statut du projet renvoyé par l'API.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import type { ProjectSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { STEPS, stepPath, stepState, type StepState } from "../lib/steps";
import { cx, Icon, StatusBadge } from "./ui";

export interface Crumb {
  label: string;
  to?: string;
}

const STATE_BADGE: Record<StepState, { text: string; className: string }> = {
  done: { text: "Fait", className: "bg-secondary-container text-on-secondary-container" },
  current: { text: "En cours", className: "bg-primary-container text-on-primary" },
  todo: { text: "À venir", className: "text-outline" },
};

function Brand() {
  return (
    <Link to="/" className="flex h-16 items-center gap-space-sm px-space-lg">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-container text-on-primary shadow-card">
        <Icon name="view_in_ar" />
      </span>
      <span className="flex flex-col">
        <span className="text-title-md font-bold tracking-tight text-primary">SmartBricks</span>
        <span className="text-label-sm uppercase tracking-wider text-on-surface-variant">Cadrage agile</span>
      </span>
    </Link>
  );
}

function SideNav({ project, onNavigate }: { project?: ProjectSummary; onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const linkBase = "flex items-center justify-between rounded-lg px-space-md py-space-sm transition-colors";
  const active = "bg-surface-container text-primary font-bold shadow-[inset_3px_0_0_0_var(--color-primary)]";
  const idle = "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface";

  return (
    <div className="flex h-full flex-col justify-between">
      <div className="flex flex-col">
        <Brand />
        {user?.role === "FREELANCER" ? (
          <nav className="flex flex-col gap-space-xs px-space-sm">
            <NavLink to="/espace-freelance" onClick={onNavigate} className={({ isActive }) => cx(linkBase, isActive ? active : idle)}>
              <span className="flex items-center gap-space-sm">
                <Icon name="assignment_ind" />
                <span className="text-body-md">Mes tâches</span>
              </span>
            </NavLink>
          </nav>
        ) : (
          <nav className="flex flex-col gap-space-xs px-space-sm">
            <NavLink to="/" end onClick={onNavigate} className={({ isActive }) => cx(linkBase, isActive ? active : idle)}>
              <span className="flex items-center gap-space-sm">
                <Icon name="dashboard" />
                <span className="text-body-md">Tableau de bord</span>
              </span>
            </NavLink>
            <NavLink to="/copilote" onClick={onNavigate} className={({ isActive }) => cx(linkBase, isActive ? active : idle)}>
              <span className="flex items-center gap-space-sm">
                <Icon name="add_circle" />
                <span className="text-body-md">Nouveau projet</span>
              </span>
            </NavLink>
          </nav>
        )}

        {project && (
          <>
            <div className="px-space-lg pb-space-xs pt-space-lg text-label-sm uppercase tracking-wider text-outline">
              Parcours du projet
            </div>
            <nav className="flex flex-col gap-space-xs px-space-sm">
              {STEPS.map((step, i) => {
                const state = stepState(project.status, i);
                const badge = STATE_BADGE[state];
                return (
                  <NavLink
                    key={step.key}
                    to={stepPath(project.id, step.key)}
                    onClick={onNavigate}
                    className={({ isActive }) => cx(linkBase, isActive ? active : idle)}
                  >
                    <span className="flex items-center gap-space-sm">
                      <Icon
                        name={state === "done" ? "check_circle" : step.icon}
                        className={state === "done" ? "text-secondary" : state === "todo" ? "text-outline-variant" : "text-primary"}
                      />
                      <span className="text-body-md">
                        {i + 1}. {step.label}
                      </span>
                    </span>
                    <span className={cx("rounded px-1.5 py-0.5 text-label-sm", badge.className)}>{badge.text}</span>
                  </NavLink>
                );
              })}
            </nav>
          </>
        )}

        {user?.role === "ADMIN" && (
          <>
            <div className="px-space-lg pb-space-xs pt-space-lg text-label-sm uppercase tracking-wider text-outline">
              Administration
            </div>
            <nav className="flex flex-col gap-space-xs px-space-sm">
              <NavLink
                to="/admin/benchmark"
                onClick={onNavigate}
                className={({ isActive }) => cx(linkBase, isActive ? active : idle)}
              >
                <span className="flex items-center gap-space-sm">
                  <Icon name="science" />
                  <span className="text-body-md">Comparaison des méthodes</span>
                </span>
              </NavLink>
            </nav>
          </>
        )}
      </div>

      <div className="flex flex-col gap-space-sm p-space-sm">
        <div className="rounded-xl bg-surface-container-low p-space-md">
          <div className="mb-space-xs flex items-center gap-space-sm">
            <span className="flex gap-0.5">
              <span className="h-3 w-2 rounded-sm bg-primary" />
              <span className="h-3 w-2 rounded-sm bg-primary-container" />
              <span className="h-3 w-2 rounded-sm bg-secondary" />
            </span>
            <span className="text-label-md font-bold text-primary">Méthode Briques</span>
          </div>
          <p className="text-body-sm text-on-surface-variant">
            Le copilote dialogue et explique ; des algorithmes prouvés prennent les décisions chiffrées.
          </p>
        </div>
        {user && (
          <div className="flex items-center justify-between gap-2 px-space-sm py-space-xs">
            <div className="min-w-0">
              <div className="truncate text-label-md text-on-surface">{user.name}</div>
              <div className="truncate text-body-sm text-on-surface-variant">{user.organization_name ?? user.email}</div>
            </div>
            <button
              onClick={logout}
              className="flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant hover:bg-surface-container"
              title="Se déconnecter"
              aria-label="Se déconnecter"
            >
              <Icon name="logout" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function AppShell({
  project,
  crumbs = [],
  actions,
  children,
}: {
  project?: ProjectSummary;
  crumbs?: Crumb[];
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  useEffect(() => setDrawer(false), [location.pathname]);

  return (
    <div className="min-h-screen bg-surface">
      {/* Barre latérale fixe (ordinateur) */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 overflow-y-auto bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.04)] lg:block print:hidden">
        <SideNav project={project} />
      </aside>

      {/* Tiroir (tablette et mobile) */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <button className="absolute inset-0 bg-inverse-surface/40" aria-label="Fermer le menu" onClick={() => setDrawer(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 overflow-y-auto bg-surface-container-lowest shadow-overlay">
            <SideNav project={project} onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64 print:pl-0">
        {/* En-tête */}
        <header className="sticky top-0 z-30 flex h-16 items-center gap-space-sm bg-surface/85 px-4 shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl lg:px-space-lg print:hidden">
          <button
            className="flex h-11 w-11 items-center justify-center rounded-lg text-primary hover:bg-surface-container lg:hidden"
            onClick={() => setDrawer(true)}
            aria-label="Ouvrir le menu"
          >
            <Icon name="menu" className="text-[24px]" />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-space-sm">
            <nav aria-label="Fil d'Ariane" className="hidden items-center gap-space-xs text-label-md text-on-surface-variant md:flex">
              {crumbs.slice(0, -1).map((c) => (
                <span key={c.label} className="flex items-center gap-space-xs">
                  {c.to ? (
                    <Link to={c.to} className="hover:text-on-surface">
                      {c.label}
                    </Link>
                  ) : (
                    c.label
                  )}
                  <Icon name="chevron_right" className="text-[16px]" />
                </span>
              ))}
            </nav>
            <h1 className="truncate text-title-md font-bold tracking-tight text-on-surface">
              {crumbs.at(-1)?.label ?? "SmartBricks"}
            </h1>
            {project && (
              <span className="hidden sm:inline-flex">
                <StatusBadge status={project.status} />
              </span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-space-sm">
            {actions}
            <span className="hidden items-center rounded-lg bg-surface-container-low p-1 md:flex">
              <span className="rounded bg-surface-container-lowest px-space-sm py-0.5 text-label-md font-bold text-primary">Ar</span>
              <span className="px-space-sm py-0.5 text-label-md text-on-surface-variant">Ariary MGA</span>
            </span>
          </div>
        </header>

        <main className={cx("mx-auto w-full max-w-[1280px] px-4 py-space-lg lg:px-space-xl", project && "pb-28 lg:pb-space-lg")}>
          {children}
        </main>
      </div>

      {/* Barre du bas (mobile) : les étapes du projet */}
      {project && (
        <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface-container-lowest/95 backdrop-blur-xl lg:hidden print:hidden">
          <div className="flex h-16 items-stretch">
            {STEPS.map((step) => (
              <NavLink
                key={step.key}
                to={stepPath(project.id, step.key)}
                className={({ isActive }) =>
                  cx(
                    "flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 text-label-sm",
                    isActive ? "text-primary-container" : "text-on-surface-variant",
                  )
                }
              >
                <Icon name={step.icon} className="text-[22px]" />
                <span className="truncate">{step.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
