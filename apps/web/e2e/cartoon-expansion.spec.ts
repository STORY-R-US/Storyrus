import { expect, test } from "./fixtures";
import { TEST_SESSION_TOKEN } from "./session";

const books = [[27, "heroi-policia", "cartoon"], [26, "heroi-bombeiro", "cartoon"], [25, "construtor", "cartoon"], [24, "esther-higiene", "cartoon"], [15, "rebeca", "cartoon"], [14, "raquel-papai", "cartoon"], [2, "antonio-bicicleta", "cartoon"], [1, "emilia-bailarina", "cartoon"], [0, "martin-goleiro", "cartoon"], [18, "noe", "cartoon"], [60, "enzo-dinossauro", "cartoon"], [21, "meupai-heroi", "cartoon"], [9, "natal", "cartoon"], [10, "nano", "cartoon"], [62, "sofia-princesa", "cartoon"], [62, "sofia-princesa", "realistic"], [63, "lia-cores", "cartoon"], [63, "lia-cores", "realistic"], [64, "bento-compartilhar", "cartoon"], [64, "bento-compartilhar", "realistic"], [65, "nina-boa-noite", "cartoon"], [65, "nina-boa-noite", "realistic"], [66, "theo-sentimentos", "cartoon"], [66, "theo-sentimentos", "realistic"], [67, "clara-miguel-casamento", "cartoon"], [67, "clara-miguel-casamento", "realistic"]] as const;

for (const lang of ["pt", "en", "es"]) {
  for (const width of [390, 1440]) {
    test(`new Cartoon books keep localized scenes and square covers in ${lang} at ${width}px`, async ({ page }) => {
      test.setTimeout(90_000);
      await page.setViewportSize({ width, height: 950 });
      await page.addInitScript(({ lang, token }) => {
        localStorage.setItem("lang", lang);
        localStorage.setItem("storyrus_token", token);
      }, { lang, token: TEST_SESSION_TOKEN });
      await page.route("**/v1/**", route => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith("/auth/me")) return route.fulfill({ json: {
          id: "cartoon-test", email: "cartoon@example.test", is_guest: false,
          email_verified: true, terms_accepted_at: "2026-10-30", adult_confirmed_at: "2026-10-30",
          full_name: "Ana", phone: "11999999999", street: "Rua de Teste", number: "1",
          city: "São Paulo", postal_code: "01310100", state: "SP", country: "BR", credits: 10,
        } });
        if (path.endsWith("/credits")) return route.fulfill({ json: { credits: 10 } });
        return route.fulfill({ json: [] });
      });
      let expectedCoverWidth = 0;
      for (const [index, slug, style] of books) {
        await page.goto(`/livro/${index}${style === "cartoon" ? "?modo=cartoon" : ""}`);
        const gallery = page.getByTestId("book-series");
        const image = gallery.locator("img");
        await expect(gallery.getByRole("tab")).toHaveCount(3);
        for (const [position, role] of ["capa", "pagina", "foto"].entries()) {
          await gallery.getByRole("tab").nth(position).click();
          await expect(image).toHaveAttribute("src", `/exemplos/${position === 0 ? "covers/" : ""}${style}-${role}-${slug}-v1-${lang}.webp`);
          await image.evaluate(async el => { await (el as HTMLImageElement).decode(); await new Promise(requestAnimationFrame); });
          await expect.poll(() => image.evaluate(el => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
          const ratio = await image.evaluate(el => (el as HTMLImageElement).naturalWidth / (el as HTMLImageElement).naturalHeight);
          expect(ratio).toBeCloseTo(position === 1 ? 2 : 1, 2);
          if (position === 0) {
            const box = (await image.boundingBox())!;
            expect(Math.abs(box.width - box.height)).toBeLessThan(1);
            if (expectedCoverWidth) expect(Math.abs(box.width - expectedCoverWidth)).toBeLessThan(1);
            expectedCoverWidth = box.width;
          } else {
            expect(await image.evaluate(el => getComputedStyle(el).objectFit)).toBe("contain");
          }
          expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
          if (position === 1) {
            const bounds = (await image.boundingBox())!;
            const artworkBottom = bounds.y + (bounds.height + bounds.width / ratio) / 2;
            for (const arrow of await gallery.locator(".cat-flip-nav").all()) {
              expect((await arrow.boundingBox())!.y).toBeGreaterThan(artworkBottom);
            }
          }
          if (position === 1) await gallery.screenshot({ path: `test-results/${style}-${index}-${lang}-${width}-open.png` });
        }
        await gallery.getByRole("tab").first().click();
        await image.evaluate(async el => { await (el as HTMLImageElement).decode(); await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
        if (lang === "pt") await page.screenshot({ path: `test-results/${style}-${index}-${width}-page.png`, fullPage: true });
        const personalize = page.getByTestId("landing-personalize");
        await expect(personalize).toHaveAttribute("href", new RegExp(`modelo=catalog-${style}-${index}`));
        await personalize.click();
        await expect(page.getByTestId("studio-selected-catalog-model")).toBeVisible();
        await expect(page).toHaveURL(new RegExp(`modelo=catalog-${style}-${index}`));
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      }
    });
  }
}
