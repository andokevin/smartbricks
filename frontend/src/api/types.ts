/** Types des réponses de l'API (miroir de backend/app/schemas.py). */

export type Role = "CLIENT" | "FREELANCER" | "ADMIN";
export type ProjectStatus = "DRAFT" | "SCOPED" | "TEAM_SELECTED" | "PLANNED";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  organization_name: string | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Health {
  status: string;
  database: string;
  llm_provider: "mock" | "claude" | "gemini";
  environment: "development" | "production" | "test";
}

export interface ProjectSummary {
  id: number;
  title: string;
  status: ProjectStatus;
  budget_mga: number;
  budget_hours: number;
  start_date: string;
  target_deadline: string;
  base_city: string | null;
}

export interface Feature {
  id: number;
  ref: string;
  title: string;
  description: string | null;
  req_type: string;
  business_value: number;
  estimated_hours: number;
  estimated_cost_mga: number;
  is_mandatory: boolean;
  depends_on: string[];
  selected_for_sprint: boolean;
}

export interface Task {
  id: number;
  ref: string;
  feature_ref: string;
  title: string;
  required_skill: string;
  min_level: number;
  estimated_hours: number;
  depends_on: string[];
  on_site_city: string | null;
  status: string;
  assigned_freelancer_id: number | null;
  start_date: string | null;
  end_date: string | null;
}

export interface Project extends ProjectSummary {
  description: string | null;
  features: Feature[];
  tasks: Task[];
  sites: string[];
  team: number[];
}

export interface ResetDemoOut {
  demo_project_id: number;
  freelancers: number;
  features: number;
  tasks: number;
}
