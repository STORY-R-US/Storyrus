import type {
  Job,
  JobAccepted,
  OrderTicket,
  OwnerUser,
  OwnerUsersReport,
  OwnerUserUpdate,
  Project,
  PrintAddress,
  PrintOrder,
  StoryTemplate,
  UploadUrl,
  UsageReport,
  UserVoice,
  VoiceList,
} from "./types";

const BASE = ""; // mesmo host (proxy do Vite cobre /v1)
const TOKEN_KEY = "storyrus_token";
/** Renova o JWT se faltar menos que isto para o `exp` (STO-26). */
const REFRESH_SKEW_SEC = 60 * 60 * 2;

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

let token: string | null = readStoredToken();
let refreshPromise: Promise<boolean> | null = null;
let resumePromise: Promise<boolean> | null = null;

export function setToken(t: string | null) {
  token = t;
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}
export function getToken() {
  return token;
}

/** Decodifica payload JWT (sem verificar assinatura — so para `exp` local). */
export function readJwtPayload(t: string): { exp?: number; sub?: string } | null {
  try {
    const parts = t.split(".");
    if (parts.length < 2) return null;
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "="));
    return JSON.parse(json) as { exp?: number; sub?: string };
  } catch {
    return null;
  }
}

function tokenExpired(t: string, nowSec = Date.now() / 1000): boolean {
  const payload = readJwtPayload(t);
  if (!payload?.exp) return false;
  return payload.exp <= nowSec;
}

function tokenExpiresSoon(t: string, skewSec = REFRESH_SKEW_SEC, nowSec = Date.now() / 1000): boolean {
  const payload = readJwtPayload(t);
  if (!payload?.exp) return false;
  return payload.exp <= nowSec + skewSec;
}

async function postToken(
  path: string,
  init: RequestInit = {},
): Promise<string | null> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), authFetchTimeoutMs);
  try {
    const resp = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { access_token?: string };
    return data.access_token ?? null;
  } finally {
    window.clearTimeout(timer);
  }
}

