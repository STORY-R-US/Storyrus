import assets from "./localizedExamples.json";
import type { Lang } from "./i18n/lang";

// Every entry starts from the approved PT image. Localizations replace its text,
// preserving the subject and scene; language never selects a different book.
const localized = assets as Record<string, { en: string; es: string }>;

export function localizedExample(reference: string, lang: Lang): string {
  if (!reference || lang === "pt") return reference;
  // Partial release: keep the exact PT scene until its lettering is localized.
  return localized[reference]?.[lang] || reference;
}
