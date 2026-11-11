/** Les 6 étapes du parcours d'un projet, et leur état selon le statut du projet. */
import type { ProjectStatus } from "../api/types";

export type StepKey = "copilote" | "perimetre" | "equipe" | "planning" | "tournee" | "synthese";
export type StepState = "done" | "current" | "todo";

export interface Step {
  key: StepKey;
  label: string;
  icon: string;
  algorithm?: string; // numéro dans la liste du cours
}

export const STEPS: Step[] = [
  { key: "copilote", label: "Copilote", icon: "smart_toy", algorithm: "n°33" },
  { key: "perimetre", label: "Périmètre", icon: "grid_view", algorithm: "n°29" },
  { key: "equipe", label: "Équipe", icon: "groups", algorithm: "n°22 · n°21" },
  { key: "planning", label: "Planning", icon: "calendar_month", algorithm: "n°3" },
  { key: "tournee", label: "Tournée", icon: "route", algorithm: "n°30" },
  { key: "synthese", label: "Synthèse", icon: "fact_check", algorithm: "n°33" },
];

/** Nombre d'étapes terminées pour chaque statut du projet. */
const DONE_COUNT: Record<ProjectStatus, number> = {
  DRAFT: 1, // le copilote a produit le projet
  SCOPED: 2,
  TEAM_SELECTED: 3,
  PLANNED: 4,
};

export function stepState(status: ProjectStatus, index: number): StepState {
  const done = DONE_COUNT[status];
  if (index < done) return "done";
  if (index === done) return "current";
  return "todo";
}

export function nextStep(status: ProjectStatus): Step {
  return STEPS[Math.min(DONE_COUNT[status], STEPS.length - 1)] as Step;
}

export function stepPath(projectId: number, key: StepKey): string {
  return `/projets/${projectId}/${key}`;
}

export const STATUS_LABEL: Record<ProjectStatus, string> = {
  DRAFT: "Brouillon",
  SCOPED: "Cadré",
  TEAM_SELECTED: "Équipe choisie",
  PLANNED: "Planifié",
};
