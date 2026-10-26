import { afterEach, describe, expect, it, vi } from "vitest";
import {
  api,
  ensureSession,
  getToken,
  restoreClerkSessionFromStorage,
  sessionTokenFromStorage,
  setClerkGetToken,
  setToken,
} from "./api";

describe("sessão do Clerk", () => {
  afterEach(() => {
    setToken(null);
    setClerkGetToken(null);
    vi.unstubAllGlobals();
  });

  it("segue quando já há um token de teste", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setToken("e2e-token");
    await expect(ensureSession()).resolves.toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(getToken()).toBe("e2e-token");
  });

  it("pede 401 quando não há sessão", async () => {
    setToken(null);
    await expect(ensureSession()).rejects.toThrow("401:");
  });

  it("usa o token do Clerk quando o teste não gravou um Bearer", async () => {
    setToken(null);
    setClerkGetToken(async () => "clerk-session");
    await expect(ensureSession()).resolves.toBeUndefined();
    expect(getToken()).toBe("clerk-session");
  });

  it("ignora o token antigo da senha e usa a sessão do Clerk", async () => {
    const oldPayload = btoa(JSON.stringify({ sub: "8c1c0b2e-1111-2222-3333-444455556666" }))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
    localStorage.setItem("storyrus_token", `header.${oldPayload}.sig`);
    restoreClerkSessionFromStorage();
    setClerkGetToken(async () => "clerk-session");
    await expect(ensureSession()).resolves.toBeUndefined();
    expect(getToken()).toBe("clerk-session");
    expect(sessionTokenFromStorage(localStorage.getItem("storyrus_token"))).toBeNull();
  });

  it("esquece o Bearer quando a API recusa a sessão", async () => {
    setToken("stale-token");
    vi.stubGlobal("fetch", vi.fn(async (path: string) => {
      if (path === "/health") {
        return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
      }
      return new Response(JSON.stringify({ detail: "Sessão inválida" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }));
    await expect(api.me()).rejects.toThrow("401:");
    expect(getToken()).toBeNull();
  });
});
