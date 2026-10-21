/** Shared with landing via localStorage key `lang` (PT/EN/ES). */

import { useCallback, useEffect, useRef, useState } from "react";

export type Lang = "pt" | "en" | "es";

export const LANGS: Lang[] = ["pt", "en", "es"];

export const LANG_STORAGE_KEY = "lang";

const PT_COUNTRIES = new Set([
  "BR",
  "PT",
  "AO",
  "MZ",
  "CV",
  "GW",
  "ST",
  "TL",
]);

const ES_COUNTRIES = new Set([
  "ES",
  "MX",
  "AR",
  "CO",
  "CL",
  "PE",
  "UY",
  "PY",
  "VE",
  "EC",
  "GT",
  "BO",
  "CR",
  "PA",
  "DO",
  "HN",
  "SV",
  "NI",
  "CU",
  "PR",
]);

export function isLang(value: unknown): value is Lang {
  return value === "pt" || value === "en" || value === "es";
}

export function peekStoredLang(): Lang | null {
  try {
    const s = localStorage.getItem(LANG_STORAGE_KEY);
    if (isLang(s)) return s;
  } catch {
    /* ignore */
  }
  return null;
}

export function readStoredLang(fallback: Lang = "pt"): Lang {
  return peekStoredLang() ?? fallback;
}

export function writeStoredLang(lang: Lang): void {
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
}

export function htmlLangAttr(lang: Lang): string {
  return lang === "en" ? "en" : lang === "es" ? "es" : "pt-BR";
}

export function applyDocumentLang(lang: Lang): void {
  document.documentElement.lang = htmlLangAttr(lang);
}

export function langFromCountry(iso: string | null | undefined): Lang | null {
  if (!iso) return null;
  const code = iso.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return null;
  if (PT_COUNTRIES.has(code)) return "pt";
  if (ES_COUNTRIES.has(code)) return "es";
  return "en";
}

export function langFromNavigator(navLang?: string | null): Lang | null {
  const fromArg = navLang ?? null;
  const fromNav =
    typeof navigator !== "undefined" ? navigator.language : "";
  const raw = (fromArg || fromNav || "").toLowerCase();
  if (!raw) return null;
  if (raw.startsWith("pt")) return "pt";
  if (raw.startsWith("es")) return "es";
  if (raw.startsWith("en")) return "en";
  return null;
}

export function ipCountryUrl(): string {
  return "https://ipapi.co/country/";
}

export async function detectCountryByIp(signal?: AbortSignal): Promise<string | null> {
  const resp = await fetch(ipCountryUrl(), { signal });
  if (!resp.ok) return null;
  const text = (await resp.text()).trim().toUpperCase();
  return /^[A-Z]{2}$/.test(text) ? text : null;
}

/** Preferência salva > país por IP > navigator.language > pt. */
export async function resolveInitialLang(signal?: AbortSignal): Promise<Lang> {
  const stored = peekStoredLang();
  if (stored) return stored;
  try {
    const country = await detectCountryByIp(signal);
    const fromIp = langFromCountry(country);
    if (fromIp) return fromIp;
  } catch {
    /* rede / abort */
  }
  return langFromNavigator() ?? "pt";
}

/**
 * Idioma da UI: usa storage se existir; na primeira visita detecta por IP
 * (e grava). Troca manual também grava e não é sobrescrita.
 */
export function useResolvedLang(): [Lang, (lang: Lang) => void] {
  const [lang, setLangState] = useState<Lang>(() => readStoredLang("pt"));
  const locked = useRef(peekStoredLang() !== null);

  useEffect(() => {
    applyDocumentLang(lang);
    if (locked.current) writeStoredLang(lang);
  }, [lang]);

  useEffect(() => {
    if (locked.current) return;
    const ctrl = new AbortController();
    void resolveInitialLang(ctrl.signal)
      .then((next) => {
        if (ctrl.signal.aborted || locked.current) return;
        locked.current = true;
        writeStoredLang(next);
        setLangState(next);
        applyDocumentLang(next);
      })
      .catch(() => {
        if (ctrl.signal.aborted || locked.current) return;
        locked.current = true;
        const next = langFromNavigator() ?? "pt";
        writeStoredLang(next);
        setLangState(next);
        applyDocumentLang(next);
      });
    return () => ctrl.abort();
  }, []);

  const setLang = useCallback((next: Lang) => {
    locked.current = true;
    writeStoredLang(next);
    setLangState(next);
    applyDocumentLang(next);
  }, []);

  return [lang, setLang];
}
