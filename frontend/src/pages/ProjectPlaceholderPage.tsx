/** Écran provisoire des étapes pas encore construites (remplacé écran par écran en phase 6). */
import { useParams } from "react-router-dom";

import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { ButtonLink, Card, ErrorBanner, Icon, Spinner } from "../components/ui";
import { STEPS, type StepKey } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

export function ProjectPlaceholderPage({ step }: { step: StepKey }) {
  const projectId = Number(useParams().projectId);
  const project = useAsync(() => api.project(projectId), [projectId]);
  const meta = STEPS.find((s) => s.key === step);

  return (
    <AppShell
      project={project.data ?? undefined}
      crumbs={[{ label: "Projets", to: "/" }, { label: project.data?.title ?? "…" }, { label: meta?.label ?? step }]}
    >
      {project.error && <ErrorBanner message={project.error} onRetry={project.reload} />}
      {project.loading && <Spinner />}
      {project.data && (
        <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
          <Icon name={meta?.icon ?? "construction"} className="text-[40px] text-primary" />
          <p className="text-title-md text-on-surface">Écran « {meta?.label} » : en construction</p>
          <p className="text-body-md text-on-surface-variant">Il sera branché sur l'API dans la suite de la phase 6.</p>
          <ButtonLink to="/" variant="secondary" icon="arrow_back">
            Tableau de bord
          </ButtonLink>
        </Card>
      )}
    </AppShell>
  );
}

export function SimplePlaceholderPage({ title }: { title: string }) {
  return (
    <AppShell crumbs={[{ label: title }]}>
      <Card className="flex flex-col items-center gap-space-sm p-space-xl text-center">
        <Icon name="construction" className="text-[40px] text-primary" />
        <p className="text-title-md text-on-surface">« {title} » : en construction</p>
      </Card>
    </AppShell>
  );
}
