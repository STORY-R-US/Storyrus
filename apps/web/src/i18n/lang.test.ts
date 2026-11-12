import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import {
  detectCountryByIp,
  ipCountryUrl,
  langFromCountry,
  langFromNavigator,
  peekStoredLang,
  resolveInitialLang,
  writeStoredLang,
  useResolvedLang,
} from "./lang";

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("langFromCountry", () => {
  it("mapeia países PT / ES / demais", () => {
    expect(langFromCountry("BR")).toBe("pt");
    expect(langFromCountry("pt")).toBe("pt");
    expect(langFromCountry("MX")).toBe("es");
    expect(langFromCountry("ES")).toBe("es");
    expect(langFromCountry("US")).toBe("en");
    expect(langFromCountry("FR")).toBe("en");
    expect(langFromCountry("")).toBeNull();
    expect(langFromCountry("BRA")).toBeNull();
  });
});

describe("langFromNavigator", () => {
  it("lê prefixo do locale do browser", () => {
    expect(langFromNavigator("pt-BR")).toBe("pt");
    expect(langFromNavigator("es-MX")).toBe("es");
    expect(langFromNavigator("en-US")).toBe("en");
    expect(langFromNavigator("fr-FR")).toBeNull();
  });
});

describe("resolveInitialLang", () => {
  it("preferência salva vence o IP", async () => {
    writeStoredLang("es");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(resolveInitialLang()).resolves.toBe("es");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(peekStoredLang()).toBe("es");
  });

  it("usa país por IP quando não há storage", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        text: async () => "US\n",
      })),
    );
    await expect(resolveInitialLang()).resolves.toBe("en");
  });

  it("cai no navigator quando o IP falha", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("offline");
      }),
    );
    Object.defineProperty(navigator, "language", {
      configurable: true,
      value: "es-AR",
    });
    await expect(resolveInitialLang()).resolves.toBe("es");
  });
});

describe("detectCountryByIp", () => {
  it("chama ipapi.co/country/", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      text: async () => "BR",
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(detectCountryByIp()).resolves.toBe("BR");
    expect(fetchMock).toHaveBeenCalledWith(ipCountryUrl(), expect.anything());
  });
});

it("keeps the page and authentication provider in the same language without reloading", () => {
  writeStoredLang("pt");
  const page = renderHook(() => useResolvedLang());
  const provider = renderHook(() => useResolvedLang());
  act(() => page.result.current[1]("es"));
  expect(provider.result.current[0]).toBe("es");
  expect(document.documentElement.lang).toBe("es");
  act(() => provider.result.current[1]("en"));
  expect(page.result.current[0]).toBe("en");
  expect(peekStoredLang()).toBe("en");
});
