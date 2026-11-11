/** Client HTTP de l'API SmartBricks.
 *
 * - Toutes les routes sont sous /api/v1 (Vite redirige vers FastAPI en développement).
 * - Le jeton JWT est gardé dans localStorage (dans un try/catch : le stockage peut être bloqué).
 * - Les erreurs de l'API ({"detail": "..."}) deviennent des ApiError avec le message en français.
 */
import type {
  ChatOut,
  City,
  ConfirmOut,
  Conversation,
  Draft,
  Feature,
  FeaturePatch,
  Health,
  Scope,
  Project,
  ProjectSummary,
  ResetDemoOut,
  TokenOut,
  User,
} from "./types";

const BASE = "/api/v1";
const TOKEN_KEY = "smartbricks_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* stockage indisponible : la session durera le temps de l'onglet */
  }
}

/** Transforme le corps d'erreur FastAPI en message lisible. */
function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Erreurs de validation Pydantic : [{loc, msg}, …]
      return detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join(" ; ");
    }
  }
  return `Erreur ${status}`;
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Serveur injoignable : vérifiez que l'API est lancée.");
  }
  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;
  if (!response.ok) {
    if (response.status === 401) setToken(null);
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data as T;
}

export const api = {
  health: () => request<Health>("GET", "/health"),
  login: (email: string, password: string) => request<TokenOut>("POST", "/auth/login", { email, password }),
  me: () => request<User>("GET", "/auth/me"),
  resetDemo: () => request<ResetDemoOut>("POST", "/admin/reset-demo"),
  projects: () => request<ProjectSummary[]>("GET", "/projects"),
  project: (id: number) => request<Project>("GET", `/projects/${id}`),
  cities: () => request<City[]>("GET", "/cities"),

  // Module A — copilote
  chat: (message: string, conversationId: number | null) =>
    request<ChatOut>("POST", "/assistant/chat", { message, conversation_id: conversationId }),
  confirm: (conversationId: number, draft: Draft) =>
    request<ConfirmOut>("POST", "/assistant/confirm", { conversation_id: conversationId, draft }),
  conversation: (id: number) => request<Conversation>("GET", `/assistant/conversations/${id}`),
  projectConversation: (projectId: number) =>
    request<Conversation>("GET", `/assistant/projects/${projectId}/conversation`),

  // Module B — sac à dos
  scope: (projectId: number) => request<Scope>("GET", `/projects/${projectId}/scope`),
  runScope: (projectId: number) => request<Scope>("POST", `/projects/${projectId}/scope`),
  patchFeature: (featureId: number, patch: FeaturePatch) =>
    request<Feature>("PATCH", `/features/${featureId}`, patch),
};
