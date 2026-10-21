import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, resetStepIdempotencyState, setToken } from "./api";

describe("startStep Idempotency-Key", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    resetStepIdempotencyState();
    setToken("test-token");
    fetchMock.mockReset();
    vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) =>
      String(input) === "/health" ? jsonResponse({ status: "ok" }, 200) : fetchMock(input, init),
    );
    let n = 0;
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(() => {
      const id = String(++n).padStart(12, "0");
      return `00000000-0000-4000-8000-${id}`;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStepIdempotencyState();
    setToken(null);
  });

  function jsonResponse(body: unknown, status = 202) {
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }

  it("reusa a mesma chave e a mesma promise em cliques concorrentes", async () => {
    let resolveFetch!: (value: Response) => void;
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    );

    const p1 = api.startStep("proj-1", "avatar", {});
    const p2 = api.startStep("proj-1", "avatar", {});
    expect(p1).toBe(p2);

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.get("Idempotency-Key")).toBe("00000000-0000-4000-8000-000000000001");

    resolveFetch!(
      new Response(JSON.stringify({ job_id: "j1", estimated_cost_credits: 1 }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(p1).resolves.toEqual({ job_id: "j1", estimated_cost_credits: 1 });
    await expect(p2).resolves.toEqual({ job_id: "j1", estimated_cost_credits: 1 });
  });

  it("reusa a chave após falha de rede (retry sem double-debit)", async () => {
    fetchMock
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockImplementationOnce(() =>
        jsonResponse({ job_id: "j2", estimated_cost_credits: 1 }),
      );

    await expect(api.startStep("proj-1", "story", {})).rejects.toThrow(/Failed to fetch/);
    await expect(api.startStep("proj-1", "story", {})).resolves.toEqual({
      job_id: "j2",
      estimated_cost_credits: 1,
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const key1 = new Headers(fetchMock.mock.calls[0][1].headers).get("Idempotency-Key");
    const key2 = new Headers(fetchMock.mock.calls[1][1].headers).get("Idempotency-Key");
    expect(key1).toBe("00000000-0000-4000-8000-000000000001");
    expect(key2).toBe(key1);
  });

  it("emite chave nova após sucesso (próximo start intencional)", async () => {
    fetchMock
      .mockImplementationOnce(() =>
        jsonResponse({ job_id: "j1", estimated_cost_credits: 1 }),
      )
      .mockImplementationOnce(() =>
        jsonResponse({ job_id: "j2", estimated_cost_credits: 1 }),
      );

    await api.startStep("proj-1", "ebook", {});
    await api.startStep("proj-1", "ebook", {});

    const key1 = new Headers(fetchMock.mock.calls[0][1].headers).get("Idempotency-Key");
    const key2 = new Headers(fetchMock.mock.calls[1][1].headers).get("Idempotency-Key");
    expect(key1).toBe("00000000-0000-4000-8000-000000000001");
    expect(key2).toBe("00000000-0000-4000-8000-000000000002");
  });

  it("preserva a chave após 502 para reencontrar uma geração que já pode ter sido gravada", async () => {
    fetchMock
      .mockImplementationOnce(() => jsonResponse({ detail: "Bad gateway" }, 502))
      .mockImplementationOnce(() => jsonResponse({ job_id: "j-existing", estimated_cost_credits: 1 }));
    await expect(api.startStep("proj-1", "avatar", {})).rejects.toThrow("502:");
    await expect(api.startStep("proj-1", "avatar", {})).resolves.toMatchObject({ job_id: "j-existing" });
    const keys = fetchMock.mock.calls.map((call) => new Headers(call[1].headers).get("Idempotency-Key"));
    expect(keys[0]).toBe(keys[1]);
  });

  it("emite chave nova após erro HTTP definitivo", async () => {
    fetchMock
      .mockImplementationOnce(() =>
        jsonResponse({ detail: "créditos insuficientes" }, 402),
      )
      .mockImplementationOnce(() =>
        jsonResponse({ job_id: "j3", estimated_cost_credits: 1 }),
      );

    await expect(api.startStep("proj-1", "video", { duration_s: 5 })).rejects.toThrow(
      /402:/,
    );
    await api.startStep("proj-1", "video", { duration_s: 5 });

    const key1 = new Headers(fetchMock.mock.calls[0][1].headers).get("Idempotency-Key");
    const key2 = new Headers(fetchMock.mock.calls[1][1].headers).get("Idempotency-Key");
    expect(key1).toBe("00000000-0000-4000-8000-000000000001");
    expect(key2).toBe("00000000-0000-4000-8000-000000000002");
  });

  it("retenta 500 da prévia com a mesma Idempotency-Key", async () => {
    fetchMock
      .mockImplementationOnce(() => jsonResponse({ detail: "Erro interno" }, 500))
      .mockImplementationOnce(() =>
        jsonResponse({
          job_id: "preview-1",
          status: "PENDING",
          type: "AVATAR",
          estimated_cost_credits: 1,
        }),
      );

    await expect(api.startPreview("proj-1", { brief: "aventura" })).resolves.toMatchObject({
      job_id: "preview-1",
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const key1 = new Headers(fetchMock.mock.calls[0][1].headers).get("Idempotency-Key");
    const key2 = new Headers(fetchMock.mock.calls[1][1].headers).get("Idempotency-Key");
    expect(key1).toBe(key2);
  });

  it("isola chaves por projeto e por etapa", async () => {
    fetchMock.mockImplementation(() =>
      jsonResponse({ job_id: "j", estimated_cost_credits: 1 }),
    );

    await api.startStep("proj-a", "avatar", {});
    await api.startStep("proj-b", "avatar", {});
    await api.startStep("proj-a", "story", {});

    const keys = fetchMock.mock.calls.map((call) =>
      new Headers(call[1].headers).get("Idempotency-Key"),
    );
    expect(keys).toEqual([
      "00000000-0000-4000-8000-000000000001",
      "00000000-0000-4000-8000-000000000002",
      "00000000-0000-4000-8000-000000000003",
    ]);
  });
});
