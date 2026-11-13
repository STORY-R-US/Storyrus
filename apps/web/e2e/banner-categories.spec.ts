import { expect, test } from "./fixtures";

for (const lang of ["pt", "en", "es"]) {
  for (const width of [390, 1440]) {
    test(`banner categories match their books in ${lang} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(value => localStorage.setItem("lang", value), lang);
      await page.goto("/");
      const mobile = width < 1321;
      if (mobile) {
        await page.getByTestId("landing-menu").click();
        await page.locator(".kmobile-cat-toggle").first().click();
      } else {
        await page.locator(".kcats .kcat-btn").first().hover();
      }
      const panel = mobile ? page.getByTestId("landing-site-menu") : page.locator("#cat-panel");
      const dinosaurs = panel.locator('a[href="/catalogo#aventuras-dinosaurs"]').first();
      if (mobile) await dinosaurs.locator("..").getByRole("button").click();
      else await dinosaurs.hover();
      const feats = mobile ? dinosaurs.locator("../..").locator(".kmobile-feats") : page.getByTestId("landing-cat-feats");
      await expect(feats.locator(".kcat-feat")).toHaveCount(2);
      for (const id of [18, 60]) await expect(feats.locator(`a[href="/livro/${id}"]`)).toBeVisible();
      await expect.poll(() => feats.locator("img").evaluateAll(images => images.every(img => (img as HTMLImageElement).naturalWidth > 0))).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (lang === "pt") await page.screenshot({ path: `test-results/banner-dinosaurs-${width}.png` });
      await dinosaurs.click();
      await expect(page.getByTestId("catalog-category")).toHaveValue("aventuras-dinosaurs");
      await expect(page.getByTestId("landing-catalog-card")).toHaveCount(2);
      await page.locator('a.cat-book-link[href="/livro/60"]').click();
      await expect(page.getByTestId("book-series-cover")).toBeVisible();

      // The Cartoon menu must neither advertise empty themes nor switch artwork style.
      await page.goto("/cartoon");
      if (mobile) {
        await page.getByTestId("landing-menu").click();
        await page.locator(".kmobile-cat-toggle").first().click();
      } else await page.locator(".kcats .kcat-btn").first().hover();
      const cartoonDinosaurs = panel.locator('a[href="/catalogo?modo=cartoon#aventuras-dinosaurs"]').first();
      await expect(cartoonDinosaurs).toBeVisible();
      if (mobile) await cartoonDinosaurs.locator("..").getByRole("button").click();
      else await cartoonDinosaurs.hover();
      const cartoonFeats = mobile ? cartoonDinosaurs.locator("../..").locator(".kmobile-feats") : page.getByTestId("landing-cat-feats");
      await expect(cartoonFeats.locator(".kcat-feat")).toHaveCount(2);
      for (const id of [18, 60]) await expect(cartoonFeats.locator(`a[href="/livro/${id}?modo=cartoon"]`)).toBeVisible();
      const adventure = panel.locator('a[href="/catalogo?modo=cartoon#aventuras-adventure"]').first();
      await adventure.click();
      await expect(page.getByTestId("catalog-category")).toHaveValue("aventuras-adventure");
      const adventureBooks = [2, 10, 14, 25, 33];
      await expect(page.getByTestId("landing-catalog-card")).toHaveCount(adventureBooks.length);
      for (const id of adventureBooks) {
        await expect(page.locator(`a.cat-book-link[href="/livro/${id}?modo=cartoon"]`)).toBeVisible();
      }
      await expect(page.locator('a.cat-book-link[href="/livro/33?modo=cartoon"]')).toHaveAttribute("href", "/livro/33?modo=cartoon");
      await page.locator('a.cat-book-link[href="/livro/33?modo=cartoon"]').click();
      await expect(page.getByTestId("book-series-cover")).toBeVisible();
    });
  }
}
