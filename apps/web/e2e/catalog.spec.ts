import { expect, test } from "@playwright/test";

for (const lang of ["pt", "en", "es"]) {
  test(`catálogo organizado e capas disponíveis em ${lang}`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem("lang", value), lang);
    await page.route(/https:\/\/ipapi\.co\//, (route) => route.abort());
    await page.goto("/catalogo");
    await expect(page.locator("#aventuras > h2")).toBeVisible();
    await expect(page.locator("#voce-e-eu-tio_tia")).toBeAttached();
    await expect(page.locator('#aventuras-sport a[href="/livro/53"]')).toHaveCount(2);
    const images = page.locator(".cat-book img");
    await images.evaluateAll((items) => items.forEach((item) => (item as HTMLImageElement).loading = "eager"));
    await expect.poll(() => images.evaluateAll((items) => items.filter((item) => !(item as HTMLImageElement).complete || !(item as HTMLImageElement).naturalWidth).length), { timeout: 15000 }).toBe(0);
    if (lang === "pt") await page.screenshot({ path: "test-results/catalogo-organizado.png", fullPage: true });
    await page.locator('#aventuras-sport a[href="/livro/53"]').first().click();
    await expect(page).toHaveURL(/\/livro\/53$/);
    await expect(page.getByTestId("book-series-cover")).toBeVisible();
  });
}

test("ordem da vitrine", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("lang", "pt"));
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.goto("/");
  const catalog = page.locator("#catalogo");
  const links = catalog.locator(".cat-book-link");
  await expect(links).toHaveCount(49);
  expect((await links.evaluateAll((items) => items.map((item) => item.getAttribute("href")))).slice(0, 12)).toEqual([25, 26, 27, 21, 30, 22, 20, 38, 47, 0, 36, 53].map((id) => `/livro/${id}`));
});

test("vitrine em desktop e celular", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("lang", "pt"));
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.setViewportSize({ width: 1280, height: 3000 });
  await page.goto("/");
  await page.locator("#catalogo").evaluate((element) => window.scrollTo(0, element.getBoundingClientRect().top + window.scrollY - 80));
  await page.locator("#catalogo img").evaluateAll((items) => items.forEach((item) => (item as HTMLImageElement).loading = "eager"));
  await expect.poll(() => page.locator("#catalogo img").evaluateAll((items) => items.filter((item) => !(item as HTMLImageElement).naturalWidth).length), { timeout: 15000 }).toBe(0);
  await page.screenshot({ path: "test-results/vitrine-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  const first = page.locator("#catalogo .cat-card").first();
  await first.scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/vitrine-mobile.png" });
});
