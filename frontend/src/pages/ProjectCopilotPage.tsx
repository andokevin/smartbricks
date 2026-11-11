/** Étape 1 d'un projet existant : la conversation qui l'a créé et le brouillon confirmé (lecture seule).
 * Pour le projet issu des données de démonstration (pas de conversation), on affiche son contenu. */
import { useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { Conversation, Draft, Project } from "../api/types";
import { AppShell } from "../components/AppShell";
import { ChatPanel } from "../components/copilot/ChatPanel";
import { DraftEditor } from "../components/copilot/DraftEditor";
import { ButtonLink, Card, ErrorBanner, Icon, Spinner } from "../components/ui";
import { stepPath } from "../lib/steps";
import { useAsync } from "../lib/useAsync";

/** Projet enregistré → même forme qu'un brouillon, pour réutiliser l'affichage. */
function projectAsDraft(p: Project): Draft {
  return {
    project: {
      title: p.title,
      description: p.description ?? "",
      budget_mga: p.budget_mga,
      budget_hours: p.budget_hours,
      deadline: p.target_deadline,
      base_city: p.base_city,
    },
    features: p.features.map((f) => ({
      ref: f.ref,
      title: f.title,
      description: f.description ?? "",
      req_type: f.req_type as Draft["features"][number]["req_type"],
      business_value: f.business_value,
      estimated_hours: f.estimated_hours,
      is_mandatory: f.is_mandatory,
      depends_on: f.depends_on,
    })),
    tasks: p.tasks.map((t) => ({
      ref: t.ref,
      feature_ref: t.feature_ref,
      title: t.title,
      required_skill: t.required_skill,
      min_level: t.min_level,
      estimated_hours: t.estimated_hours,
      depends_on: t.depends_on,
      on_site_city: t.on_site_city,
    })),
    sites: p.sites,
  };
}

export function ProjectCopilotPage() {
  const projectId = Number(useParams().projectId);
  const data = useAsync(async () => {
    const project = await api.project(projectId);
    let conversation: Conversation | null = null;
    try {
      conversation = await api.projectConversation(projectId);
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e;
    }
    return { project, conversation };
  }, [projectId]);

  const project = data.data?.project;
  const conversation = data.data?.conversation ?? null;

  return (
    <AppShell project={project} crumbs={[{ label: "Projets", to: "/" }, { label: project?.title ?? "…" }, { label: "Copilote" }]}>
      {data.error && <ErrorBanner message={data.error} onRetry={data.reload} />}
      {data.loading && <Spinner />}
      {project && (
        <div className="flex flex-col gap-space-lg">
          <div className="flex flex-col justify-between gap-space-md md:flex-row md:items-end">
            <div>
              <span className="text-label-md text-primary">Étape 1 : Copilote</span>
              <h2 className="text-headline-lg-mobile tracking-tight text-on-surface md:text-headline-lg">Le besoin exprimé</h2>
              <p className="mt-1 max-w-3xl text-body-md text-on-surface-variant">
                Ce que le client a décrit, et le brouillon qu'il a validé. Les chiffres du projet sont ensuite calculés
                par les algorithmes des étapes suivantes.
              </p>
            </div>
            <ButtonLink to={stepPath(project.id, "perimetre")} iconRight="arrow_forward">
              Voir le périmètre
            </ButtonLink>
          </div>

          <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
            <div className="lg:col-span-7">
              {conversation ? (
                <ChatPanel messages={conversation.messages} busy={false} provider={null} readOnly />
              ) : (
                <Card className="flex flex-col gap-3 p-space-lg">
                  <div className="flex items-center gap-2">
                    <Icon name="dataset" className="text-primary" />
                    <h3 className="text-title-md font-bold text-on-surface">Projet de démonstration</h3>
                  </div>
                  <p className="text-body-md text-on-surface-variant">
                    Ce projet a été créé directement par les données de démonstration, sans conversation. C'est
                    exactement le brouillon que le copilote simulé produit pour cette description :
                  </p>
                  <blockquote className="rounded-xl bg-surface-container-low p-space-md text-body-md text-on-surface">
                    {project.description}
                  </blockquote>
                  <ButtonLink to="/copilote" variant="secondary" icon="auto_awesome" className="self-start">
                    Refaire la conversation avec le copilote
                  </ButtonLink>
                </Card>
              )}
            </div>
            <div className="lg:col-span-5">
              <DraftEditor
                draft={conversation?.draft ?? projectAsDraft(project)}
                warnings={conversation?.warnings ?? []}
                cities={[]}
                readOnly
              />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
