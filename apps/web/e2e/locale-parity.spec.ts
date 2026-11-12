import { expect, test } from "@playwright/test";

for (const path of ["/", "/cartoon"]) {
  test(`PT, EN and ES keep identical books and complete images on ${path}`, async ({ page }) => {
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
    expect(pt.books).toHaveLength(path === "/" ? 53 : 30);
    expect(pt.hero).toBe(path === "/" ? 18 : 4);
    for (const lang of ["pt", "en", "es"]) {
      await page.getByTestId(`landing-lang-${lang}`).click();
      expect(await read()).toEqual(pt);
      const images = page.locator("img");
      await images.evaluateAll((imgs) => imgs.forEach((img) => { img.loading = "eager"; }));
      await expect.poll(() => images.evaluateAll((imgs) => imgs.filter((img) => !img.complete || !img.naturalWidth).map((img) => img.src)), { timeout: 20_000 }).toEqual([]);
    }
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
