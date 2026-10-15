import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BackendStatus } from "./BackendStatus";
import { api, ensureSession, getToken, setToken } from "./api";
import { backendFetch, isBackendWarming, warmBackend } from "./backendConnection";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json" },
});
const fetchMock = vi.fn();

beforeEach(() => {
  vi.useFakeTimers();
  fetchMock.mockReset();
  fetchMock.mockImplementation((path: string) => Promise.resolve(json(
    path === "/health" ? { status: "ok" } : { ok: true },
  )));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Render cold start", () => {
  it("aguarda 66s de cold start antes de enviar o login uma única vez", async () => {
    const readyAt = Date.now() + 65_000;
    fetchMock.mockImplementation((path: string) => Promise.resolve(
      path === "/health" && Date.now() < readyAt
        ? new Response("Acordando", { status: 503 })
        : json(path === "/health" ? { status: "ok" } : { access_token: "new-token" }),
    ));
    const login = backendFetch("/v1/auth/login", { method: "POST", body: "{}" }, 15_000);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock.mock.calls.every(([path]) => path === "/health")).toBe(true);
    expect(isBackendWarming()).toBe(true);
    await vi.advanceTimersByTimeAsync(6_000);
    expect((await login).status).toBe(200);
    expect(fetchMock.mock.calls.filter(([path]) => path === "/v1/auth/login")).toHaveLength(1);
    expect(isBackendWarming()).toBe(false);
  });

  it("recusa HTML 200 e JSON sem status ok no health check", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("<html>Waking up</html>", { headers: { "Content-Type": "text/html" } }))
      .mockResolvedValueOnce(json({ status: "starting" }))
      .mockResolvedValueOnce(json({ status: "ok" }));
    const ready = warmBackend();
    await vi.advanceTimersByTimeAsync(4_000);
    await ready;
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("compartilha o despertar entre chamadas concorrentes", async () => {
    let resolveHealth!: (response: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveHealth = resolve; }));
    const first = backendFetch("/v1/projects", { method: "POST" });
    const second = backendFetch("/v1/usage");
    expect(warmBackend()).toBe(warmBackend());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    resolveHealth(json({ status: "ok" }));
    await Promise.all([first, second]);
    expect(fetchMock.mock.calls.filter(([path]) => path === "/health")).toHaveLength(1);
  });

  it("encerra a espera em 90s e permite uma nova tentativa", async () => {
    fetchMock.mockResolvedValue(new Response("Acordando", { status: 503 }));
    const result = expect(backendFetch("/v1/projects", { method: "POST" })).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(90_000);
    await result;
    expect(isBackendWarming()).toBe(false);
    expect(fetchMock.mock.calls.every(([path]) => path === "/health")).toBe(true);
    fetchMock.mockImplementation((path: string) => Promise.resolve(json(path === "/health" ? { status: "ok" } : {})));
    expect((await backendFetch("/v1/projects", { method: "POST" })).ok).toBe(true);
  });

  it("a prévia não repete ciclos de 90s quando o despertar esgota o prazo", async () => {
    setToken("test-token");
    fetchMock.mockResolvedValue(new Response(null, { status: 503 }));
    const result = expect(api.startPreview("proj-1")).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(90_000);
    await result;
    expect(fetchMock.mock.calls.every(([path]) => path === "/health")).toBe(true);
    fetchMock.mockImplementation((path: string) => Promise.resolve(json(path === "/health"
      ? { status: "ok" } : { job_id: "j1", estimated_cost_credits: 1 })));
    await expect(api.startPreview("proj-1")).resolves.toMatchObject({ job_id: "j1" });
  });

  it("o painel com sessão também encerra a espera em 90s", async () => {
    setToken("test-token");
    fetchMock.mockResolvedValue(new Response(null, { status: 503 }));
    const result = expect(api.usage()).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(90_000);
    await result;
    expect(getToken()).toBe("test-token");
    expect(fetchMock.mock.calls.every(([path]) => path === "/health")).toBe(true);
  });

  it("limita também health checks cujo transporte ignora o cancelamento", async () => {
    fetchMock.mockImplementation(() => new Promise(() => {}));
    const result = expect(warmBackend()).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(90_000);
    await result;
    expect(isBackendWarming()).toBe(false);
  });

  it("verifica a API novamente ao voltar depois de inatividade", async () => {
    await backendFetch("/v1/credits");
    await backendFetch("/v1/credits");
    expect(fetchMock.mock.calls.filter(([path]) => path === "/health")).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(60_001);
    await backendFetch("/v1/credits");
    expect(fetchMock.mock.calls.filter(([path]) => path === "/health")).toHaveLength(2);
  });

  it("retoma uma leitura após falha temporária do proxy", async () => {
    let reads = 0;
    fetchMock.mockImplementation((path: string) => Promise.resolve(
      path === "/health" ? json({ status: "ok" }) : ++reads === 1
        ? new Response("Bad gateway", { status: 502 }) : json({ credits: 10 }),
    ));
    expect(await (await backendFetch("/v1/credits")).json()).toEqual({ credits: 10 });
    expect(reads).toBe(2);
    expect(fetchMock.mock.calls.filter(([path]) => path === "/health")).toHaveLength(2);
  });

  it("encerra a recuperação após duas leituras com falha", async () => {
    fetchMock.mockImplementation((path: string) => Promise.resolve(path === "/health"
      ? json({ status: "ok" }) : new Response(null, { status: 503 })));
    expect((await backendFetch("/v1/credits")).status).toBe(503);
    expect(fetchMock.mock.calls.filter(([path]) => path === "/v1/credits")).toHaveLength(2);
  });

  it.each([401, 422, 500])("não repete uma leitura com erro HTTP %s", async (status) => {
    fetchMock.mockImplementation((path: string) => Promise.resolve(json(
      path === "/health" ? { status: "ok" } : { detail: "Erro" }, path === "/health" ? 200 : status,
    )));
    expect((await backendFetch("/v1/credits")).status).toBe(status);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("não repete um POST após erro do proxy ou falha de rede ambígua", async () => {
    fetchMock.mockImplementation((path: string) => path === "/health"
      ? Promise.resolve(json({ status: "ok" })) : Promise.resolve(new Response(null, { status: 502 })));
    expect((await backendFetch("/v1/projects", { method: "POST" })).status).toBe(502);
    fetchMock.mockImplementation((path: string) => path === "/health"
      ? Promise.resolve(json({ status: "ok" })) : Promise.reject(new TypeError("Failed to fetch")));
    await expect(backendFetch("/v1/projects", { method: "POST" })).rejects.toThrow("Failed to fetch");
    expect(fetchMock.mock.calls.filter(([path]) => path === "/v1/projects")).toHaveLength(2);
  });

  it("cancelar uma chamada não interrompe outra aguardando o mesmo despertar", async () => {
    let resolveHealth!: (response: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveHealth = resolve; }));
    const controller = new AbortController();
    const cancelled = backendFetch("/v1/cancelled", { method: "POST", signal: controller.signal });
    const other = backendFetch("/v1/projects", { method: "POST" });
    const result = expect(cancelled).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await result;
    resolveHealth(json({ status: "ok" }));
    await other;
    expect(fetchMock.mock.calls.some(([path]) => path === "/v1/cancelled")).toBe(false);
  });

  it("o sinal do chamador não desativa o timeout da requisição", async () => {
    await warmBackend();
    fetchMock.mockImplementation((_path: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(new DOMException("Abort", "AbortError")), { once: true });
    }));
    const result = expect(backendFetch("/v1/projects", {
      method: "POST", signal: new AbortController().signal,
    }, 50)).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(50);
    await result;
  });

  it("mostra um aviso acessível apenas se o despertar demorar", async () => {
    render(<BackendStatus />);
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 }));
    const ready = warmBackend();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(1_500));
    expect(screen.getByRole("status")).toHaveTextContent(/preparando sua conexão/i);
    await act(async () => { await vi.advanceTimersByTimeAsync(500); await ready; });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("sessão durante indisponibilidade", () => {
  function expiredToken() {
    return `e30.${btoa(JSON.stringify({ sub: "u1", exp: Date.now() / 1000 - 10 }))}.sig`;
  }

  it("recupera um JWT que venceu enquanto a API estava acordando", async () => {
    const expiresAt = Date.now() + 10_000;
    setToken(`e30.${btoa(JSON.stringify({ sub: "u1", exp: expiresAt / 1000 }))}.sig`);
    fetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/health") return Promise.resolve(Date.now() < expiresAt + 2_000
        ? new Response(null, { status: 503 }) : json({ status: "ok" }));
      if (path === "/v1/auth/resume") return Promise.resolve(json({ access_token: "fresh-token" }));
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer fresh-token");
      return Promise.resolve(json({ id: "u1" }));
    });
    const me = api.me();
    await vi.advanceTimersByTimeAsync(12_000);
    await expect(me).resolves.toMatchObject({ id: "u1" });
    expect(getToken()).toBe("fresh-token");
  });

  it.each([429, 502, 503])("não apaga o JWT se o resume responde %s", async (status) => {
    const token = expiredToken();
    setToken(token);
    fetchMock.mockImplementation((path: string) => Promise.resolve(path === "/health"
      ? json({ status: "ok" }) : json({ detail: "Indisponível" }, status)));
    await expect(ensureSession()).rejects.toThrow(`${status}:`);
    expect(getToken()).toBe(token);
  });

  it("limpa o JWT quando o servidor confirma que ele é inválido", async () => {
    setToken(expiredToken());
    fetchMock.mockImplementation((path: string) => Promise.resolve(path === "/health"
      ? json({ status: "ok" }) : json({ detail: "Token inválido" }, 401)));
    await expect(ensureSession()).rejects.toThrow("401:");
    expect(getToken()).toBeNull();
  });
});
