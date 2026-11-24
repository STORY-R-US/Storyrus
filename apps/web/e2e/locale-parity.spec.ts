import { expect, test } from "@playwright/test";

for (const path of ["/", "/cartoon"]) {
  test(`PT, EN and ES keep identical books and complete images on ${path}`, async ({ page }) => {
    test.setTimeout(120_000);
    await page.addInitScript(() => localStorage.setItem("lang", "pt"));
    await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
    await page.goto(path);
    await expect(page.getByTestId("landing-hero-title")).toBeVisible();
    while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
    const read = async () => ({
      books: await page.locator("#catalogo .cat-book-link").evaluateAll((links) => links.map((a) => a.getAttribute("href"))),
      hero: await page.locator('.hero-series:not([aria-hidden="true"])').count(),
      reviews: await page.locator('.rev-photo:not([aria-hidden="true"])').count(),
      videos: await page.locator("#videos .vid-card").count(),
      how: await page.locator("#como img").count(),
      steps: await page.locator("#passo img").count(),
    });
    const pt = await read();
    expect(pt.books).toHaveLength(path === "/" ? 109 : 59);
    expect(pt.hero).toBe(path === "/" ? 17 : 4);
    for (const lang of ["pt", "en", "es"]) {
      await page.getByTestId(`landing-lang-${lang}`).click();
      expect(await read()).toEqual(pt);
      const images = page.locator("img");
      // The carousel intentionally clears inactive src values as it advances.
      // Decode its declared assets independently instead of racing React's src updates.
      const failed = await images.evaluateAll(async (imgs) => {
        const sources = [...new Set(imgs.map((img) => img.dataset.src || img.getAttribute("src") || ""))];
        const failures: string[] = [];
        // Bound decoded-image memory on smaller laptops and CI workers.
        for (const src of sources) {
          if (!src) { failures.push("missing image source"); continue; }
          const probe = new Image();
          probe.src = src;
          try { await probe.decode(); } catch { failures.push(src); }
          probe.src = "";
        }
        return failures;
      });
      expect(failed).toEqual([]);
    }
  });
}

for (const lang of ["pt", "en", "es"]) for (const width of [390, 1440]) {
  test(`Cartoon keeps its existing books in catalog order in ${lang} at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.addInitScript(value => localStorage.setItem("lang", value), lang);
    await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
    const readBooks = async (path: string) => {
      await page.goto(path);
      await expect(page.getByTestId("landing-hero-title")).toBeVisible();
      while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
      return page.locator("#catalogo .cat-book-link").evaluateAll(links =>
        links.map(link => new URL((link as HTMLAnchorElement).href).pathname),
      );
    };
    const realistic = await readBooks("/");
    const cartoon = await readBooks("/cartoon");
    expect(realistic).toHaveLength(109);
    expect(new Set(realistic).size).toBe(109);
    expect(cartoon).toHaveLength(59);
    expect(cartoon).toEqual(realistic.filter(path => Number(path.split("/").at(-1)) < 69));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("a formerly PT-only book retains its cover, page and photo after changing language", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("lang", "pt"));
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.goto("/livro/20");
  for (const lang of ["pt", "en", "es"]) {
    await page.getByTestId(`landing-lang-${lang}`).click();
    await expect(page.getByTestId("not-found-title")).toHaveCount(0);
    const tabs = page.locator(".book-series [role=tab]");
    await expect(tabs).toHaveCount(3);
    for (let i = 0; i < 3; i++) {
      await tabs.nth(i).click();
      const image = page.locator(".book-series img").first();
      await expect.poll(() => image.evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    }
  }
});
