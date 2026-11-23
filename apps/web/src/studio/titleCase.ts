const SMALL_WORDS = new Set([
  "a", "o", "as", "os", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "com", "para", "por", "um", "uma",
  "the", "and", "of", "in", "on", "at", "to", "for", "with", "an",
  "el", "la", "los", "las", "y", "del", "en", "con", "un", "una",
]);

/**
 * Arruma maiúsculas e minúsculas do título: palavras escritas inteiras em maiúsculas
 * ("ANA CLARA DESENHAR E PINTAR") viram "Ana Clara Desenhar e Pintar", os espaços
 * repetidos somem e a primeira letra do título fica sempre maiúscula.
 * Palavras que já misturam maiúsculas e minúsculas ficam como foram escritas.
 */
export function tidyTitleCase(value: string): string {
  const words = value.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  const isShout = (word: string) => /\p{L}/u.test(word) && word === word.toLocaleUpperCase() && word !== word.toLocaleLowerCase();
  const shouted = words.some((word) => isShout(word) && (word.match(/\p{L}/gu) || []).length > 1);
  const fixed = words.map((word, index) => {
    if (!shouted || !isShout(word)) return word;
    const lower = word.toLocaleLowerCase();
    if (index > 0 && SMALL_WORDS.has(lower.replace(/[^\p{L}]/gu, "")) && !/[:.!?]$/.test(words[index - 1])) return lower;
    return lower.replace(/\p{L}/u, (letter) => letter.toLocaleUpperCase());
  });
  return fixed.join(" ").replace(/\p{L}/u, (letter) => letter.toLocaleUpperCase());
}
