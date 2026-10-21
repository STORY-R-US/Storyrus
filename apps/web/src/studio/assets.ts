export type StudioAssets = {
  character_url: string | null;
  realistic_url: string | null;
  extra_characters: { name: string; url: string }[];
  page_images: string[];
  cover_url?: string | null;
  in_hand_url?: string | null;
  generic_images?: boolean;
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url: string | null;
};

export function mergeStudioAssets(prev: StudioAssets | null, next: StudioAssets): StudioAssets {
  if (!prev) return next;
  const prevPages = prev.page_images ?? [];
  const nextPages = next.page_images ?? [];
  return {
    ...next,
    page_images: nextPages.length === prevPages.length ? prevPages : nextPages,
    cover_url: next.cover_url ?? prev.cover_url ?? null,
    in_hand_url: next.in_hand_url ?? prev.in_hand_url ?? null,
    generic_images: next.generic_images ?? prev.generic_images,
  };
}
