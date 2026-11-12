import { expect, test } from "@playwright/test";

for (const width of [390, 1280]) {
  test(`uniform covers and working P/M at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("lang", "pt"));
    await page.route("**/health", r => r.fulfill({ json: { status: "ok" } }));
    await page.goto("/");
    const cards = page.locator("#catalogo .cat-card");
    await expect(cards).toHaveCount(48);
    const boxes = await cards.locator(".cat-book").evaluateAll(els => els.map(e => ({ w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height })));
    expect(Math.max(...boxes.map(b => b.w)) - Math.min(...boxes.map(b => b.w))).toBeLessThan(2);
    for (const b of boxes) expect(Math.abs(b.w - b.h)).toBeLessThan(2);
    const card = cards.first();
    const book = card.locator(".cat-book");
    const initial = (await book.boundingBox())!;
    await card.getByRole("button", { name: "P", exact: true }).click();
    await expect(card.getByRole("button", { name: "P", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect.poll(async () => (await book.boundingBox())!.width / initial.width).toBeCloseTo(.75, 2);
    expect(decodeURIComponent((await card.getByTestId("landing-personalize").getAttribute("href"))!)).toContain("tamanho=P");
    await card.getByRole("button", { name: "M", exact: true }).click();
    await expect.poll(async () => (await book.boundingBox())!.width / initial.width).toBeCloseTo(1, 2);
    expect(decodeURIComponent((await card.getByTestId("landing-personalize").getAttribute("href"))!)).toContain("tamanho=M");
  });
}
