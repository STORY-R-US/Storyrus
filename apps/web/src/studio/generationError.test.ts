import { describe, expect, it } from "vitest";
import { generationError } from "./generationError";
import { studioCopy } from "./i18n";

describe.each(["pt", "en", "es"] as const)("book failures in %s", (lang) => {
  const copy = studioCopy(lang);
  it("explains internal failures in the selected language", () => {
    const message = generationError(copy, "BOOK_GENERATED_CONTENT_INVALID");
    expect(message).toContain({ pt: "Uma etapa interna", en: "An internal creation step", es: "una etapa interna" }[lang]);
  });
  it.each([
    ["BOOK_LAYOUT_UNSAFE", "previewNoSafeTextArea"],
    ["BOOK_GENERATED_CONTENT_INVALID", "previewInternalCreationFailed"],
    ["BOOK_STORAGE_TEMPORARY", "previewInternalCreationFailed"],
    ["BOOK_TEXT_INVALID", "previewBookTextInvalid"],
    ["Os versos gerados precisam ser mais curtos para manter a leitura confortável", "previewBookTextInvalid"],
    ["BOOK_REVIEW_INVALID", "previewBookReviewInvalid"],
    ["BOOK_ART_REJECTED", "previewBookArtRejected"],
    ["BOOK_ART_UNAVAILABLE", "previewBookArtUnavailable"],
    ["BOOK_ART_INVALID", "previewBookArtUnavailable"],
  ] as const)("explains %s without exposing provider prose", (code, key) => {
    expect(generationError(copy, `Etapa editorial cover:art: ${code}: internal detail`)).toBe(copy[key]);
  });
  it("keeps an uncertain paid result blocked ahead of other classifications", () => {
    expect(generationError(copy, "GENERATION_OUTCOME_UNKNOWN BOOK_LAYOUT_UNSAFE")).toBe(copy.previewGenerationOutcomeUnknown);
  });
});
