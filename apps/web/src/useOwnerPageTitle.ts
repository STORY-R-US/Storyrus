import { OWNER_PAGES, type OwnerPage } from "./ownerPages";
import { usePageMeta } from "./pageMeta";

export { OWNER_PAGES, applyOwnerPageMeta } from "./ownerPages";
export type { OwnerPage } from "./ownerPages";

export function useOwnerPageTitle(path: OwnerPage["path"]) {
  const page = OWNER_PAGES.find((item) => item.path === path);
  usePageMeta(
    page
      ? {
          path: page.path,
          title: page.title,
          description: page.description,
          robots: "noindex, nofollow",
          sitemap: false,
          prerender: false,
        }
      : null,
  );
}
