import { expect, test } from "@playwright/test";

for (const route of ["/", "/cartoon"]) {
  for (const lang of ["pt", "en", "es"]) {
    for (const width of [390, 1440]) {
      test(`loads only the active book sequence on ${route} in ${lang} at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 900 });
        await page.emulateMedia({ reducedMotion: "reduce" });
        await page.addInitScript(value => localStorage.setItem("lang", value), lang);
        await page.route("**/health", r => r.fulfill({ json: { status: "ok" } }));
        const requested = new Set<string>();
        page.on("request", request => requested.add(new URL(request.url()).pathname));
        await page.goto(route);
        const shots = page.locator('.hero-carousel img[data-testid^="landing-hero-slide-"]');
        const first = shots.first();
        await expect(first).toBeVisible();
        await first.evaluate(image => (image as HTMLImageElement).decode());
        const last = shots.last();
        const deferred = new URL((await last.getAttribute("data-src"))!, page.url()).pathname;
        expect(requested.has(deferred)).toBe(false);

        const nextBookCover = await shots.nth(3).getAttribute("data-src");
        const nextButton = page.locator(".khero-flipbook .fb-nav").last();
        for (let i = 0; i < 3; i++) await nextButton.click();
        await expect(page.getByTestId("landing-hero-flip")).toHaveAttribute("src", nextBookCover!);
        await expect(shots.nth(3)).toBeVisible();
        await shots.nth(3).evaluate(image => (image as HTMLImageElement).decode());
        await expect.poll(() => requested.has(new URL(nextBookCover!, page.url()).pathname)).toBe(true);
        expect(requested.has(deferred)).toBe(false);
      });
    }
  }
}
