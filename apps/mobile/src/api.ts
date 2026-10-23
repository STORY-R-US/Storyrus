import Constants from "expo-constants";
import type {
  Job,
  Project,
  ProjectAssets,
  StudioStep,
  Theme,
  UploadUrl,
  UserVoice,
  VoiceList,
} from "./types";

/**
 * API base: production BFF at https://storyrus.ai (same-origin /v1 proxy).
 * Local override (highest → lowest):
 *   1. EXPO_PUBLIC_API_BASE env (e.g. EXPO_PUBLIC_API_BASE=http://10.0.2.2:8000 npx expo start)
 *   2. expo.extra.apiBase in app.json
 */
const BASE: string =
  (typeof process !== "undefined" && process.env?.EXPO_PUBLIC_API_BASE) ||
  (Constants.expoConfig?.extra as { apiBase?: string } | undefined)?.apiBase ||
  "https://storyrus.ai";

function httpError(status: number, detail: string): Error & { status: number } {
  return Object.assign(new Error(`${status}: ${detail}`), { status });
}

export function isSessionRejected(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const value = error as { status?: number; message?: string };
  return value.status === 401 || value.status === 403 || /^(401|403):/.test(value.message ?? "");
}

type ClerkTokenGetter = (opts?: { skipCache?: boolean }) => Promise<string | null>;

let token: string | null = null;
let manualOverride = false;
let clerkGetToken: ClerkTokenGetter | null = null;
let clerkSignOut: (() => Promise<void>) | null = null;

export function setClerkGetToken(fn: ClerkTokenGetter | null) {
  clerkGetToken = fn;
}

export function setClerkSignOut(fn: (() => Promise<void>) | null) {
  clerkSignOut = fn;
}

export function getToken(): string | null {
  return token;
}

/** Testes gravam o Bearer aqui. A sessão real vem do Clerk. */
export function setToken(t: string | null) {
  token = t;
  manualOverride = Boolean(t);
}

export async function hydrateToken(): Promise<void> {
  if (manualOverride) return;
  if (!clerkGetToken) return;
  try {
    token = await clerkGetToken();
  } catch {
    /* mantém o último token se o Clerk não responder */
  }
}

/** Garante sessão de conta. O Clerk renova o token. */
export async function ensureSession(): Promise<void> {
  await hydrateToken();
  if (!token) throw httpError(401, "Nao autenticado");
}

/** @deprecated Use ensureSession. */
export async function ensureGuest(): Promise<void> {
  return ensureSession();
}

export function logout(): void {
  setToken(null);
  void clerkSignOut?.();
}

/** Clear session (studio "Sair"). */
export async function resetToGuest(): Promise<void> {
  logout();
}

