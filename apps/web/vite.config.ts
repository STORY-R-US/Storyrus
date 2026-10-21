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

function frameSave(): Plugin {
  return {
    name: "frame-save",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/__enquadre", (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.end();
          return;
        }
        const chunks: Buffer[] = [];
        req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
        req.on("end", () => {
          try {
            const body = JSON.parse(Buffer.concat(chunks).toString("utf8")) as { file?: string; png?: string };
            const allow = new Set(["dica-boa.png", "dica-multi.png"]);
            if (!body.file || !allow.has(body.file) || typeof body.png !== "string") throw new Error("bad");
            const buf = Buffer.from(body.png.replace(/^data:image\/png;base64,/, ""), "base64");
            if (buf.length < 1000 || buf.length > 8_000_000) throw new Error("size");
            writeFileSync(resolve(server.config.root, "public/exemplos", body.file), buf);
            res.setHeader("content-type", "application/json");
            res.end(JSON.stringify({ ok: true }));
          } catch {
            res.statusCode = 400;
            res.setHeader("content-type", "application/json");
            res.end(JSON.stringify({ ok: false }));
          }
        });
      });
    },
  };
}

export default defineConfig({
  cacheDir: ".vite",
  plugins: [react(), routeHtml(), frameSave()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/v1": apiTarget,
      "/health": apiTarget,
    },
  },
});