/** Headers dos paineis do dono: senha compartilhada e/ou JWT da sessão. */
function ownerHeaders(password?: string | null, extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const secret = (password ?? "").trim();
  if (secret) headers.set("X-Usage-Password", secret);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

async function ownerFetch(
  path: string,
  password: string | null | undefined,
  init: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), ownerFetchTimeoutMs);
  try {
    return await fetch(`${BASE}${path}`, {
      ...init,
      headers: ownerHeaders(password, init.headers),
      signal: init.signal ?? controller.signal,
    });
  } catch (err) {
    if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) {
      throw httpError(504, "Servidor demorou demais para responder");
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

async function readOwnerError(resp: Response): Promise<Error> {
  let detail = resp.statusText;
  try {
    detail = (await resp.json()).detail ?? detail;
  } catch {
    /* corpo vazio */
  }
  return httpError(resp.status, String(detail));
}

async function ownerJson<T>(
  path: string,
  password?: string | null,
  init: RequestInit = {},
): Promise<T> {
  await renewOwnerSession();
  let resp = await ownerFetch(path, password, init);
  // JWT vencido: o estúdio renova sozinho; o painel precisa do mesmo resume
  // antes de tratar a conta logada como "senha inválida".
  if (resp.status === 401 && token) {
    const before = token;
    const resumed = await resumeSession(before);
    if (resumed && token && token !== before) {
      resp = await ownerFetch(path, password, init);
    }
  }
  if (!resp.ok) throw await readOwnerError(resp);
  return resp.status === 204 ? (undefined as T) : ((await resp.json()) as T);
}

/** Reemite JWT enquanto o atual ainda e aceito pela API. */
export async function refreshSession(): Promise<boolean> {
  if (!token) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const next = await postToken("/v1/auth/refresh", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!next) return false;
      setToken(next);
      return true;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

/** Recupera o mesmo user_id a partir de um JWT expirado (evita orfaos). */
export async function resumeSession(oldToken: string): Promise<boolean> {
  if (!resumePromise) {
    resumePromise = (async () => {
      const next = await postToken("/v1/auth/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: oldToken }),
      });
      if (!next) return false;
      setToken(next);
      return true;
    })().finally(() => {
      resumePromise = null;
    });
  }
  return resumePromise;
}

/**
 * Garante sessão de conta (sem mintar convidado).
 * Refresh/resume se o JWT existir; sem token → 401 para a UI redirecionar.
 */
export async function ensureSession(): Promise<void> {
  if (!token) {
    throw new Error("401: Nao autenticado");
  }
  if (tokenExpired(token)) {
    const old = token;
    const ok = await resumeSession(old);
    if (ok) return;
    setToken(null);
    throw new Error("401: Nao autenticado");
  }
  if (tokenExpiresSoon(token)) {
    void refreshSession();
  }
}

/** @deprecated Use ensureSession — web não mintar mais guest automaticamente. */
export async function ensureGuest(): Promise<void> {
  return ensureSession();
}

export function logout(): void {
  setToken(null);
}

function uuid(): string {
  return crypto.randomUUID();
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

/** Erros HTTP do `req` (ex.: "402: ...") vs falha de rede/ambígua. */
function isHttpErrorMessage(message: string): boolean {
  return /^\d{3}:/.test(message);
}

function httpStatus(message: string): number {
  const match = /^(\d{3}):/.exec(message);
  return match ? Number(match[1]) : 0;
}

/** 5xx: a prévia pode ter sido gravada. Mantém a Idempotency-Key e tenta de novo. */
function isRetryableHttpStatus(status: number): boolean {
  return status >= 500 && status <= 599;
}

/** Limpa estado de idempotência (só para testes). */
export function resetStepIdempotencyState(): void {
  stepIdempotencyKeys.clear();
  stepInFlight.clear();
}

/** Auth calls must not hang forever when the API/proxy is down (browser fetch has no default timeout). */
export let authFetchTimeoutMs = 15_000;

/** Painéis do dono: cold start do Render cabe; não fica em "Abrindo…" para sempre. */
export let ownerFetchTimeoutMs = 75_000;

/** Só para testes — restaura o valor padrão depois. */
export function setAuthFetchTimeoutMsForTests(ms: number): void {
  authFetchTimeoutMs = ms;
}

/** Só para testes — restaura o valor padrão depois. */
export function setOwnerFetchTimeoutMsForTests(ms: number): void {
  ownerFetchTimeoutMs = ms;
}

function httpError(status: number, detail: string): Error & { status: number } {
  const err = new Error(`${status}: ${detail}`) as Error & { status: number };
  err.status = status;
  return err;
}

/**
 * Renova o JWT antes do painel. Não apaga o token se o Render estiver
 * acordando — a senha do painel e um novo toque em "abrir com esta sessão"
 * ainda podem entrar.
 */
async function renewOwnerSession(): Promise<void> {
  if (!token) return;
  try {
    if (tokenExpired(token)) {
      await resumeSession(token);
      return;
    }
    if (tokenExpiresSoon(token)) {
      await refreshSession();
    }
  } catch {
    /* a chamada segue com o token atual */
  }
}

function isAuthPath(path: string): boolean {
  return (
    path.startsWith("/v1/auth/signup") ||
    path.startsWith("/v1/auth/login") ||
    path.startsWith("/v1/auth/guest") ||
    path.startsWith("/v1/auth/resume") ||
    path.startsWith("/v1/auth/upgrade") ||
    path.startsWith("/v1/auth/verify-email") ||
    path.startsWith("/v1/auth/resend-verify") ||
    path.startsWith("/v1/auth/forgot-password") ||
    path.startsWith("/v1/auth/reset-password") ||
    path.startsWith("/v1/auth/me") ||
    path.startsWith("/v1/auth/refresh")
  );
}

async function reqOnce(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const timeoutMs = isAuthPath(path) ? authFetchTimeoutMs : undefined;
  let timedOut = false;
  const controller = timeoutMs ? new AbortController() : null;
  const timer = controller
    ? window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs)
    : undefined;
  try {
    return await fetch(`${BASE}${path}`, {
      ...init,
      headers,
      signal: init.signal ?? controller?.signal,
    });
  } catch (err) {
    if (timedOut || (err instanceof DOMException && err.name === "AbortError")) {
      throw new Error(
        timedOut
          ? "504: Servidor demorou demais para responder"
          : ((err as Error).message || "Requisição cancelada"),
      );
    }
    throw err;
  } finally {
    if (timer !== undefined) window.clearTimeout(timer);
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const skipSession =
    path.startsWith("/v1/auth/signup") ||
    path.startsWith("/v1/auth/login") ||
    path.startsWith("/v1/auth/guest") ||
    path.startsWith("/v1/auth/resume") ||
    path.startsWith("/v1/auth/verify-email") ||
    path.startsWith("/v1/auth/resend-verify") ||
    path.startsWith("/v1/auth/forgot-password") ||
    path.startsWith("/v1/auth/reset-password");
  if (!skipSession) await ensureSession();

  let resp = await reqOnce(path, init);
  // Token morto: tenta resume do JWT antigo; sem sucesso limpa a sessão.
  if (resp.status === 401 && token && !path.startsWith("/v1/auth/")) {
    const old = token;
    const resumed = await resumeSession(old);
    if (resumed) {
      resp = await reqOnce(path, init);
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
    throw new Error(`${resp.status}: ${detail}`);
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
  district?: string | null;
  city: string;
  state: string;
  country: string;
  accept_terms: boolean;
};

export type MeUser = {
  id: string;
  email: string;
  credits: number;
  created_at: string;
  is_guest: boolean;
  email_verified: boolean;
  is_admin?: boolean;
  is_owner?: boolean;
  full_name: string | null;
  phone: string | null;
  postal_code: string | null;
  street: string | null;
  number: string | null;
  complement: string | null;
  district: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
};

export type ProfileUpdatePayload = Partial<
  Pick<
    SignupPayload,
    | "full_name"
    | "phone"
    | "postal_code"
    | "street"
    | "number"
    | "complement"
    | "district"
    | "city"
    | "state"
    | "country"
  >
>;

export type SignupResult = {
  ok: boolean;
  message: string;
  verify_token?: string | null;
};

export const api = {
  /** Cadastro completo — não emite JWT; usuário deve verificar o e-mail. */
  async signup(payload: SignupPayload) {
    return req<SignupResult>("/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  async verifyEmail(token: string) {
    const out = await req<{ access_token: string }>("/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
    setToken(out.access_token);
    return out;
  },
  async resendVerify(email: string) {
    return req<SignupResult>("/v1/auth/resend-verify", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  async login(email: string, password: string) {
    const out = await req<{ access_token: string }>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(out.access_token);
    return out;
  },
  async forgotPassword(email: string) {
    return req<{ ok: boolean; message: string; reset_token?: string | null }>(
      "/v1/auth/forgot-password",
      {
        method: "POST",
        body: JSON.stringify({ email }),
      },
    );
  },
  async resetPassword(token: string, password: string, passwordConfirm: string) {
    const out = await req<{ access_token: string }>("/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({
        token,
        password,
        password_confirm: passwordConfirm,
      }),
    });
    setToken(out.access_token);
    return out;
  },
  /** Guest → conta real no mesmo user_id (exige verificar e-mail depois). */
  async upgrade(payload: SignupPayload) {
    return req<SignupResult>("/v1/auth/upgrade", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  logout,
  async me() {
    return req<MeUser>("/v1/auth/me");
  },
  async updateMe(payload: ProfileUpdatePayload) {
    return req<MeUser>("/v1/auth/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  async refresh() {
    return refreshSession();
  },
  async credits() {
    return req<{ credits: number }>("/v1/credits");
  },
  async createProject(input: {
    theme?: string;
    childName?: string;
    dedication?: string;
    childAge?: number;
    style?: "cgi_3d" | "realistic" | "cartoon";
    bookSize?: "M" | "P";
    coverType?: "soft" | "hard";
    language?: string;
  } = {}) {
    const theme = input.theme?.trim().slice(0, 32) || undefined;
    return req<Project>("/v1/projects", {
      method: "POST",
      body: JSON.stringify({
        style: input.style ?? "cgi_3d",
        theme,
        book_size: input.bookSize,
        cover_type: input.coverType,
        child_name: input.childName?.trim() || undefined,
        child_age: input.childAge ?? undefined,
        dedication: input.dedication?.trim() || undefined,
        language: input.language,
      }),
    });
  },
  async getProject(id: string) {
    return req<Project>(`/v1/projects/${id}`);
  },
  // URLs (assinadas) dos resultados de cada etapa.
  async getAssets(id: string) {
    return req<{
      character_url: string | null;
      realistic_url: string | null;
      extra_characters: { name: string; url: string }[];
      page_images: string[];
      cover_url?: string | null;
      in_hand_url?: string | null;
      ebook_url: string | null;
      video_url: string | null;
      narrated_video_url: string | null;
    }>(`/v1/projects/${id}/assets`);
  },
  // Upload da foto via API (servidor grava no storage). Evita PUT do navegador.
  async uploadPhoto(
    id: string,
    file: File,
    meta?: {
      language?: string;
      themeLabel?: string;
      extraNames?: string;
      gender?: string;
      subject?: string;
      alsoName?: string;
      alsoGender?: string;
      alsoSubject?: string;
      quantity?: string;
      clientName?: string;
      clientEmail?: string;
      clientPhone?: string;
      clientAddress?: string;
      clientNotes?: string;
      finalize?: boolean;
    },
  ) {
    await ensureGuest();
    const fd = new FormData();
    fd.append("file", file);
    if (meta?.language) fd.append("language", meta.language);
    if (meta?.themeLabel) fd.append("theme_label", meta.themeLabel);
    if (meta?.extraNames) fd.append("extra_names", meta.extraNames);
    if (meta?.gender) fd.append("gender", meta.gender);
    if (meta?.subject) fd.append("subject", meta.subject);
    if (meta?.alsoName) fd.append("also_name", meta.alsoName);
    if (meta?.alsoGender) fd.append("also_gender", meta.alsoGender);
    if (meta?.alsoSubject) fd.append("also_subject", meta.alsoSubject);
    if (meta?.clientName) fd.append("client_name", meta.clientName);
    if (meta?.clientEmail) fd.append("client_email", meta.clientEmail);
    if (meta?.clientPhone) fd.append("client_phone", meta.clientPhone);
    if (meta?.clientAddress) fd.append("client_address", meta.clientAddress);
    if (meta?.clientNotes) fd.append("client_notes", meta.clientNotes);
    if (meta?.quantity) fd.append("quantity", meta.quantity);
    if (meta?.finalize === false) fd.append("finalize", "0");
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const resp = await fetch(`${BASE}/v1/projects/${id}/photo`, {
      method: "POST",
      body: fd,
      headers,
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        detail = (await resp.json()).detail ?? detail;
      } catch {
        /* corpo vazio */
      }
      throw new Error(`${resp.status}: ${detail}`);
    }
    return resp.json();
  },
  // Usar uma história fornecida pelo usuário (digitada/colada). Sem IA.
  async setStoryText(id: string, story_text: string) {
    return req<Project>(`/v1/projects/${id}/story/text`, {
      method: "POST",
      body: JSON.stringify({ story_text }),
    });
  },
  // Catálogo de histórias prontas da plataforma.
  async storyTemplates() {
    return req<StoryTemplate[]>("/v1/projects/story-templates");
  },
  // Usar uma história pronta do catálogo, personalizada com o nome. Sem IA, sem créditos.
  async applyStoryTemplate(id: string, template_id: string) {
    return req<Project>(`/v1/projects/${id}/story/template`, {
      method: "POST",
      body: JSON.stringify({ template_id }),
    });
  },
  // Extrair o texto de um arquivo (PDF/DOCX/TXT) enviado pelo usuário.
  async extractStory(id: string, file: File) {
    await ensureGuest();
    const fd = new FormData();
    fd.append("file", file);
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const resp = await fetch(`${BASE}/v1/projects/${id}/story/extract`, {
      method: "POST",
      body: fd,
      headers,
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        detail = (await resp.json()).detail ?? detail;
      } catch {
        /* corpo vazio */
      }
      throw new Error(`${resp.status}: ${detail}`);
    }
    return (await resp.json()) as { text: string };
  },
  async listJobs(id: string) {
    return req<Job[]>(`/v1/projects/${id}/jobs`);
  },
  async requestPhotoUpload(id: string, contentType: string, ext: string) {
    return req<UploadUrl>(`/v1/projects/${id}/photos`, {
      method: "POST",
      body: JSON.stringify({ content_type: contentType, ext }),
    });
  },
  async uploadToSignedUrl(url: string, file: File) {
    // PUT direto no storage (URL assinada). Em dev (stub) pode falhar silenciosamente.
    try {
      await fetch(url, { method: "PUT", body: file, headers: { "Content-Type": file.type } });
    } catch {
      /* storage stub local */
    }
  },
  startStep(
    id: string,
    step: "avatar" | "realistic" | "story" | "ebook" | "video" | "extra-character" | "narrated-video",
    body: Record<string, unknown> = {},
  ): Promise<JobAccepted> {
    // Clique duplo / retry em voo: mesma promise + mesma Idempotency-Key.
    const cacheKey = stepCacheKey(id, step);
    const inFlight = stepInFlight.get(cacheKey);
    if (inFlight) return inFlight as Promise<JobAccepted>;

    const idempotencyKey = getOrCreateStepIdempotencyKey(id, step);
    const promise = (async () => {
      try {
        const accepted = await req<JobAccepted>(`/v1/projects/${id}/${step}`, {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
          body: JSON.stringify(body),
        });
        // Sucesso: libera a chave para um próximo start intencional (regenerar).
        releaseStepIdempotencyKey(id, step);
        return accepted;
      } catch (err) {
        const message = err instanceof Error ? err.message : "";
        // Resposta HTTP definitiva: libera. Falha de rede: mantém a chave no retry.
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
  /** Cadeia automática: avatar → história → ebook → vídeo (prévia no Studio). */
  startPreview(id: string, body: { brief?: string } = {}): Promise<JobAccepted> {
    const step = "preview";
    const cacheKey = stepCacheKey(id, step);
    const inFlight = stepInFlight.get(cacheKey);
    if (inFlight) return inFlight as Promise<JobAccepted>;

    const idempotencyKey = getOrCreateStepIdempotencyKey(id, step);
    const promise = (async () => {
      const maxAttempts = 3;
      try {
        let lastError: unknown;
        for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
          try {
            const accepted = await req<JobAccepted>(`/v1/projects/${id}/preview`, {
              method: "POST",
              headers: { "Idempotency-Key": idempotencyKey },
              body: JSON.stringify(body),
            });
            releaseStepIdempotencyKey(id, step);
            return accepted;
          } catch (err) {
            lastError = err;
            const message = err instanceof Error ? err.message : "";
            const status = httpStatus(message);
            const retryable = isRetryableHttpStatus(status);
            if (!retryable || attempt === maxAttempts) {
              // 4xx é definitivo. 5xx esgotado mantém a chave: o retry manual
              // reencontra o job se o insert chegou a commitar.
              if (isHttpErrorMessage(message) && !retryable) {
                releaseStepIdempotencyKey(id, step);
              }
              throw err;
            }
            await new Promise((resolve) => window.setTimeout(resolve, 200 * attempt));
          }
        }
        throw lastError;
      } finally {
        stepInFlight.delete(cacheKey);
      }
    })();

    stepInFlight.set(cacheKey, promise);
    return promise;
  },
  async listVoices() {
    return req<VoiceList>("/v1/voices");
  },
  async uploadVoice(file: File, name: string, makeDefault = false) {
    await ensureGuest();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    fd.append("make_default", makeDefault ? "true" : "false");
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const resp = await fetch(`${BASE}/v1/voices`, { method: "POST", body: fd, headers });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        detail = (await resp.json()).detail ?? detail;
      } catch {
        /* corpo vazio */
      }
      throw new Error(`${resp.status}: ${detail}`);
    }
    return (await resp.json()) as UserVoice;
  },
  async setDefaultVoice(id: string) {
    return req<UserVoice>(`/v1/voices/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_default: true }),
    });
  },
  async deleteVoice(id: string) {
    return req<void>(`/v1/voices/${id}`, { method: "DELETE" });
  },
  async approveCharacter(id: string) {
    return req<Project>(`/v1/projects/${id}/avatar/approve`, { method: "POST" });
  },
  async approveBook(id: string) {
    return req<Project>(`/v1/projects/${id}/book/approve`, { method: "POST" });
  },
  async requestPrint(id: string) {
    return req<Project>(`/v1/projects/${id}/print-request`, { method: "POST" });
  },
  async printOrder(id: string) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order`);
  },
  async setPrintQuantity(id: string, quantity: number) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/quantity`, {
      method: "PUT",
      body: JSON.stringify({ quantity }),
    });
  },
  async savePrintAddress(id: string, body: PrintAddress) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/address`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  async quotePrintFreight(id: string) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/freight`, { method: "POST" });
  },
  async selectPrintFreight(id: string, serviceId: number) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/freight/select`, {
      method: "POST",
      body: JSON.stringify({ service_id: serviceId }),
    });
  },
  async checkoutPrint(id: string, installments: number) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/checkout`, {
      method: "POST",
      body: JSON.stringify({ installments }),
    });
  },
  // Upload de foto de personagem extra
  async uploadExtraCharacter(id: string, file: File, name: string) {
    await ensureGuest();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const resp = await fetch(`${BASE}/v1/projects/${id}/extra-character`, {
      method: "POST",
      body: fd,
      headers,
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        detail = (await resp.json()).detail ?? detail;
      } catch {
        /* corpo vazio */
      }
      throw new Error(`${resp.status}: ${detail}`);
    }
    return resp.json();
  },
  async usage(password?: string | null, from?: string, to?: string, scope?: "orders") {
    const q = new URLSearchParams();
    if (from) q.set("from", from);
    if (to) q.set("to", to);
    if (scope) q.set("scope", scope);
    const suffix = q.toString() ? `?${q}` : "";
    return ownerJson<UsageReport>(`/v1/usage${suffix}`, password);
  },
  async deleteOrder(password: string | null | undefined, id: string) {
    await ownerJson<void>(`/v1/usage/orders/${id}`, password, { method: "DELETE" });
  },
  async generateOrderImages(password: string | null | undefined, id: string) {
    return ownerJson<JobAccepted>(`/v1/usage/orders/${id}/generate`, password, { method: "POST" });
  },
  /** Pedidos da própria conta (visão de quem não é admin em "Meus Pedidos"). */
  async myOrders() {
    return req<OrderTicket[]>("/v1/usage/orders/mine");
  },
  async users(password?: string | null) {
    return ownerJson<OwnerUsersReport>("/v1/users", password);
  },
  async user(password: string | null | undefined, id: string) {
    return ownerJson<OwnerUser>(`/v1/users/${id}`, password);
  },
  async updateUser(password: string | null | undefined, id: string, body: OwnerUserUpdate) {
    return ownerJson<OwnerUser>(`/v1/users/${id}`, password, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  async deleteUser(password: string | null | undefined, id: string) {
    await ownerJson<void>(`/v1/users/${id}`, password, { method: "DELETE" });
  },
  async downloadPrintPackage(password: string | null | undefined, id: string) {
    const headers = ownerHeaders(password);
    const resp = await fetch(`${BASE}/v1/print-orders/${id}/package`, { headers });
    if (!resp.ok) throw new Error("Pacote de produção indisponível.");
    return resp.blob();
  },
  async setPrintValidation(password: string | null | undefined, id: string, next: string) {
    return ownerJson<PrintOrder>(`/v1/print-orders/${id}/validation`, password, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
  },
};
