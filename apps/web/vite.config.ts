import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { parsePtCatalog } from "./src/catalogSeo";
import { OWNER_PAGES } from "./src/ownerPages";
import {
  applyPageMeta,
  htmlFileForPath,
  NOT_FOUND_PAGE,
  publicHtmlPages,
  renderSitemap,
  type HtmlPage,
} from "./src/pageMeta";

// Alvo do proxy configurável: localhost em dev, http://api:8000 no docker-compose.
const apiTarget = process.env.VITE_API_PROXY ?? "http://localhost:8000";

function routeHtml(): Plugin {
  let outDir = "dist";
  let root = ".";
  return {
    name: "route-html",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
      root = config.root;
    },
    closeBundle() {
      const indexPath = resolve(outDir, "index.html");
      if (!existsSync(indexPath)) return;
      const index = readFileSync(indexPath, "utf8");
      const landing = readFileSync(resolve(root, "src/Landing.tsx"), "utf8");
      const books = parsePtCatalog(landing);
      const pages: HtmlPage[] = [
        ...publicHtmlPages(books),
        ...OWNER_PAGES.map((page) => ({
          path: page.path,
          title: page.title,
          description: page.description,
          robots: "noindex, nofollow",
          sitemap: false,
          prerender: false,
        })),
      ];
      for (const page of pages) {
        const file = resolve(outDir, htmlFileForPath(page.path));
        mkdirSync(dirname(file), { recursive: true });
        writeFileSync(file, applyPageMeta(index, page));
      }
      writeFileSync(resolve(outDir, "404.html"), applyPageMeta(index, NOT_FOUND_PAGE));
      writeFileSync(
        resolve(outDir, "sitemap.xml"),
        renderSitemap(pages.filter((page) => page.sitemap)),
      );
    },
  };
}

export default defineConfig({
  plugins: [react(), routeHtml()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/v1": apiTarget,
      "/health": apiTarget,
    },
  },
});
