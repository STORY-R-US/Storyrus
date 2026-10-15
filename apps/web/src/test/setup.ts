import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { resetStepIdempotencyState, setToken } from "../api";
import { resetBackendConnectionForTests } from "../backendConnection";
import { server, state } from "./server";

// crypto.randomUUID em ambiente de teste (caso o jsdom não exponha).
if (!globalThis.crypto?.randomUUID) {
  // @ts-expect-error polyfill simples para os testes
  globalThis.crypto = { ...globalThis.crypto, randomUUID: () => `uuid-${Math.random()}` };
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  // Node 24's fetch rejects jsdom's AbortSignal. Drop that signal so IP
  // detection still hits the MSW handler instead of falling back to en-US.
  const fetchImpl = globalThis.fetch.bind(globalThis);
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    if (!init?.signal) return fetchImpl(input, init);
    try {
      return await fetchImpl(input, init);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (init.signal.aborted || !message.includes("AbortSignal")) throw err;
      const { signal: _signal, ...rest } = init;
      return fetchImpl(input, rest);
    }
  }) as typeof fetch;
});
afterEach(() => {
  server.resetHandlers();
  state.reset();
  setToken(null);
  resetStepIdempotencyState();
  resetBackendConnectionForTests();
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
});
afterAll(() => server.close());
