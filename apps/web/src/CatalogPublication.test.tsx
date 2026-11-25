import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  catalogCoverFile,
  catalogEntry,
  catalogSections,
  type CatalogCardBook,
  type CatalogSection,
} from "./Landing";
import { catalogModel, catalogModelId } from "./catalogModel";
import publication from "./catalogPublication20261124.json";
import localizedAssets from "./localizedExamples.json";
import { localizedExample } from "./localizedExamples";

const languages = ["pt", "en", "es"] as const;
const roles = ["cover", "page", "holding"] as const;
const publicationDate = new Date("2026-11-24T12:00:00Z");
const newIndexes = Array.from({ length: 50 }, (_, offset) => 69 + offset);
const revisedIndexes = [62, 63, 64, 65, 66, 67];
const publishedIndexes = [...revisedIndexes, ...newIndexes];

// The existing 59 books remain intact alongside the fifty reviewed Cartoon editions.
const previousIndexes = [
  0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 18, 19, 20, 21, 22, 23, 24,
  25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43,
  44, 45, 46, 47, 49, 51, 52, 53, 54, 55, 56, 57, 59, 60, 62, 63, 64, 65,
  66, 67, 68,
];

function indexes(books: CatalogCardBook[]) {
  return books.map((book) => book.catalogI).sort((a, b) => (a ?? -1) - (b ?? -1));
}

function uniqueIndexes(sections: CatalogSection[]) {
  return [...new Set(indexes(sections.flatMap((section) => section.books)))];
}

function themeIndexes(sections: CatalogSection[], categoryId: string, themeId: string) {
  const theme = sections.find((section) => section.id === categoryId)?.subs.find((sub) => sub.id === themeId);
  expect(theme, `${categoryId}/${themeId} is present`).toBeDefined();
  return indexes(theme!.books);
}

function occurrences(sections: CatalogSection[], catalogIndex: number) {
  return sections.flatMap((section) => section.subs
    .filter((sub) => sub.books.some((book) => book.catalogI === catalogIndex))
    .map((sub) => `${section.id}/${sub.id}`));
}

function topology(sections: CatalogSection[]) {
  return sections.map((section) => ({
    id: section.id,
    subs: section.subs.map((sub) => ({ id: sub.id, indexes: indexes(sub.books) })),
  }));
}

