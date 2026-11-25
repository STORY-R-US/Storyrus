import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { catalogCoverFile } from "./Landing";
import { catalogModel } from "./catalogModel";
import { localizedExample } from "./localizedExamples";

describe("complete Cartoon editions of the fifty new books", () => {
  it("connects each localized cover, spread and reading scene to the correct Studio model", () => {
    const files = new Set<string>();
    for (let index = 69; index <= 118; index++) {
      const model = catalogModel(`catalog-cartoon-${index}`)!;
      expect(model.available).toBe(true);
      expect(model.style).toBe("cartoon");
      expect(model.titles).toEqual(catalogModel(`catalog-realistic-${index}`)!.titles);
      for (const role of ["cover", "page", "holding"] as const) {
        const alias = `catalog_models/cartoon-${index}-${role}-20261124.webp`;
        expect(model.sources[role]).toBe(alias);
        expect(existsSync(resolve("../../backend/app/assets/composition_examples", alias))).toBe(true);
        for (const lang of ["pt", "en", "es"] as const) {
          const file = `cartoon-20261124/${index}/${role}-${lang}.webp`;
          expect(localizedExample(alias, lang)).toBe(file);
          expect(localizedExample(`cartoon-20261124/${index}/${role}-pt.webp`, lang)).toBe(file);
          expect(existsSync(resolve("public/exemplos", file))).toBe(true);
          if (role === "cover") expect(catalogCoverFile(index, lang, "cartoon")).toBe(file);
          files.add(file);
        }
      }
    }
    expect(files.size).toBe(450);
  });
});
