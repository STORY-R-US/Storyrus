import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ensureSession, getToken, resumeSession, setToken } from "./api";
import { resetBackendConnectionForTests } from "./backendConnection";

describe("recuperação de sessão durante indisponibilidade", () => {
  const fetchMock = vi.fn();
  let expired: string;

  function json(body: unknown, status = 200, headers: Record<string, string> = {}) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json", ...headers },
    });
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-15T12:00:00Z"));
    resetBackendConnectionForTests();
    expired = `e30.${btoa(JSON.stringify({ sub: "u1", exp: Date.now() / 1000 - 60 }))}.sig`;
    setToken(expired);
    fetchMock.mockReset();
    vi.stubGlobal("fetch", (path: string, init?: RequestInit) => path === "/health"
      ? Promise.resolve(json({ status: "ok" }))
      : fetchMock(path, init));
  });

  afterEach(() => {
    setToken(null);
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it.each([429, 500, 502, 503, 504])("preserva a sessão quando a API responde %s", async (status) => {
    fetchMock.mockResolvedValue(json({ detail: "Indisponível" }, status));
    await expect(ensureSession()).rejects.toThrow(`${status}:`);
    expect(getToken()).toBe(expired);
    expect(localStorage.getItem("storyrus_token")).toBe(expired);
  });

  it("respeita Retry-After antes de repetir a renovação", async () => {
    fetchMock
      .mockResolvedValueOnce(json({}, 429, { "Retry-After": "3" }))
      .mockResolvedValueOnce(json({ access_token: "fresh-token" }));

    await expect(ensureSession()).rejects.toThrow("429:");
    await expect(ensureSession()).rejects.toThrow("429:");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(3_000);
    await expect(ensureSession()).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(getToken()).toBe("fresh-token");
  });

  it("aceita Retry-After como data HTTP", async () => {
    const retryAt = new Date(Date.now() + 5_000).toUTCString();
    fetchMock
      .mockResolvedValueOnce(json({}, 503, { "Retry-After": retryAt }))
      .mockResolvedValueOnce(json({ access_token: "fresh-token" }));

    await expect(ensureSession()).rejects.toThrow("503:");
    await vi.advanceTimersByTimeAsync(4_000);
    await expect(ensureSession()).rejects.toThrow("503:");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    await expect(ensureSession()).resolves.toBeUndefined();
  });

  it("aguarda após 503 mesmo quando não há Retry-After", async () => {
    fetchMock
      .mockResolvedValueOnce(json({}, 503))
      .mockResolvedValueOnce(json({ access_token: "fresh-token" }));

    await expect(ensureSession()).rejects.toThrow("503:");
    await vi.advanceTimersByTimeAsync(9_000);
    await expect(ensureSession()).rejects.toThrow("503:");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    await expect(ensureSession()).resolves.toBeUndefined();
  });

  it("compartilha uma renovação entre chamadas concorrentes", async () => {
    fetchMock.mockResolvedValue(json({ access_token: "fresh-token" }));
    await Promise.all(Array.from({ length: 8 }, () => ensureSession()));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("limpa a sessão quando o servidor confirma token inválido", async () => {
    fetchMock.mockResolvedValue(json({ detail: "Token inválido" }, 401));
    await expect(ensureSession()).rejects.toThrow("401:");
    expect(getToken()).toBeNull();
  });

  it("preserva a sessão se a resposta 200 não contém um token", async () => {
    fetchMock.mockResolvedValue(json({}));
    await expect(ensureSession()).rejects.toThrow("502:");
    expect(getToken()).toBe(expired);
  });

  it("uma nova sessão pode renovar sem herdar o bloqueio da anterior", async () => {
    fetchMock
      .mockResolvedValueOnce(json({}, 429, { "Retry-After": "60" }))
      .mockResolvedValueOnce(json({ access_token: "fresh-token" }));
    await expect(ensureSession()).rejects.toThrow("429:");
    setToken("other-expired-token");
    await expect(resumeSession("other-expired-token")).resolves.toBe(true);
    expect(getToken()).toBe("fresh-token");
  });
});
