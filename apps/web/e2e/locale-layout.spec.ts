import { expect, test } from "./fixtures";

for (const width of [320, 390, 768, 1024, 1440]) {
  for (const route of ["/", "/cartoon"]) {
    test(`translated layout keeps PT dimensions on ${route} at ${width}px`, async ({ page }) => {
      test.setTimeout(60_000);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.addInitScript(() => localStorage.setItem("lang", "pt"));
      await page.goto(route);
      await expect(page.getByTestId("catalog-search")).toBeVisible();
      while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
      const selectors = [".khead", ".khero-intro", ".khero-intro h1", ".khero-intro .keyebrow", ".khero-intro .kbtn", ".hero-carousel", ".hero-series.on .hero-series-inner", ".hero-shot.on", ".fb-stage", ".khero-after", ".khead-links .kbtn", ".kcats .kcat-btn", ".cat-card", ".cat-body h3", ".cat-note-grid", ".cat-go", ".howex-card", ".faq-q", ".kband .kbtn", ".kfoot", ".kfoot-nav a", ".kfoot-tag", ".kfoot-copy", ".rev-card", ".vid-card", ".fmt-card", ".kband", ".cat-below", ".cat-notes-sizes", ".promise-card", ".ktitle", ".ksub"];
      let baseline: { selector: string; width: number; height: number }[] = [];
      for (const lang of ["pt", "en", "es"]) {
        await page.getByTestId(`landing-lang-${lang}`).click();
        await page.getByTestId("landing-hero-pick-0").click();
        await page.locator(".flipbook").hover();
        await expect.poll(async () => (await page.locator(".fb-stage").boundingBox())?.width ?? 0).toBeGreaterThan(0);
        // Wait for responsive sizing and web fonts before comparing actual boxes.
        await page.evaluate(() => document.fonts.ready);
        await page.mouse.move(0, 0);
        await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
        const current = await page.evaluate(list => list.flatMap(selector => [...document.querySelectorAll(selector)].map(element => {
          const rect = element.getBoundingClientRect();
          return { selector, width: rect.width, height: rect.height };
        })), selectors);
        if (lang === "pt") baseline = current;
        else {
          expect(current).toHaveLength(baseline.length);
          for (let i = 0; i < current.length; i++) {
            const message = `${lang}: ${current[i].selector}, element ${i}`;
            expect.soft(Math.abs(current[i].width - baseline[i].width), message).toBeLessThan(2);
            expect.soft(Math.abs(current[i].height - baseline[i].height), message).toBeLessThan(2);
          }
        }
      }
    });
  }
}
