import AsyncStorage from "@react-native-async-storage/async-storage";
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

const TOKEN_KEY = "storyrus_token";

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

async function sessionToken(response: Response): Promise<string | null> {
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw httpError(response.status, "Não foi possível renovar a sessão agora");
  const data = (await response.json()) as { access_token?: string };
  if (!data.access_token) throw httpError(502, "Resposta de sessão indisponível");
  return data.access_token;
}

let token: string | null = null;
let guestPromise: Promise<void> | null = null;
let hydratePromise: Promise<void> | null = null;

export function getToken(): string | null {
  return token;
}

export function setToken(t: string | null) {
  token = t;
  void (t
    ? AsyncStorage.setItem(TOKEN_KEY, t)
    : AsyncStorage.removeItem(TOKEN_KEY)
  ).catch(() => {
    /* ignore persistence failures */
  });
}

/** Load persisted JWT into memory. Call once at app boot before API use. */
export function hydrateToken(): Promise<void> {
  if (!hydratePromise) {
    hydratePromise = (async () => {
      try {
        const stored = await AsyncStorage.getItem(TOKEN_KEY);
        if (stored) token = stored;
      } catch {
        /* ignore */
      }
    })();
  }
  return hydratePromise;
}

/** Garante sessão de conta (sem mintar convidado). */
export async function ensureSession(): Promise<void> {
  await hydrateToken();
  if (!token) {
    throw httpError(401, "Nao autenticado");
  }
  if (tokenExpired(token)) {
    const old = token;
    const ok = await resumeSession(old);
    if (ok) return;
    setToken(null);
    throw httpError(401, "Nao autenticado");
  }
  if (tokenExpiresSoon(token)) {
    void refreshSession().catch(() => { /* falha temporária mantém a sessão */ });
  }
}

/** @deprecated Use ensureSession. */
export async function ensureGuest(): Promise<void> {
  return ensureSession();
}

export function logout(): void {
  setToken(null);
  guestPromise = null;
}

function readJwtPayload(t: string): { exp?: number } | null {
  try {
    const parts = t.split(".");
    if (parts.length < 2) return null;
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    // atob is available in RN Hermes / modern JS engines.
    const json = globalThis.atob(b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "="));
    return JSON.parse(json) as { exp?: number };
  } catch {
    return null;
  }
}

function tokenExpired(t: string, nowSec = Date.now() / 1000): boolean {
  const payload = readJwtPayload(t);
  if (!payload?.exp) return false;
  return payload.exp <= nowSec;
}

function tokenExpiresSoon(t: string, skewSec = 60 * 60 * 2, nowSec = Date.now() / 1000): boolean {
  const payload = readJwtPayload(t);
  if (!payload?.exp) return false;
  return payload.exp <= nowSec + skewSec;
}

let refreshPromise: Promise<boolean> | null = null;
let resumePromise: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (!token) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const resp = await fetch(`${BASE}/v1/auth/refresh`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const next = await sessionToken(resp);
      if (!next) return false;
      setToken(next);
      return true;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function resumeSession(oldToken: string): Promise<boolean> {
  if (!resumePromise) {
    resumePromise = (async () => {
      const resp = await fetch(`${BASE}/v1/auth/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: oldToken }),
      });
      const next = await sessionToken(resp);
      if (!next) return false;
      setToken(next);
      return true;
    })().finally(() => {
      resumePromise = null;
    });
  }
  return resumePromise;
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
  const skipSession =
    path.startsWith("/v1/auth/signup") ||
    path.startsWith("/v1/auth/login") ||
    path.startsWith("/v1/auth/guest") ||
    path.startsWith("/v1/auth/resume") ||
    path.startsWith("/v1/auth/verify-email");
  if (!skipSession) await ensureSession();

  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (!(init.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers.Authorization = `Bearer ${token}`;
  let resp = await fetch(`${BASE}${path}`, { ...init, headers });
  if (resp.status === 401 && token && !path.startsWith("/v1/auth/")) {
    const old = token;
    const resumed = await resumeSession(old);
    if (resumed) {
      headers.Authorization = `Bearer ${token}`;
      resp = await fetch(`${BASE}${path}`, { ...init, headers });
    } else {
      setToken(null);
    }
  }
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

export type SignupPayload = {
  email: string;
  password: string;
  password_confirm: string;
  full_name: string;
  phone: string;
  postal_code: string;
  street: string;
  number: string;
  complement?: string | null;
  district: string;
  city: string;
  state: string;
  accept_terms: boolean;
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
};

export const api = {
  guest: () =>
    req<{ access_token: string }>("/v1/auth/guest", { method: "POST" }),
  signup: async (payload: SignupPayload) =>
    req<{ ok: boolean; message: string; verify_token?: string | null }>("/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyEmail: async (tokenValue: string) => {
    const out = await req<{ access_token: string }>("/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token: tokenValue }),
    });
    setToken(out.access_token);
    return out;
  },
  upgrade: async (payload: SignupPayload) =>
    req<{ ok: boolean; message: string; verify_token?: string | null }>("/v1/auth/upgrade", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: async (email: string, password: string) => {
    const out = await req<{ access_token: string }>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(out.access_token);
    return out;
  },
  me: () => req<MeUser>("/v1/auth/me"),
  updateMe: (payload: Partial<SignupPayload>) =>
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
