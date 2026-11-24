import { expect, test } from "./fixtures";

for (const lang of ["pt", "en", "es"]) for (const width of [390, 1440]) {
  test(`catalog covers fit and remain uniform in ${lang} at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.addInitScript(value => localStorage.setItem("lang", value), lang);
    // Permit only the site's typography provider; the fixture still blocks live API writes.
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, route => route.continue());
    await page.goto("/catalogo");
    await expect(page.getByTestId("landing-catalog-card")).toHaveCount(109);
    await page.evaluate(() => document.fonts.ready);
    const frames = await page.locator(".cat-book").evaluateAll(elements => elements.map(element => {
      const box = element.getBoundingClientRect();
      return { width: box.width, height: box.height };
    }));
    expect(frames).toHaveLength(109);
    for (const frame of frames) {
      expect(Math.abs(frame.width - frames[0].width)).toBeLessThanOrEqual(1);
      expect(Math.abs(frame.height - frames[0].height)).toBeLessThanOrEqual(1);
      expect(Math.abs(frame.width - frame.height)).toBeLessThanOrEqual(1);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.goto("/catalogo#aventuras-dinosaurs");
    await expect(page.getByTestId("landing-catalog-card")).toHaveCount(4);
    const images = page.locator(".cat-book img");
    await images.evaluateAll(items => items.forEach(item => item.loading = "eager"));
    await expect.poll(() => images.evaluateAll(items => items.every(item => item.complete && item.naturalWidth > 0))).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    const shot = testInfo.outputPath(`catalog-${lang}-${width}.png`);
    await page.screenshot({ path: shot, fullPage: true });
    await testInfo.attach("catalog visual review", { path: shot, contentType: "image/png" });
  });
}
