import assets from "./localizedExamples.json";
import coverFormats from "./coverFormats.json";
import type { Lang } from "./i18n/lang";

// Every entry starts from the approved PT image. Localizations replace its text,
// preserving the subject and scene; language never selects a different book.
const localized = assets as Record<string, { en: string; es: string }>;

export function localizedExample(reference: string, lang: Lang): string {
  if (!reference) return reference;
  const file = lang === "pt" ? reference : localized[reference]?.[lang] || reference;
  // Cover variants share the approved square book format; originals are retained.
  return (coverFormats as Record<string, string>)[file] || file;
}
