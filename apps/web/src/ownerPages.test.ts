import { describe, expect, it } from "vitest";
import { OWNER_PAGES, applyOwnerPageMeta } from "./ownerPages";

const INDEX = `<!doctype html>
<html lang="pt-BR">
  <head>
    <title>Story R Us — Histórias Ilustradas Com A Foto Do Seu Filho</title>
    <meta name="description" content="Envie uma foto." />
    <link rel="canonical" href="https://storyrus.ai/" />
    <meta property="og:url" content="https://storyrus.ai/" />
    <meta property="og:title" content="Story R Us — Histórias Ilustradas Com A Foto Do Seu Filho" />
    <meta property="og:description" content="Uma foto vira personagem." />
    <meta name="twitter:title" content="Story R Us — Histórias Ilustradas Com A Foto Do Seu Filho" />
    <meta name="twitter:description" content="Transforme uma foto." />
  </head>
</html>`;

describe("títulos dos painéis do dono", () => {
  it("troca title e Open Graph em cada rota privada", () => {
    for (const page of OWNER_PAGES) {
      const html = applyOwnerPageMeta(INDEX, page);
      expect(html).toContain(`<title>${page.title}</title>`);
      expect(html).toContain(`property="og:title" content="${page.title}"`);
      expect(html).toContain(`property="og:description" content="${page.description}"`);
      expect(html).toContain(`property="og:url" content="https://storyrus.ai${page.path}"`);
      expect(html).toContain(`rel="canonical" href="https://storyrus.ai${page.path}"`);
      expect(html).toContain(`name="robots" content="noindex, nofollow"`);
      expect(html).not.toContain("Histórias Ilustradas Com A Foto Do Seu Filho");
    }
  });
});
