import { expect, test } from "@playwright/test";

for (const [route, count] of [["/", 50], ["/cartoon", 25], ["/catalogo", 55]] as const) {
for (const lang of ["pt", "en", "es"]) {
  test(`visible cover artwork fills the frame in ${lang} on ${route}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("lang", value), lang);
    await page.route("**/health", r => r.fulfill({ json: { status: "ok" } }));
    await page.goto(route);
    await expect(page.getByTestId("catalog-search")).toBeVisible();
    while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
    await expect(page.locator("#catalogo .cat-card")).toHaveCount(count);
    const gaps = await page.locator("#catalogo .cat-card .cat-book img").evaluateAll(async images => {
      const results: { src: string; gaps: number[] }[] = [];
      // Release each decoded image before inspecting the next large cover.
      for (const element of images) {
        const image = element as HTMLImageElement;
        // Decode even lazy images: check artwork pixels, not just equal DOM boxes.
        const bitmap = await createImageBitmap(await (await fetch(image.src)).blob());
        const canvas = document.createElement("canvas");
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const context = canvas.getContext("2d")!;
        context.drawImage(bitmap, 0, 0);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        const columns = new Uint32Array(canvas.width);
        const rows = new Uint32Array(canvas.height);
        for (let y = 0; y < canvas.height; y++) {
          for (let x = 0; x < canvas.width; x++) {
            if (pixels[(y * canvas.width + x) * 4 + 3] > 128) {
              columns[x]++; rows[y]++;
            }
          }
        }
        const x0 = columns.findIndex(n => n > canvas.height / 2);
        const y0 = rows.findIndex(n => n > canvas.width / 2);
        const x1 = columns.findLastIndex(n => n > canvas.height / 2) + 1;
        const y1 = rows.findLastIndex(n => n > canvas.width / 2) + 1;
        const rect = image.getBoundingClientRect();
        const frame = image.parentElement!.getBoundingClientRect();
        results.push({ src: image.src, gaps: [
          rect.left + x0 / canvas.width * rect.width - frame.left,
          rect.top + y0 / canvas.height * rect.height - frame.top,
          frame.right - rect.left - x1 / canvas.width * rect.width,
          frame.bottom - rect.top - y1 / canvas.height * rect.height,
        ] });
        bitmap.close();
        canvas.width = 0;
        canvas.height = 0;
      }
      return results;
    });
    expect(gaps).toHaveLength(count);
    for (const cover of gaps) {
      for (const gap of cover.gaps) expect(Math.abs(gap), cover.src).toBeLessThan(1);
    }
  });
}
}

for (const width of [390, 1280]) {
for (const [route, count] of [["/", 50], ["/cartoon", 25], ["/catalogo", 55]] as const) {
for (const lang of ["pt", "en", "es"]) {
  test(`uniform covers and working P/M in ${lang} on ${route} at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(value => localStorage.setItem("lang", value), lang);
    await page.route("**/health", r => r.fulfill({ json: { status: "ok" } }));
    await page.goto(route);
    await expect(page.getByTestId("catalog-search")).toBeVisible();
    while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
    const cards = page.locator("#catalogo .cat-card");
    await expect(cards).toHaveCount(count);
    const boxes = await cards.locator(".cat-book").evaluateAll(els => els.map(e => ({ w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height })));
    expect(Math.max(...boxes.map(b => b.w)) - Math.min(...boxes.map(b => b.w))).toBeLessThan(2);
    for (const b of boxes) expect(Math.abs(b.w - b.h)).toBeLessThan(2);
    const card = cards.filter({ has: page.getByTestId("landing-personalize") }).first();
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
}
}