describe("approved photographic catalog publication — 2026-11-24", () => {
  it.each(languages)("publishes the complete catalog in %s while preserving Cartoon", (lang) => {
    const realistic = catalogSections(lang, "photo", publicationDate);
    const cartoon = catalogSections(lang, "cartoon", publicationDate);

    expect(publication.map((book) => book.catalog_index)).toEqual(newIndexes);
    expect(new Set(publication.map((book) => book.stable_slug)).size).toBe(50);
    expect(uniqueIndexes(realistic)).toEqual([...previousIndexes, ...newIndexes]);
    expect(uniqueIndexes(realistic)).toHaveLength(109);
    expect(realistic.map((section) => [section.id, section.subs.length])).toEqual([
      ["aventuras", 7], ["voce-e-eu", 10], ["ocasioes", 6], ["educativo", 9],
    ]);
    const themes = realistic.flatMap((section) => section.subs);
    expect(themes).toHaveLength(32);
    for (const section of realistic) {
      for (const sub of section.subs) {
        const ids = indexes(sub.books);
        // The three biblical stories exclude the family book "Mamãe e Eu".
        const minimum = sub.id === "biblico" ? 3 : 4;
        expect(new Set(ids).size, `${lang}: ${section.id}/${sub.id}`).toBeGreaterThanOrEqual(minimum);
        expect(new Set(ids).size, `${lang}: duplicate within ${section.id}/${sub.id}`).toBe(ids.length);
      }
    }
    expect(topology(realistic)).toEqual(topology(catalogSections("pt", "photo", publicationDate)));

    for (const record of publication) {
      const book = catalogEntry(lang, record.catalog_index);
      expect(book, `${lang}: book ${record.catalog_index}`).toMatchObject({
        catalogI: record.catalog_index,
        t: record.locales[lang].t,
        story: record.locales[lang].p,
        quote: record.locales[lang].quote,
        tag: record.locales[lang].tag,
        cover: "Hard",
        size: "M",
        theme: record.theme_id,
        heroi: record.hero_name,
      });
    }
    expect(catalogEntry(lang, 69)?.heroi).toBe("Léo");
    for (const index of publishedIndexes) {
      const cover = `catalog-20261124/${index}/cover-${lang}.webp`;
      expect(catalogCoverFile(index, lang, "photo"), `cover ${index}/${lang}`).toBe(cover);
      expect(catalogEntry(lang, index)?.img).toBe(cover);
    }

    expect(themeIndexes(realistic, "voce-e-eu", "irmaos_primos")).toEqual([22, 89, 90, 91]);
    expect(themeIndexes(realistic, "voce-e-eu", "recem_nascidos")).toEqual([83, 84, 85, 118]);
    expect(catalogEntry(lang, 42)?.theme).toBe("consciencia_corporal");
    expect(occurrences(realistic, 42)).toEqual(["educativo/consciencia_corporal"]);
    expect(occurrences(cartoon, 42)).toEqual(["educativo/consciencia_corporal"]);
    for (const sections of [realistic, cartoon]) {
      expect(themeIndexes(sections, "educativo", "biblico")).toEqual([20, 38, 47]);
      expect(themeIndexes(sections, "voce-e-eu", "mothers_day")).toContain(44);
      expect(themeIndexes(sections, "voce-e-eu", "family_love")).toContain(44);
    }

    const dadBooks = [14, 21, 81, 82];
    expect(themeIndexes(realistic, "voce-e-eu", "fathers_day")).toEqual(dadBooks);
    expect(themeIndexes(realistic, "ocasioes", "fathers_day")).toEqual(dadBooks);
    expect(publication.filter((book) => book.theme_id === "fathers_day")
      .map((book) => [book.catalog_index, book.hero_name])).toEqual([[81, "Eduardo"], [82, "Laura"]]);

    expect(uniqueIndexes(cartoon)).toEqual([...previousIndexes, ...newIndexes]);
    expect(topology(cartoon)).toEqual(topology(realistic));
    expect(uniqueIndexes(cartoon)).toHaveLength(109);
    for (const book of cartoon.flatMap((section) => section.books)) {
      expect(book.img, `${lang}: Cartoon book ${book.catalogI}`).not.toContain("catalog-20261124/");
      expect(book.img).toBe(catalogCoverFile(book.catalogI!, lang, "cartoon"));
    }
    for (const index of revisedIndexes) {
      expect(catalogCoverFile(index, lang, "cartoon")).not.toBe(catalogCoverFile(index, lang, "photo"));
    }
  });

  it("resolves 168 backend aliases to 504 distinct, present localized preview assets", () => {
    const backendAliases = Object.keys(localizedAssets).filter((key) =>
      /^catalog_models\/realistic-\d+-(cover|page|holding)-20261124\.webp$/.test(key));
    const aliases = new Set<string>();
    const webFiles = new Set<string>();
    const filesByLanguage = new Map(languages.map((lang) => [lang, new Set<string>()]));
    const filesByRole = new Map(roles.map((role) => [role, new Set<string>()]));

    expect(backendAliases).toHaveLength(168);
    for (const index of publishedIndexes) {
      const model = catalogModel(catalogModelId(index));
      expect(model, `model ${index}`).toBeDefined();
      // Availability is validated by the backend suite, not by the image routing contract.
      expect(model?.style).toBe("realistic");
      for (const role of roles) {
        const alias = `catalog_models/realistic-${index}-${role}-20261124.webp`;
        const ptMaster = `catalog-20261124/${index}/${role}-pt.webp`;
        expect(model?.sources[role], `model source ${index}/${role}`).toBe(alias);
        expect(backendAliases, alias).toContain(alias);
        aliases.add(alias);
        expect(existsSync(resolve("../../backend/app/assets/composition_examples", alias)), alias).toBe(true);

        for (const lang of languages) {
          const expectedFile = `catalog-20261124/${index}/${role}-${lang}.webp`;
          const localizedFile = localizedExample(alias, lang);
          expect(localizedFile, `${alias} -> ${lang}`).toBe(expectedFile);
          expect(localizedExample(ptMaster, lang), `${ptMaster} -> ${lang}`).toBe(expectedFile);
          expect(existsSync(resolve("public/exemplos", localizedFile)), localizedFile).toBe(true);
          webFiles.add(localizedFile);
          filesByLanguage.get(lang)!.add(localizedFile);
          filesByRole.get(role)!.add(localizedFile);
        }
      }
    }
    expect(aliases.size).toBe(168);
    expect(webFiles.size).toBe(504);
    for (const files of [...filesByLanguage.values(), ...filesByRole.values()]) expect(files.size).toBe(168);
  });
});
