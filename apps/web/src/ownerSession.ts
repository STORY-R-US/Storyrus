/** Sessão compartilhada dos painéis do dono (/gastos, /pedidos, /usuarios). */

import { getToken } from "./api";

export const OWNER_PASSWORD_KEY = "storyrus.usage.password";
/** Marca que o painel abriu com o JWT do estúdio (sem senha do dashboard). */
export const OWNER_SESSION_KEY = "storyrus.usage.session";
export const OWNER_SESSION_TOKEN = "__session__";

export function readOwnerSecret(): string {
  try {
    const stored = sessionStorage.getItem(OWNER_PASSWORD_KEY);
    if (stored) return stored;
    if (sessionStorage.getItem(OWNER_SESSION_KEY) === "1") return OWNER_SESSION_TOKEN;
  } catch {
    /* ignore */
  }
  return "";
}

export function persistOwnerSecret(secret: string | null | undefined): void {
  try {
    const cleaned = (secret ?? "").trim();
    if (!cleaned || cleaned === OWNER_SESSION_TOKEN) {
      sessionStorage.removeItem(OWNER_PASSWORD_KEY);
      sessionStorage.setItem(OWNER_SESSION_KEY, "1");
      return;
    }
    sessionStorage.setItem(OWNER_PASSWORD_KEY, cleaned);
    sessionStorage.removeItem(OWNER_SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function clearOwnerSecret(): void {
  try {
    sessionStorage.removeItem(OWNER_PASSWORD_KEY);
    sessionStorage.removeItem(OWNER_SESSION_KEY);
  } catch {
    /* ignore */
  }
}

/** Valor enviado à API: senha real ou undefined (só Bearer). */
export function apiOwnerPassword(secret: string | null | undefined): string | undefined {
  const cleaned = (secret ?? "").trim();
  if (!cleaned || cleaned === OWNER_SESSION_TOKEN) return undefined;
  return cleaned;
}

export function canTryOwnerSession(): boolean {
  return Boolean(getToken());
}

/** 401/429 — credencial rejeitada; limpa sessão do painel. */
export function isOwnerAuthFailure(status: number | undefined): boolean {
  return status === 401 || status === 429;
}

/** Rede / cold start / 502–504 — não é senha errada; vale retry. */
export function isOwnerTransientFailure(
  status: number | undefined,
  message?: string,
): boolean {
  if (status === 502 || status === 504 || status === 500) return true;
  if (status != null) return false;
  return /failed to fetch|networkerror|load failed|demorou demais|abort|indispon/i.test(
    message || "",
  );
}

export function ownerGateError(
  status: number | undefined,
  fallback: string,
  opts?: { usedSession?: boolean },
): string {
  const detail = (fallback || "").replace(/^\d{3}:\s*/i, "").trim();
  if (isOwnerTransientFailure(status, fallback)) {
    return "Servidor indisponível ou acordando (Render). Toque em Tentar de novo — pode levar cerca de um minuto.";
  }
  if (status === 401 && /administrador/i.test(detail)) {
    return "Acesso restrito a administradores. Entre com a conta admin ou use a senha do painel (Render).";
  }
  if (status === 401 && opts?.usedSession) {
    return "Esta sessão não é admin. Entre com a conta admin ou use a senha do painel (Render) — não a senha da conta.";
  }
  if (status === 401) return "Senha inválida. Use a senha do painel (Render), não a da conta.";
  if (status === 429) return "Muitas tentativas. Aguarde alguns minutos ou entre com a conta do dono.";
  if (status === 503) return "Painel ainda não configurado no servidor.";
  return detail || fallback;
}
