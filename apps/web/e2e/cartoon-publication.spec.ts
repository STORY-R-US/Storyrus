import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect, test } from "./fixtures";
import { TEST_SESSION_TOKEN } from "./session";

const LANGUAGES = ["pt", "en", "es"] as const;
type Lang = (typeof LANGUAGES)[number];
const ROLES = ["cover", "page", "holding"] as const;

// Approved editorial titles, independent of the frontend's imported registry.
const BOOKS = [
  {
    index: 70,
    titles: {
      pt: "Beatriz e o Museu dos Dinossauros",
      en: "Beatriz and the Dinosaur Museum",
      es: "Beatriz y el Museo de los Dinosaurios",
    },
  },
  {
    index: 87,
    titles: {
      pt: "Catarina e João: Do Primeiro Olhar ao Nosso Lar",
      en: "Catarina and João: From Our First Glance to Our Home",
      es: "Catarina y João: De la Primera Mirada a Nuestro Hogar",
    },
  },
  {
    index: 118,
    titles: {
      pt: "O Primeiro Colo de Noah: Um Encontro de Amor",
      en: "Noah's First Cuddle: A Meeting Filled with Love",
      es: "El Primer Abrazo de Noah: Un Encuentro de Amor",
    },
  },
] as const;

function assetPath(index: number, lang: Lang, role: (typeof ROLES)[number]) {
  return `/exemplos/cartoon-20261124/${index}/${role}-${lang}.webp`;
}

function escaped(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function loaded(image: Locator) {
  await expect.poll(
    () => image.evaluate((element) => {
      const img = element as HTMLImageElement;
      return img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
    }),
    { timeout: 15_000 },
  ).toBe(true);
}

async function mockAccount(page: Page, lang: Lang) {
  const writes: string[] = [];
  await page.addInitScript(({ language, token }) => {
    localStorage.setItem("lang", language);
    localStorage.setItem("storyrus_token", token);
  }, { language: lang, token: TEST_SESSION_TOKEN });
  await page.route("**/v1/**", (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET") {
      writes.push(`${request.method()} ${path}`);
      return route.fulfill({ status: 405, json: { detail: "Publication preview tests never create or modify projects" } });
    }
    if (path.endsWith("/auth/me")) {
      return route.fulfill({ json: {
        id: "publication-test", email: "publication@example.test", full_name: "Ana",
        is_guest: false, email_verified: true,
        terms_accepted_at: "2026-11-24", adult_confirmed_at: "2026-11-24",
        phone: "11999999999", street: "Rua de Teste", number: "1",
        city: "São Paulo", postal_code: "01310100", state: "SP", country: "BR", credits: 10,
      } });
    }
    if (path.endsWith("/credits")) return route.fulfill({ json: { credits: 10 } });
    if (path.endsWith("/voices")) return route.fulfill({ json: { items: [], custom_voice_available: false } });
    return route.fulfill({ json: [] });
  });
  return writes;
}

async function screenshot(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(name);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: "image/png" });
}

for (const width of [390, 1440]) for (const book of BOOKS) {
  for (const lang of LANGUAGES) {
    test(`new Cartoon book ${book.index} keeps its complete ${lang} gallery and Studio model at ${width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      const writes = await mockAccount(page, lang);
      const prefix = `/exemplos/cartoon-20261124/${book.index}/`;
      const responses = new Map<string, number>();
      const failedAssets: string[] = [];
      page.on("response", (response) => {
        const path = new URL(response.url()).pathname;
        if (path.startsWith(prefix)) responses.set(path, response.status());
      });
      page.on("requestfailed", (request) => {
        const path = new URL(request.url()).pathname;
        if (path.startsWith(prefix)) failedAssets.push(path);
      });

      await page.goto(`/livro/${book.index}?modo=cartoon`);
      await expect(page.getByTestId("not-found-title")).toHaveCount(0);
      await expect(page.locator(".book-sheet h1")).toHaveText(book.titles[lang]);
      await expect(page).toHaveTitle(new RegExp(escaped(book.titles[lang]), "i"));
      const tabs = page.locator(".book-series [role=tab]");
      await expect(tabs).toHaveCount(3);
      for (const [position, role] of ROLES.entries()) {
        await tabs.nth(position).click();
        const image = page.locator(".book-series img");
        await expect(image).toHaveAttribute("src", assetPath(book.index, lang, role));
        await loaded(image);
        expect(responses.get(assetPath(book.index, lang, role))).toBe(200);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

      if ([62, 70, 118].includes(book.index)) {
        await tabs.first().click();
        await loaded(page.locator(".book-series img"));
        await screenshot(page, testInfo, `book-${book.index}-${lang}-${width}.png`);
      }

      const personalize = page.getByTestId("landing-personalize");
      await expect(personalize).toHaveAttribute("href", new RegExp(`modelo=catalog-cartoon-${book.index}(?:&|$)`));
      await personalize.click();
      await expect(page).toHaveURL(new RegExp(`/app\\?.*modelo=catalog-cartoon-${book.index}(?:&|$)`));
      const selected = page.getByTestId("studio-selected-catalog-model");
      await expect(selected).toBeVisible();
      await expect(selected.locator("strong").first()).toHaveText(book.titles[lang]);
      await selected.locator(".catalog-book-design-samples summary").click();
      const examples = selected.locator(".catalog-book-design-trio img");
      await expect(examples).toHaveCount(3);
      for (const [position, role] of ROLES.entries()) {
        await expect(examples.nth(position)).toHaveAttribute("src", assetPath(book.index, lang, role));
        await loaded(examples.nth(position));
      }
      await selected.locator(".catalog-book-design-trio button").first().click();
      const enlarged = page.locator("dialog img");
      await expect(enlarged).toHaveAttribute("src", assetPath(book.index, lang, "cover"));
      await loaded(enlarged);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(failedAssets).toEqual([]);
      expect([...responses.values()].every((status) => status === 200)).toBe(true);
      expect(writes, "Browsing the published previews must not generate, purchase, or mutate a project").toEqual([]);
    });
  }
}
