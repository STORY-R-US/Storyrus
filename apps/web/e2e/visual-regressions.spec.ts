import { expect, test } from "./fixtures";
import { TEST_SESSION_TOKEN } from "./session";

for (const signedIn of [false, true]) {
  test(`navigation stays centered and readable with signedIn=${signedIn}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.addInitScript(({ signedIn, token }) => {
      localStorage.setItem("lang", "pt");
      if (signedIn) localStorage.setItem("storyrus_token", token);
    }, { signedIn, token: TEST_SESSION_TOKEN });
    await page.route("**/v1/auth/me", r => r.fulfill({ json: {
      id: "visual-test", email: "test@example.invalid", is_guest: false,
      email_verified: true, full_name: "Alexandria Teste", credits: 0,
    } }));
    await page.goto("/");
    await expect(page.getByTestId("landing-hero-title")).toBeVisible();
    if (signedIn) await expect(page.getByTestId("landing-header-user")).toBeVisible();
    for (const width of [1321, 1366, 1440, 1600, 1760, 1862]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const lang of ["pt", "en", "es"]) {
        await page.getByTestId(`landing-lang-${lang}`).click();
        const nav = (await page.locator(".kcats").boundingBox())!;
        const actions = (await page.locator(".khead-actions").boundingBox())!;
        expect(Math.abs(nav.x + nav.width / 2 - width / 2), `${lang} at ${width}`).toBeLessThan(1);
        expect(nav.x + nav.width + 8).toBeLessThanOrEqual(actions.x);
        expect(actions.x + actions.width).toBeLessThanOrEqual(width);
      }
    }
    await page.locator(".theme-toggle").first().click();
    await expect.poll(() => page.locator(".kcats .kcat-btn").first().evaluate(el => {
      const style = getComputedStyle(el);
      return { color: style.color, background: style.backgroundColor };
    })).toEqual({ background: "rgb(255, 255, 255)", color: "rgb(31, 53, 104)" });
  });
}

for (const width of [390, 1440]) {
  for (const lang of ["pt", "en", "es"]) {
    test(`all public book galleries fit and load in ${lang} at ${width}px`, async ({ page }) => {
      test.setTimeout(180_000);
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(value => localStorage.setItem("lang", value), lang);
      const books = new Map<string, string>();
      for (const route of ["/catalogo", "/cartoon"]) {
        await page.goto(route);
        await expect(page.getByTestId("catalog-search")).toBeVisible();
        while (await page.getByTestId("catalog-more").count()) await page.getByTestId("catalog-more").click();
        const cards = await page.locator(".cat-card").evaluateAll(elements => elements.map(card => ({
          href: card.querySelector<HTMLAnchorElement>(".cat-book-link")!.getAttribute("href")!,
          image: card.querySelector<HTMLImageElement>(".cat-book img")!.src,
        })));
        for (const card of cards) books.set(card.href, card.image);
      }
      expect(books.size).toBeGreaterThan(60);
      expect(books.has("/livro/58")).toBe(false);
      for (const [href, cover] of books) {
        await page.goto(href);
        const gallery = page.getByTestId("book-series");
        await expect(gallery.locator("img"), href).toHaveAttribute("src", new URL(cover).pathname);
        const dimensions = await page.locator(".book-sheet, .book-series-frame, .book-sheet .cat-body, .book-sheet h1").evaluateAll(elements => elements.map(element => {
          const box = element.getBoundingClientRect();
          return { left: box.left, right: box.right, scroll: element.scrollWidth, width: element.clientWidth };
        }));
        for (const box of dimensions) {
          expect(box.left, href).toBeGreaterThanOrEqual(0);
          expect(box.right, href).toBeLessThanOrEqual(width + 1);
          expect(box.scroll, href).toBeLessThanOrEqual(box.width + 1);
        }
        const tabs = gallery.getByRole("tab");
        const count = await tabs.count();
        for (let i = 0; i < Math.max(1, count); i++) {
          if (count) await tabs.nth(i).click();
          await expect.poll(() => gallery.locator("img").evaluate(img => (img as HTMLImageElement).naturalWidth), { message: `${href}, image ${i}` }).toBeGreaterThan(0);
          expect(await gallery.locator("img").getAttribute("src")).not.toContain("/exemplos//exemplos/");
        }
      }
    });
  }
}

for (const lang of ["pt", "en", "es"]) {
  test(`tablet header, hero action, search and category results in ${lang}`, async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.addInitScript(value => localStorage.setItem("lang", value), lang);
    await page.goto("/");
    await expect(page.locator(".khamb")).toBeVisible();
    await expect(page.locator(".khead-main")).toBeHidden();
    await page.setViewportSize({ width: 1280, height: 900 });
    await expect(page.locator(".khamb")).toBeVisible();
    await expect(page.locator(".khead-main")).toBeHidden();
    await page.setViewportSize({ width: 1366, height: 900 });
    await expect(page.locator(".kcats")).toBeVisible();
    const navigation = await page.locator(".kcats").boundingBox();
    const actions = await page.locator(".khead-actions").boundingBox();
    expect(navigation!.x + navigation!.width).toBeLessThan(actions!.x);
    await page.setViewportSize({ width: 1024, height: 900 });
    await expect(page.getByTestId("landing-hero-cta")).toHaveCount(0);
    await expect(page.getByTestId("landing-header-cta")).toBeVisible();
    await page.getByTestId("catalog-search").fill("noé");
    // Search ignores accents; translated proper names can differ.
    await page.getByTestId("catalog-search").fill("Enzo");
    expect(await page.getByTestId("landing-catalog-card").count()).toBeGreaterThan(0);
    await page.getByTestId("catalog-search").fill("zzzz-no-book");
    await expect(page.getByTestId("landing-catalog-card")).toHaveCount(0);
    await page.goto("/catalogo/sentimentos");
    await expect(page.locator(".cat-book-link[href='/livro/64']")).toBeVisible();
    await page.getByTestId("catalog-search").fill("zzzz-no-book");
    await expect(page.locator(".catalog-actions a[href='/catalogo']")).toBeVisible();
    await expect(page.locator(".catalog-actions a[href='/app']")).toBeVisible();
    await page.goto("/app?exemplo=dinosaurs");
    await expect(page.locator(".project-journey-steps")).toHaveCount(1);
    await expect(page.locator(".purchase-steps")).toHaveCount(0);
    await expect(page.getByTestId("studio-story-text")).toContainText(lang === "en" ? "Noah woke" : lang === "es" ? "Noé despertó" : "Noé acordou");
    await expect(page.locator(".studio-preview-trio img")).toHaveCount(3);
  });
}
