import type { StudioCopy } from "./i18n";

export const ART_STYLE_KEY = "realistic" as const;

/** Exibe o tema salvo no projeto (texto livre ou legado). */
export const resolveThemeName = (
  id: string | null | undefined,
  themes: StudioCopy["themes"],
  empty = "—",
) => {
  const raw = (id ?? "").trim();
  if (!raw) return empty;
  if (raw in themes) return themes[raw as keyof typeof themes];
  return raw;
};

/** Etapas finais (dependem de personagem + história). */
export function studioSteps(t: StudioCopy): {
  key: "ebook" | "video" | "narrated-video";
  label: string;
  hint: string;
}[] {
  return [
    {
      key: "ebook",
      label: t.stepEbook,
      hint: t.stepEbookHint,
    },
    {
      key: "video",
      label: t.stepVideo,
      hint: t.stepVideoHint,
    },
    {
      key: "narrated-video",
      label: t.stepNarrated,
      hint: t.stepNarratedHint,
    },
  ];
}
