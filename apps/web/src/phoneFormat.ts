import { regionProfile } from "./signupRegions";

/** Código de discagem (DDI) dos países do cadastro. */
const DIAL_CODES: Record<string, string> = {
  BR: "55", US: "1", CA: "1", MX: "52", AR: "54", CL: "56", CO: "57", PE: "51", UY: "598",
  PY: "595", BO: "591", EC: "593", VE: "58", CR: "506", PA: "507", DO: "1", GT: "502",
  PT: "351", ES: "34", FR: "33", IT: "39", DE: "49", GB: "44",
};

export function dialCode(country: string): string | null {
  return DIAL_CODES[country.toUpperCase()] ?? null;
}

/** Formato nacional: os dígitos do exemplo viram posições a preencher. */
function nationalMask(country: string, digits: number): string | null {
  const code = country.toUpperCase();
  if (code === "BR") return digits > 10 ? "(00) 00000-0000" : "(00) 0000-0000";
  const sample = regionProfile(code).phonePlaceholder;
  return sample.startsWith("+") ? null : sample;
}

function applyMask(mask: string, digits: string): string {
  let out = "";
  let pending = "";
  let used = 0;
  for (const ch of mask) {
    if (used >= digits.length) break;
    if (/\d/.test(ch)) {
      out += pending + digits[used];
      pending = "";
      used += 1;
    } else {
      pending += ch;
    }
  }
  return out + digits.slice(used);
}

function nationalDigits(raw: string, country: string): string {
  const dial = dialCode(country);
  let digits = raw.replace(/\D/g, "");
  if (!dial) return digits;
  if (raw.trimStart().startsWith("+")) {
    if (digits.startsWith(dial)) digits = digits.slice(dial.length);
    else if (dial.startsWith(digits)) return "";
  }
  // Número colado com o código do país e sem o "+": sobra dígito para o formato nacional.
  const mask = nationalMask(country, 99);
  const slots = mask ? mask.replace(/\D/g, "").length : 0;
  return slots > 0 && digits.length > slots && digits.startsWith(dial) ? digits.slice(dial.length) : digits;
}

/** Exemplo do campo, já com o código do país: "+55 (11) 99999-9999". */
export function phonePlaceholder(country: string): string {
  const dial = dialCode(country);
  const sample = regionProfile(country.toUpperCase()).phonePlaceholder;
  return dial && !sample.startsWith("+") ? `+${dial} ${sample}` : sample;
}

/** Telefone no formato do país, com o código de discagem na frente. */
export function formatPhone(raw: string, country: string): string {
  const clean = raw.replace(/[^\d+()\-\s]/g, "").slice(0, 32);
  const dial = dialCode(country);
  if (!dial) return clean;
  const digits = nationalDigits(clean, country).slice(0, 15);
  if (!digits) return clean.trimStart();
  const mask = nationalMask(country, digits.length);
  return `+${dial} ${mask ? applyMask(mask, digits) : digits}`;
}

/** Ao trocar o país, mantém o número e troca o formato e o código. */
export function reformatPhone(value: string, fromCountry: string, toCountry: string): string {
  const digits = nationalDigits(value, fromCountry);
  if (!digits) return "";
  return formatPhone(digits, toCountry);
}
