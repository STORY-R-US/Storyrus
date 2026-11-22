import { expect, test } from "./fixtures";
import { TEST_SESSION_TOKEN } from "./session";

for (const lang of ["pt", "en", "es"]) {
  for (const width of [390, 1440]) {
    test(`photo steps and retired book in ${lang} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 950 });
      await page.addInitScript(({ lang, token }) => {
        localStorage.setItem("lang", lang);
        localStorage.setItem("storyrus_token", token);
      }, { lang, token: TEST_SESSION_TOKEN });
      await page.route("**/v1/**", route => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith("/auth/me")) return route.fulfill({ json: {
          id: "photo-steps-test", email: "ana@example.test", is_guest: false,
          email_verified: true, terms_accepted_at: "2026-10-30", adult_confirmed_at: "2026-10-30",
          full_name: "Ana", phone: "11999999999", street: "Rua de Teste", number: "1",
          city: "São Paulo", postal_code: "01310100", state: "SP", country: "BR", credits: 10,
        } });
        if (path.endsWith("/credits")) return route.fulfill({ json: { credits: 10 } });
        return route.fulfill({ json: [] });
      });
      for (const path of ["/", "/app"]) {
        await page.goto(path);
        const steps = page.locator("#passo");
        await expect(steps.locator("figure")).toHaveCount(3);
        const images = steps.locator("img");
        await images.evaluateAll(items => items.forEach(item => (item as HTMLImageElement).loading = "eager"));
        await expect.poll(() => images.evaluateAll(items => items.every(item => (item as HTMLImageElement).naturalWidth > 0))).toBe(true);
        const sources = await images.evaluateAll(items => items.map(item => item.getAttribute("src")));
        expect(sources[0]).toContain(path === "/" ? "passo-meupai-protagonista-v3.png" : "passo-protagonista-v2.webp");
        expect(sources[1]).toContain(path === "/" ? "passo-meupai-familia-v3.png" : "passo-familia-v2.webp");
        expect(sources[2]).toContain(path === "/" ? "capa-meupai-heroi" : "capa-mamaepapaimatteo");
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await steps.screenshot({ path: `test-results/photo-steps-${path === "/" ? "home" : "studio"}-${lang}-${width}.png` });
        await expect(page.getByRole("searchbox")).toHaveCount(0);
      }
      await page.goto("/catalogo");
      while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
      await expect(page.locator('a[href="/livro/61"]')).toHaveCount(0);
      await expect(page.getByRole("searchbox")).toHaveCount(0);
      await page.goto("/livro/61");
      await expect(page.getByTestId("book-series")).toHaveCount(0);
    });
  }
}