function uuid(): string {
  // RFC4122 v4 simples (suficiente para Idempotency-Key).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Idempotency-Key estável por projeto+etapa enquanto a tentativa estiver viva. */
const stepIdempotencyKeys = new Map<string, string>();
const stepInFlight = new Map<string, Promise<unknown>>();

function stepCacheKey(projectId: string, step: string): string {
  return `${projectId}:${step}`;
}

function getOrCreateStepIdempotencyKey(projectId: string, step: string): string {
  const cacheKey = stepCacheKey(projectId, step);
  let key = stepIdempotencyKeys.get(cacheKey);
  if (!key) {
    key = uuid();
    stepIdempotencyKeys.set(cacheKey, key);
  }
  return key;
}

function releaseStepIdempotencyKey(projectId: string, step: string): void {
  stepIdempotencyKeys.delete(stepCacheKey(projectId, step));
}

function isHttpErrorMessage(message: string): boolean {
  return /^\d{3}:/.test(message);
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  await ensureSession();

  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (!(init.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(`${BASE}${path}`, { ...init, headers });
  if (resp.status === 401) setToken(null);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch {
      /* corpo vazio */
    }
    throw httpError(resp.status, String(detail));
  }
  return resp.status === 204 ? (undefined as T) : ((await resp.json()) as T);
}

export type ProfileUpdate = {
  full_name?: string;
  phone?: string;
  postal_code?: string;
  street?: string;
  number?: string;
  complement?: string | null;
  district?: string | null;
  city?: string;
  state?: string;
  country?: string;
  accept_terms?: boolean;
  confirm_adult?: boolean;
};

export type MeUser = {
  id: string;
  email: string;
  credits: number;
  is_guest: boolean;
  email_verified: boolean;
  full_name: string | null;
  phone: string | null;
  postal_code: string | null;
  street: string | null;
  number: string | null;
  complement: string | null;
  district: string | null;
  city: string | null;
  state: string | null;
  country?: string | null;
  terms_accepted_at?: string | null;
  adult_confirmed_at?: string | null;
};

export const api = {
  me: () => req<MeUser>("/v1/auth/me"),
  updateMe: (payload: ProfileUpdate) =>
    req<MeUser>("/v1/auth/me", { method: "PATCH", body: JSON.stringify(payload) }),
  credits: () => req<{ credits: number }>("/v1/credits"),
  createProject: (
    theme?: Theme,
    extraTheme?: Theme,
    childName?: string,
    dedication?: string,
    childAge?: number,
  ) =>
    req<Project>("/v1/projects", {
      method: "POST",
      body: JSON.stringify({
        style: "cgi_3d",
        theme,
        extra_theme: extraTheme || undefined,
        child_name: childName?.trim() || undefined,
        child_age: childAge ?? undefined,
        dedication: dedication?.trim() || undefined,
      }),
    }),
  getProject: (id: string) => req<Project>(`/v1/projects/${id}`),
  getAssets: (id: string) => req<ProjectAssets>(`/v1/projects/${id}/assets`),
  listJobs: (id: string) => req<Job[]>(`/v1/projects/${id}/jobs`),
  requestPhotoUpload: (id: string, contentType: string, ext: string) =>
    req<UploadUrl>(`/v1/projects/${id}/photos`, {
      method: "POST",
      body: JSON.stringify({ content_type: contentType, ext }),
    }),
  async uploadToSignedUrl(url: string, uri: string, contentType: string) {
    const blob = await (await fetch(uri)).blob();
    const response = await fetch(url, { method: "PUT", body: blob, headers: { "Content-Type": contentType } });
    if (!response.ok) throw httpError(response.status, "Não foi possível enviar a foto. Tente novamente.");
  },
  startStep(id: string, step: StudioStep, body: object = {}) {
    // Clique duplo / retry em voo: mesma promise + mesma Idempotency-Key.
    const cacheKey = stepCacheKey(id, step);
    const inFlight = stepInFlight.get(cacheKey);
    if (inFlight) {
      return inFlight as Promise<{ job_id: string; estimated_cost_credits: number }>;
    }

    const idempotencyKey = getOrCreateStepIdempotencyKey(id, step);
    const promise = (async () => {
      try {
        const accepted = await req<{ job_id: string; estimated_cost_credits: number }>(
          `/v1/projects/${id}/${step}`,
          {
            method: "POST",
            headers: { "Idempotency-Key": idempotencyKey },
            body: JSON.stringify(body),
          },
        );
        releaseStepIdempotencyKey(id, step);
        return accepted;
      } catch (err) {
        const message = err instanceof Error ? err.message : "";
        if (isHttpErrorMessage(message)) {
          releaseStepIdempotencyKey(id, step);
        }
        throw err;
      } finally {
        stepInFlight.delete(cacheKey);
      }
    })();

    stepInFlight.set(cacheKey, promise);
    return promise;
  },
  listVoices: () => req<VoiceList>("/v1/voices"),
  async uploadVoice(uri: string, name: string, mimeType: string, makeDefault = false) {
    await ensureSession();
    const ext = uri.split(".").pop()?.split("?")[0] || "m4a";
    const fd = new FormData();
    fd.append("file", {
      uri,
      name: `voice.${ext}`,
      type: mimeType || "audio/mp4",
    } as unknown as Blob);
    fd.append("name", name);
    fd.append("make_default", makeDefault ? "true" : "false");
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch(`${BASE}/v1/voices`, { method: "POST", body: fd, headers });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        detail = (await resp.json()).detail ?? detail;
      } catch {
        /* corpo vazio */
      }
      throw httpError(resp.status, String(detail));
    }
    return (await resp.json()) as UserVoice;
  },
  deleteVoice: (id: string) => req<void>(`/v1/voices/${id}`, { method: "DELETE" }),
  approveCharacter: (id: string) =>
    req<Project>(`/v1/projects/${id}/avatar/approve`, { method: "POST" }),
  approveBook: (id: string) =>
    req<Project>(`/v1/projects/${id}/book/approve`, { method: "POST" }),
  requestPrint: (id: string) =>
    req<Project>(`/v1/projects/${id}/print-request`, { method: "POST" }),
};
