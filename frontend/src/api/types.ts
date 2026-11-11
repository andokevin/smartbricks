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

// ---------------------------------------------------------------- module A — copilote

export type ReqType = "FUNCTIONAL" | "TECHNICAL" | "SECURITY" | "COMPLIANCE";

export interface DraftProject {
  title: string;
  description: string;
  budget_mga: number;
  budget_hours: number | null;
  deadline: string;
  base_city: string | null;
}

export interface DraftFeature {
  ref: string;
  title: string;
  description: string;
  req_type: ReqType;
  business_value: number;
  estimated_hours: number;
  is_mandatory: boolean;
  depends_on: string[];
}

export interface DraftTask {
  ref: string;
  feature_ref: string;
  title: string;
  required_skill: string;
  min_level: number;
  estimated_hours: number;
  depends_on: string[];
  on_site_city: string | null;
}

export interface Draft {
  project: DraftProject;
  features: DraftFeature[];
  tasks: DraftTask[];
  sites: string[];
}

export interface ChatOut {
  conversation_id: number;
  reply: string;
  ready: boolean;
  draft: Draft | null;
  warnings: string[];
  provider: string;
  fallback_reason: string | null;
}

export interface ConfirmOut {
  project_id: number;
  title: string;
  features: number;
  tasks: number;
  sites: string[];
  warnings: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Conversation {
  id: number;
  status: "OPEN" | "DRAFT_READY" | "CONFIRMED";
  project_id: number | null;
  messages: ChatMessage[];
  draft: Draft | null;
  warnings: string[];
}

export interface City {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

// ---------------------------------------------------------------- module B — sac à dos

export interface MethodChoice {
  problem: string;
  method: string;
  exact: boolean;
  reason: string;
  course_number: number;
}

export interface ScopeFeature {
  id: number;
  ref: string;
  title: string;
  business_value: number;
  estimated_hours: number;
  estimated_cost_mga: number;
  is_mandatory: boolean;
  depends_on: string[];
  selected: boolean;
  reason: string | null;
}

export interface WhatIf {
  increase_pct: number;
  extra_budget_mga: number;
  new_budget_mga: number;
  added: string[];
  removed: string[];
  value_gain: number;
  message: string;
}

export interface Scope {
  feasible: boolean;
  message: string;
  method: MethodChoice;
  optimal: boolean;
  nodes: number;
  elapsed_ms: number;
  total_value: number;
  total_cost_mga: number;
  total_hours: number;
  budget_mga: number;
  budget_hours: number;
  budget_usage: number;
  hours_usage: number;
  missing_cost_mga: number;
  missing_hours: number;
  features: ScopeFeature[];
  what_if: WhatIf[];
  verification: string[];
}

export interface FeaturePatch {
  business_value?: number;
  estimated_hours?: number;
  is_mandatory?: boolean;
}

// ---------------------------------------------------------------- module C — matching

export type CriterionKey = "cost" | "speed" | "quality" | "availability" | "coverage";
export type Weights = Record<CriterionKey, number>;

export interface MatchingRow {
  rank: number;
  id: number;
  name: string;
  city: string;
  hourly_rate_mga: number;
  hours_per_day: number;
  skills: Record<string, number>;
  criteria: { cost: number; speed: number | null; quality: number; availability: number; coverage: number };
  normalized: Weights;
  contributions: Weights;
  score: number;
  front: number;
  best_compromise: boolean;
}

export interface TaskNeed {
  id: number;
  skill: string;
  min_level: number;
  hours: number;
}

export interface Matching {
  preset: string;
  weights: Weights;
  criteria_labels: Record<CriterionKey, string>;
  pareto_criteria: CriterionKey[];
  tasks_considered: number;
  total_hours: number;
  working_days: number;
  tasks: TaskNeed[];
  ranking: MatchingRow[];
  fronts: number[][];
  best_compromise: number | null;
  suggested_team: { members: number[]; absorbable: boolean; warnings: string[] };
}

export interface TeamMember {
  id: number;
  name: string;
  city: string;
  hourly_rate_mga: number;
  hours_per_day: number;
  skills: Record<string, number>;
}

export interface TeamOut {
  project_id: number;
  members: TeamMember[];
  warnings: string[];
  absorbable: boolean;
}

// ---------------------------------------------------------------- module D — planning CSP

export interface Assignment {
  task_id: number;
  ref: string;
  title: string;
  skill: string;
  hours: number;
  freelancer_id: number;
  freelancer: string;
  start: string;
  end: string;
  days: number;
  depends_on: string[];
  on_site_city: string | null;
}

export interface ConstraintCheck {
  name: string;
  passed: boolean;
  details: string[];
}

export interface Schedule {
  run_id: number;
  scenario: "normal" | "impossible" | "date de test";
  status: "OK" | "INFEASIBLE" | "UNKNOWN";
  start_date: string;
  deadline: string;
  working_days_available: number;
  makespan_days: number | null;
  end_date: string | null;
  lower_bound_days: number;
  critical_path: string[];
  optimal: boolean;
  nodes: number;
  elapsed_ms: number;
  method: MethodChoice;
  diagnostics: string[];
  verification: { constraints_passed: boolean; checks: ConstraintCheck[] } | null;
  assignments: Assignment[];
  team: { id: number; name: string; hours_per_day: number }[];
}

export interface FreelancerInfo {
  id: number;
  name: string;
  city: string;
  hourly_rate_mga: number;
  hours_per_day: number;
  skills: Record<string, number>;
  unavailability: { start: string; end: string; reason: string | null }[];
}

// ---------------------------------------------------------------- module E — tournée

export interface TourStop {
  step: number;
  name: string;
  latitude: number;
  longitude: number;
}

export interface Tour {
  saved: boolean;
  method: MethodChoice;
  technician: { id: number; name: string; city: string } | null;
  start: { name: string; reason: string };
  closed: boolean;
  order: TourStop[];
  legs: { from: string; to: string; km: number }[];
  distance_km: number;
  cost_mga: number;
  duration_h: number;
  cost_per_km: number;
  entered_order: string[];
  entered_distance_km: number;
  gain_km: number;
  gain_mga: number;
  message: string;
}

export interface TourOptions {
  freelancer_id: number | null;
  closed: boolean;
  cost_per_km: number;
}

export interface TourRun {
  id: number;
  method: string;
  order: string[];
  distance_km: number;
  cost_mga: number;
  technician: { id: number; name: string; city: string } | null;
  created_at: string;
}

// ---------------------------------------------------------------- module A — explication

export interface Explanation {
  text: string;
  provider: string;
  replaced: boolean;
  unknown_numbers: string[];
  fallback_reason: string | null;
}

// ---------------------------------------------------------------- benchmark

export interface KnapRun {
  method: string;
  feasible: boolean;
  value: number;
  cost_mga: number;
  hours: number;
  time_ms: number;
  nodes: number;
  optimal: boolean;
  selected: number;
  gap_pct?: number;
}

export interface Benchmark {
  seed: number;
  total_ms: number;
  project: { id: number; title: string } | null;
  knapsack: {
    course_number: number;
    exact_method: string;
    approx_methods: string[];
    threshold: string;
    project: { exact: KnapRun; greedy: KnapRun; swaps: KnapRun } | null;
    random: {
      n: number; instances: number; exact_ms_avg: number; exact_ms_max: number; nodes_max: number;
      greedy_ms_avg: number; swaps_ms_avg: number; greedy_gap_avg_pct: number; greedy_gap_max_pct: number;
      swaps_gap_avg_pct: number; swaps_gap_max_pct: number; greedy_optimal_count: number;
    }[];
  };
  csp: {
    course_number: number;
    exact_method: string;
    approx_methods: string[];
    threshold: string;
    note: string | null;
    project: {
      tasks: number; team: number; lower_bound_days: number; gap_pct: number;
      first: { makespan_days: number; time_ms: number; nodes: number };
      optimized: { makespan_days: number; time_ms: number; nodes: number; optimal: boolean };
    } | null;
    random: { n: number; instances: number; first_ms_avg: number; optimized_ms_avg: number; gap_avg_pct: number; gap_max_pct: number; optimal_count: number }[];
  };
  tsp: {
    course_number: number;
    exact_method: string;
    approx_methods: string[];
    threshold: string;
    project: TspRun | null;
    national: TspRun;
    random: { sites: number; instances: number; held_karp_ms_avg: number; two_opt_ms_avg: number; nn_gap_avg_pct: number; two_opt_gap_avg_pct: number; two_opt_gap_max_pct: number }[];
  };
  selector: { course_number: number; rules: { problem: string; exact: string; approx: string; threshold: string }[] };
}

export interface TspRun {
  cities: string[];
  held_karp: { km: number; time_ms: number };
  nearest_neighbor: { km: number; time_ms: number; gap_pct: number };
  two_opt: { km: number; time_ms: number; gap_pct: number };
}

export interface ResetDemoOut {
  demo_project_id: number;
  freelancers: number;
  features: number;
  tasks: number;
}
