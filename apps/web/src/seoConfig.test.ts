import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function readJson(path: string) {
  return JSON.parse(readFileSync(path, "utf8")) as {
    rewrites?: { source: string; destination: string }[];
    headers?: { headers: { key: string; value: string }[] }[];
    cleanUrls?: boolean;
  };
}

describe("vercel e robots", () => {
  it("não reescreve rotas desconhecidas para o index e publica CSP", () => {
    for (const path of [
      resolve(process.cwd(), "vercel.json"),
      resolve(process.cwd(), "../../vercel.json"),
    ]) {
      const config = readJson(path);
      expect(config.cleanUrls).toBe(true);
      const catchAll = (config.rewrites ?? []).some(
        (rule) => rule.source === "/(.*)" && rule.destination === "/index.html",
      );
      expect(catchAll).toBe(false);
      const headers = (config.headers ?? []).flatMap((block) => block.headers);
      expect(headers.some((header) => header.key === "Access-Control-Allow-Origin")).toBe(false);
      const csp = headers.find((header) => header.key === "Content-Security-Policy-Report-Only");
      expect(csp?.value).toContain("default-src 'self'");
      expect(csp?.value).toContain("https://fonts.googleapis.com");
      expect(csp?.value).toContain("https://viacep.com.br");
      expect(csp?.value).toContain("https://api.zippopotam.us");
      expect(csp?.value).toContain("https://ipapi.co");
    }
  });

  it("não lista os painéis admin no robots.txt", () => {
    const robots = readFileSync(resolve(process.cwd(), "public/robots.txt"), "utf8");
    expect(robots).not.toMatch(/Disallow:\s*\/gastos/);
    expect(robots).not.toMatch(/Disallow:\s*\/pedidos/);
    expect(robots).not.toMatch(/Disallow:\s*\/usuarios/);
    expect(robots).toContain("Sitemap: https://storyrus.ai/sitemap.xml");
  });
});
