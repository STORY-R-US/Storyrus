import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { resetStepIdempotencyState, setToken } from "../api";
import { resetBackendConnectionForTests } from "../backendConnection";
import { resetClerkState } from "./clerkState";
import { server, state } from "./server";

vi.mock("@clerk/react", async () => {
  const React = await import("react");
  const { clerkState } = await import("./clerkState");
  return {
    ClerkProvider: ({ children }: { children: React.ReactNode }) => children,
    useAuth: () => ({
      isLoaded: clerkState.isLoaded,
      isSignedIn: clerkState.isSignedIn,
      getToken: async () => (clerkState.isSignedIn ? "clerk-session" : null),
      signOut: async () => {
        clerkState.isSignedIn = false;
      },
    }),
    SignIn: (props: { path?: string }) =>
      React.createElement("div", { "data-testid": "clerk-sign-in", "data-path": props.path }),
    SignUp: (props: { path?: string }) =>
      React.createElement("div", { "data-testid": "clerk-sign-up", "data-path": props.path }),
  };
});

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
  resetClerkState();
  resetStepIdempotencyState();
  resetBackendConnectionForTests();
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
});
afterAll(() => server.close());
