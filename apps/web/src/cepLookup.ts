import { useEffect, useRef, useState } from "react";

export type CepAddress = {
  postal_code: string;
  street: string;
  district: string;
  city: string;
  state: string;
};

export type CepStatus = "idle" | "loading" | "ok" | "miss" | "error";

export function supportsPostalLookup(country: string): boolean {
  return country === "BR" || country === "US";
}

export function digitsCep(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 8);
}

export function digitsZip(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 5);
}

export function formatCep(raw: string): string {
  const digits = digitsCep(raw);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

export function formatPostal(raw: string, country: string): string {
  if (country === "BR") return formatCep(raw);
  if (country === "US") return digitsZip(raw);
  return raw;
}

export function viaCepUrl(cep: string): string {
  return `https://viacep.com.br/ws/${digitsCep(cep)}/json/`;
}

export function zippopotamUrl(zip: string): string {
  return `https://api.zippopotam.us/us/${digitsZip(zip)}`;
}

async function lookupBrCep(raw: string, signal?: AbortSignal): Promise<CepAddress | null> {
  const cep = digitsCep(raw);
  if (cep.length !== 8) return null;
  const resp = await fetch(viaCepUrl(cep), { signal });
  if (!resp.ok) {
    throw new Error(`cep_http_${resp.status}`);
  }
  const data = (await resp.json()) as {
    erro?: boolean;
    logradouro?: string;
    bairro?: string;
    localidade?: string;
    uf?: string;
  };
  if (data?.erro) return null;
  return {
    postal_code: formatCep(cep),
    street: String(data.logradouro || "").trim(),
    district: String(data.bairro || "").trim(),
    city: String(data.localidade || "").trim(),
    state: String(data.uf || "").trim().toUpperCase(),
  };
}

async function lookupUsZip(raw: string, signal?: AbortSignal): Promise<CepAddress | null> {
  const zip = digitsZip(raw);
  if (zip.length !== 5) return null;
  const resp = await fetch(zippopotamUrl(zip), { signal });
  if (resp.status === 404) return null;
  if (!resp.ok) {
    throw new Error(`zip_http_${resp.status}`);
  }
  const data = (await resp.json()) as {
    "post code"?: string;
    places?: Array<{
      "place name"?: string;
      "state abbreviation"?: string;
      state?: string;
    }>;
  };
  const place = data.places?.[0];
  if (!place) return null;
  return {
    postal_code: zip,
    street: "",
    district: "",
    city: String(place["place name"] || "").trim(),
    state: String(place["state abbreviation"] || "").trim().toUpperCase(),
  };
}

/** Busca endereço por CEP (BR) ou ZIP (US). */
export async function lookupCep(
  raw: string,
  signal?: AbortSignal,
  country = "BR",
): Promise<CepAddress | null> {
  if (country === "US") return lookupUsZip(raw, signal);
  if (country === "BR") return lookupBrCep(raw, signal);
  return null;
}

/** Busca ViaCEP / Zippopotam quando o código postal está completo. */
export function useCepLookup(
  postalCode: string,
  enabled: boolean,
  onAddress: (addr: CepAddress) => void,
  country = "BR",
): CepStatus {
  const [status, setStatus] = useState<CepStatus>("idle");
  const lastKey = useRef("");
  const onAddressRef = useRef(onAddress);
  onAddressRef.current = onAddress;

  useEffect(() => {
    if (!enabled || !supportsPostalLookup(country)) {
      lastKey.current = "";
      setStatus("idle");
      return;
    }
    const digits = country === "US" ? digitsZip(postalCode) : digitsCep(postalCode);
    const need = country === "US" ? 5 : 8;
    if (digits.length !== need) {
      lastKey.current = "";
      setStatus("idle");
      return;
    }
    const key = `${country}:${digits}`;
    if (lastKey.current === key) return;
    lastKey.current = key;
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      setStatus("loading");
      void lookupCep(digits, ctrl.signal, country)
        .then((addr) => {
          if (ctrl.signal.aborted) return;
          if (!addr) {
            setStatus("miss");
            return;
          }
          onAddressRef.current(addr);
          setStatus("ok");
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === "AbortError") return;
          setStatus("error");
        });
    }, 280);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
  }, [enabled, postalCode, country]);

  return status;
}
