/** Aguarda o cold start antes de enviar ações que não podem ser repetidas. */
const READY_TTL_MS = 60_000;
const WARMUP_TIMEOUT_MS = 90_000;
const HEALTH_TIMEOUT_MS = 10_000;
const RETRY_DELAY_MS = 2_000;

let lastReadyAt = 0;
let warmupPromise: Promise<void> | null = null;
let warming = false;
const listeners = new Set<() => void>();

export function subscribeBackendConnection(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isBackendWarming(): boolean {
  return warming;
}

function setWarming(value: boolean): void {
  warming = value;
  listeners.forEach((listener) => listener());
}

export class BackendUnavailableError extends Error {
  readonly status = 504;

  constructor() {
    super("504: Servidor temporariamente indisponível. Tente novamente em instantes.");
    this.name = "BackendUnavailableError";
  }
}

/** O prazo é finito mesmo quando um transporte ignora AbortSignal. */
async function withTimeout<T>(
  run: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  signal?: AbortSignal | null,
): Promise<T> {
  if (signal?.aborted) throw new DOMException("Requisição cancelada", "AbortError");
  const controller = new AbortController();
  let rejectStopped!: (reason: Error) => void;
  const stopped = new Promise<never>((_resolve, reject) => { rejectStopped = reject; });
  const onAbort = () => {
    rejectStopped(new DOMException("Requisição cancelada", "AbortError"));
    controller.abort();
  };
  signal?.addEventListener("abort", onAbort, { once: true });
  const timer = window.setTimeout(() => {
    rejectStopped(new BackendUnavailableError());
    controller.abort();
  }, timeoutMs);
  try {
    return await Promise.race([run(controller.signal), stopped]);
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

async function probeBackend(): Promise<void> {
  const deadline = Date.now() + WARMUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    try {
      const healthy = await withTimeout(async (signal) => {
        const response = await fetch("/health", {
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal,
        });
        // O proxy pode devolver HTML (inclusive 200) enquanto o Render acorda.
        return response.ok && (await response.json()).status === "ok";
      }, Math.min(HEALTH_TIMEOUT_MS, deadline - Date.now()));
      if (healthy) {
        lastReadyAt = Date.now();
        return;
      }
    } catch {
      // Só o GET /health é repetido durante o cold start.
    }
    const remaining = deadline - Date.now();
    if (remaining > 0) {
      await new Promise((resolve) => window.setTimeout(resolve, Math.min(RETRY_DELAY_MS, remaining)));
    }
  }
  throw new BackendUnavailableError();
}

/** Uma única espera compartilhada por login, uploads e painéis concorrentes. */
export function warmBackend(): Promise<void> {
  if (warmupPromise) return warmupPromise;
  if (lastReadyAt && Date.now() - lastReadyAt < READY_TTL_MS) return Promise.resolve();

  const noticeTimer = window.setTimeout(() => setWarming(true), 1_500);
  warmupPromise = probeBackend().finally(() => {
    window.clearTimeout(noticeTimer);
    setWarming(false);
    warmupPromise = null;
  });
  return warmupPromise;
}

/** Cancelar uma chamada não cancela o despertar compartilhado por outras. */
async function waitForBackend(signal?: AbortSignal | null): Promise<void> {
  if (!signal) return warmBackend();
  if (signal.aborted) throw new DOMException("Requisição cancelada", "AbortError");
  await new Promise<void>((resolve, reject) => {
    const onAbort = () => reject(new DOMException("Requisição cancelada", "AbortError"));
    signal.addEventListener("abort", onAbort, { once: true });
    void warmBackend().then(resolve, reject).finally(() => signal.removeEventListener("abort", onAbort));
  });
}

/** Protege chamadas à API; URLs assinadas do storage continuam indo direto. */
export async function backendFetch(
  path: string,
  init: RequestInit = {},
  timeoutMs = 75_000,
): Promise<Response> {
  const safeToReplay = ["GET", "HEAD"].includes((init.method ?? "GET").toUpperCase());
  for (let attempt = 0; ; attempt++) {
    await waitForBackend(init.signal);
    try {
      const response = await withTimeout((signal) => fetch(path, { ...init, signal }), timeoutMs, init.signal);
      const proxyFailure = [502, 503, 504].includes(response.status)
        || response.headers.get("Content-Type")?.includes("text/html");
      if (!proxyFailure) {
        lastReadyAt = Date.now();
        return response;
      }
      lastReadyAt = 0;
      if (!safeToReplay || attempt > 0) {
        if (response.ok) throw new BackendUnavailableError();
        return response;
      }
    } catch (error) {
      lastReadyAt = 0;
      if (init.signal?.aborted || !safeToReplay || attempt > 0) throw error;
    }
    // Apenas leituras: uma retomada automática após falha do proxy/rede.
  }
}

/** Estado isolado entre testes, sem desativar a verificação de saúde. */
export function resetBackendConnectionForTests(): void {
  lastReadyAt = 0;
}
