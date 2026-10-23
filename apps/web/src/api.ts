import { BackendUnavailableError, backendFetch } from "./backendConnection";
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

type ClerkTokenGetter = (opts?: { skipCache?: boolean }) => Promise<string | null>;

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

let token: string | null = readStoredToken();
/** Testes e o e2e gravam o Bearer aqui. A sessão real vem do Clerk. */
let manualOverride = Boolean(token);
let clerkGetToken: ClerkTokenGetter | null = null;
let clerkSignOut: (() => Promise<void>) | null = null;

export function setClerkGetToken(fn: ClerkTokenGetter | null) {
  clerkGetToken = fn;
}

export function setClerkSignOut(fn: (() => Promise<void>) | null) {
  clerkSignOut = fn;
}

export function setToken(t: string | null) {
  token = t;
  manualOverride = Boolean(t);
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

async function resolveToken(): Promise<string | null> {
  if (manualOverride) return token;
  if (!clerkGetToken) return token;
  try {
    token = await clerkGetToken();
  } catch {
    /* mantém o último token se o Clerk não responder */
  }
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

/** Headers dos paineis do dono: senha compartilhada e/ou sessão do Clerk. */
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
  return backendFetch(`${BASE}${path}`, {
    ...init,
    headers: ownerHeaders(password, init.headers),
  }, ownerFetchTimeoutMs);
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
  await resolveToken();
  const resp = await ownerFetch(path, password, init);
  if (!resp.ok) throw await readOwnerError(resp);
  return resp.status === 204 ? (undefined as T) : ((await resp.json()) as T);
}

/**
 * Garante sessão de conta. O Clerk renova o token; sem sessão → 401.
 */
export async function ensureSession(): Promise<void> {
  const current = await resolveToken();
  if (!current) throw new Error("401: Nao autenticado");
}

/** @deprecated Use ensureSession — web não mintar mais guest automaticamente. */
export async function ensureGuest(): Promise<void> {
  return ensureSession();
}

export function logout(): void {
  setToken(null);
  void clerkSignOut?.();
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

/** Timeout após a API estar pronta; o cold start tem uma espera própria de 90s. */
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

function isAuthPath(path: string): boolean {
  return path.startsWith("/v1/auth/");
}

async function reqOnce(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return backendFetch(`${BASE}${path}`, { ...init, headers },
    isAuthPath(path) ? authFetchTimeoutMs : undefined);
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  await ensureSession();
  const resp = await reqOnce(path, init);
  if (resp.status === 401) setToken(null);

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
  terms_accepted_at?: string | null;
  adult_confirmed_at?: string | null;
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
> & { accept_terms?: boolean; confirm_adult?: boolean };

export const api = {
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
  async credits() {
    return req<{ credits: number }>("/v1/credits");
  },
  async createProject(input: {
    title?: string;
    gender?: "f" | "m";
    languages?: string[];
    themeDescription?: string;
    characters?: string;
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
        title: input.title?.trim() || undefined,
        gender: input.gender,
        languages: input.languages,
        theme_description: input.themeDescription,
        characters: input.characters,
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
  async myProjects() {
    return req<Project[]>("/v1/projects");
  },
  async deleteProject(id: string) {
    return req<void>(`/v1/projects/${id}`, { method: "DELETE" });
  },
  async savePreviewChanges(id: string, body: { title: string; theme_description: string; story_text: string; photo_notes: string }) {
    return req<JobAccepted>(`/v1/projects/${id}/preview/changes`, { method: "PUT", body: JSON.stringify(body) });
  },
  async updatePreviewTitle(id: string, title: string) {
    return req<JobAccepted>(`/v1/projects/${id}/preview/title`, { method: "PUT", body: JSON.stringify({ title }) });
  },
  async saveQuotation(id: string) {
    return req<Project>(`/v1/projects/${id}/quotation`, { method: "POST" });
  },
  async setPrintSpecification(id: string, book_size: string, cover_type: string) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/specification`, { method: "PUT", body: JSON.stringify({ book_size, cover_type }) });
  },
  async generatePurchasedBook(id: string) {
    return req<JobAccepted>(`/v1/projects/${id}/book/generate`, { method: "POST" });
  },
  async requestBookChanges(id: string, notes: string) {
    return req<JobAccepted>(`/v1/projects/${id}/book/changes`, { method: "POST", body: JSON.stringify({ notes }) });
  },
  // URLs (assinadas) dos resultados de cada etapa.
  async getAssets(id: string) {
    return req<{
      previews?: import("./studio/assets").BookImage[];
      page_versions?: import("./studio/assets").BookImage[];
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
    const resp = await backendFetch(`${BASE}/v1/projects/${id}/photo`, {
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
    const resp = await backendFetch(`${BASE}/v1/projects/${id}/story/extract`, {
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
        // Rede/5xx podem ter ocorrido após o commit: a próxima tentativa usa a mesma chave.
        if (isHttpErrorMessage(message) && !isRetryableHttpStatus(httpStatus(message))) {
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
  async approvePreview(id: string) {
    return req<Project>(`/v1/projects/${id}/preview/approve`, { method: "POST" });
  },
  async approveStory(id: string) {
    return req<Project>(`/v1/projects/${id}/story/approve`, { method: "POST" });
  },
  nextBookPage(id: string, body: { page?: number; adjustment?: string } = {}) {
    return req<JobAccepted>(`/v1/projects/${id}/pages/next`, {
      method: "POST", headers: { "Idempotency-Key": getOrCreateStepIdempotencyKey(id, "page") },
      body: JSON.stringify(body),
    }).then((result) => { releaseStepIdempotencyKey(id, "page"); return result; });
  },
  /** Three separate previews, then explicit approval in the Studio. */
  startPreview(id: string, body: { brief?: string; image?: string; language?: string; adjustment?: string } = {}): Promise<JobAccepted> {
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
            if (err instanceof BackendUnavailableError || !retryable || attempt === maxAttempts) {
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
    const resp = await backendFetch(`${BASE}/v1/voices`, { method: "POST", body: fd, headers });
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
  async confirmManualPayment(id: string) {
    return req<PrintOrder>(`/v1/projects/${id}/print-order/confirm-payment`, {
      method: "POST",
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
    const resp = await backendFetch(`${BASE}/v1/projects/${id}/extra-character`, {
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
    const resp = await backendFetch(`${BASE}/v1/print-orders/${id}/package`, { headers });
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
