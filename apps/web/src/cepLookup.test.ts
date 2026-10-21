import { afterEach, describe, expect, it, vi } from "vitest";
import {
  digitsCep,
  digitsZip,
  formatCep,
  formatPostal,
  lookupCep,
  supportsPostalLookup,
  viaCepUrl,
  zippopotamUrl,
} from "./cepLookup";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("cepLookup", () => {
  it("normaliza e formata CEP / ZIP", () => {
    expect(digitsCep("01310-100")).toBe("01310100");
    expect(digitsCep("01310 100 extra")).toBe("01310100");
    expect(formatCep("01310100")).toBe("01310-100");
    expect(formatCep("01310")).toBe("01310");
    expect(viaCepUrl("01310-100")).toBe("https://viacep.com.br/ws/01310100/json/");
    expect(digitsZip("90210-1234")).toBe("90210");
    expect(formatPostal("90210", "US")).toBe("90210");
    expect(formatPostal("01310100", "BR")).toBe("01310-100");
    expect(zippopotamUrl("90210")).toBe("https://api.zippopotam.us/us/90210");
    expect(supportsPostalLookup("BR")).toBe(true);
    expect(supportsPostalLookup("US")).toBe(true);
    expect(supportsPostalLookup("MX")).toBe(false);
  });

  it("preenche rua, bairro, cidade e UF", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        cep: "01310-100",
        logradouro: "Avenida Paulista",
        bairro: "Bela Vista",
        localidade: "São Paulo",
        uf: "SP",
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const addr = await lookupCep("01310-100");
    expect(addr).toEqual({
      postal_code: "01310-100",
      street: "Avenida Paulista",
      district: "Bela Vista",
      city: "São Paulo",
      state: "SP",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://viacep.com.br/ws/01310100/json/",
      expect.objectContaining({ signal: undefined }),
    );
  });

  it("preenche cidade e estado a partir do ZIP americano", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        "post code": "90210",
        country: "United States",
        places: [
          {
            "place name": "Beverly Hills",
            longitude: "-118.4065",
            state: "California",
            "state abbreviation": "CA",
            latitude: "34.0901",
          },
        ],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const addr = await lookupCep("90210", undefined, "US");
    expect(addr).toEqual({
      postal_code: "90210",
      street: "",
      district: "",
      city: "Beverly Hills",
      state: "CA",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.zippopotam.us/us/90210",
      expect.objectContaining({ signal: undefined }),
    );
  });

  it("devolve null quando o CEP não existe", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ erro: true }),
      })),
    );
    expect(await lookupCep("00000000")).toBeNull();
  });

  it("devolve null quando o ZIP americano não existe", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({}),
      })),
    );
    expect(await lookupCep("00000", undefined, "US")).toBeNull();
  });

  it("não chama a API com CEP incompleto", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await lookupCep("01310")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("não chama a API com ZIP incompleto", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await lookupCep("902", undefined, "US")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
