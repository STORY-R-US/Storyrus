import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, setToken } from "./api";

describe("painéis do dono: JSON com Content-Type", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    setToken("test-token");
    fetchMock.mockReset();
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ id: "pedido-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) =>
      String(input) === "/health"
        ? Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200, headers: { "Content-Type": "application/json" } }))
        : fetchMock(input, init),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    setToken(null);
  });

  it("Salvar pedido manda o corpo como application/json", async () => {
    await api.updateOrder(null, "pedido-1", { payment_status: "paid" });
    const call = fetchMock.mock.calls.find(([url]) => String(url).includes("/v1/usage/orders/pedido-1"));
    expect(call).toBeDefined();
    const init = call![1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init.body))).toEqual({ payment_status: "paid" });
  });

  it("DELETE sem corpo não ganha Content-Type", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(new Response(null, { status: 204 })));
    await api.deleteOrder(null, "pedido-1");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });
});
