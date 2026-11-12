import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import assets from "./localizedExamples.json";
import coverFormats from "./coverFormats.json";
import { localizedExample } from "./localizedExamples";
import catalogModels from "./catalogModels.json";
import { Landing, catalogEntry, catalogSections } from "./Landing";

const entries = Object.entries(assets);
beforeAll(() => {
  vi.stubGlobal("IntersectionObserver", class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: vi.fn().mockResolvedValue(undefined) });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", { configurable: true, value: vi.fn() });
});
const canonical = (src: string) => {
  const displayed = src.split("/exemplos/")[1];
  const file = Object.entries(coverFormats).find(([, value]) => value === displayed)?.[0] ?? displayed;
  return entries.find(([, versions]) => Object.values(versions).includes(file))?.[0] ?? file;
};

describe("approved PT images in all languages", () => {
  it("localizes every Cartoon gallery image, including images absent from the homepage", () => {
    for (const model of Object.values(catalogModels).filter((model) => model.style === "cartoon")) {
      for (const source of Object.values(model.sources).filter(Boolean)) {
        const master = source.replace(/^\/?exemplos\//, "");
        for (const lang of ["en", "es"] as const) {
          const displayed = localizedExample(master, lang);
          expect(displayed, `${model.id}: ${master} ${lang}`).not.toBe(master);
          expect(existsSync(resolve("public/exemplos", displayed))).toBe(true);
        }
      }
    }
  });
  it("uses the standard book format for every cover and language", () => {
    for (const [master] of entries.filter(([name]) => /^(cartoon-)?capa-/.test(name) && name !== "capa-livro-teste.jpg")) {
      for (const lang of ["pt", "en", "es"] as const) {
        const displayed = localizedExample(master, lang);
        if (master === "capa-meupai-heroi.png" && lang === "pt") {
          expect(displayed).toBe(master);
        } else {
          expect(displayed, `${master}: ${lang}`).toMatch(/^covers\//);
        }
      }
    }
  });

  it("has both translations and valid display assets for every PT master", () => {
    for (const [master, versions] of entries) {
      expect(existsSync(resolve("public/exemplos", master)), master).toBe(true);
      for (const lang of ["en", "es"] as const) {
        expect(versions[lang], `${master}: missing ${lang} artwork`).not.toBe("");
        const file = localizedExample(master, lang);
        const original = versions[lang] || master;
        expect(file).toBe((coverFormats as Record<string, string>)[original] || original);
        expect(existsSync(resolve("public/exemplos", file)), `${master}: ${lang}`).toBe(true);
      }
    }
    for (const [original, formatted] of Object.entries(coverFormats)) {
      expect(existsSync(resolve("public/exemplos", original)), original).toBe(true);
      expect(existsSync(resolve("public/exemplos", formatted)), formatted).toBe(true);
    }
  });

  for (const variant of ["photo", "cartoon"] as const) {
    it(`keeps the same ordered books and scenes on the ${variant} page`, async () => {
      localStorage.setItem("lang", "pt");
      const { container } = render(<MemoryRouter><Landing variant={variant} /></MemoryRouter>);
      await screen.findByTestId("landing-hero-title");
      while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
      const read = () => ({
        books: [...container.querySelectorAll("#catalogo .cat-book-link")].map((a) => a.getAttribute("href")),
        hero: [...container.querySelectorAll(".hero-carousel img")].map((img) => canonical(img.getAttribute("src")!)),
        reviews: [...container.querySelectorAll("#reviews .rev-photo img")].map((img) => canonical(img.getAttribute("src")!)),
        how: container.querySelectorAll("#como .howex img").length,
        steps: container.querySelectorAll("#passo .howex img").length,
        videos: container.querySelectorAll("#videos .vid-card").length,
      });
      const pt = read();
      expect(pt.books).toHaveLength(variant === "photo" ? 53 : 28);
      expect(pt.hero).toHaveLength(variant === "photo" ? 108 : 24);
      for (const lang of ["en", "es"] as const) {
        fireEvent.click(screen.getByTestId(`landing-lang-${lang}`));
        expect(read()).toEqual(pt);
        expect(document.title).not.toMatch(/Transformamos fotos em|Livros Cartoon/);
      }
    });
  }

  it("keeps catalog sections, book URLs and gallery availability equal to PT", () => {
    const shelves = (lang: "pt" | "en" | "es") => catalogSections(lang).map((section) => ({
      id: section.id,
      subs: section.subs.map((sub) => ({ id: sub.id, books: sub.books.map((book) => book.catalogI) })),
    }));
    for (const lang of ["en", "es"] as const) {
      expect(shelves(lang)).toEqual(shelves("pt"));
      for (let i = 0; i < 68; i++) expect(Boolean(catalogEntry(lang, i)), `book ${i}`).toBe(Boolean(catalogEntry("pt", i)));
    }
  });
});
