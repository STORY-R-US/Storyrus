import type { CatalogBookSeo } from "./pageMeta";

/**
 * Índice fora da página de livro: `toCatalogCard` devolve null para o 10
 * (Nano), o 13 (aniversário da Ester), o 16 (Abigail), o 17 (Miriam)
 * e o 32 (Nossa Família).
 */
export const SKIP_BOOK_INDEXES = new Set([10, 13, 16, 17, 32]);

/** Lê o catálogo em português de Landing.tsx (primeiro array `catalog:`). */
export function parsePtCatalog(source: string): CatalogBookSeo[] {
  const start = source.indexOf("catalog: [");
  if (start < 0) throw new Error("catalog array not found in Landing.tsx");
  const end = source.indexOf("],", start);
  if (end < 0) throw new Error("catalog array end not found in Landing.tsx");
  const body = source.slice(start, end);
  const re = /\{\s*t:\s*"((?:\\.|[^"\\])*)",\s*p:\s*"((?:\\.|[^"\\])*)"/g;
  const books: CatalogBookSeo[] = [];
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = re.exec(body))) {
    if (!SKIP_BOOK_INDEXES.has(index)) {
      books.push({
        index,
        title: match[1].replace(/\\"/g, '"'),
        description: match[2].replace(/\\"/g, '"'),
      });
    }
    index += 1;
  }
  if (books.length < 20) {
    throw new Error(`catalog SEO parse returned ${books.length} books`);
  }
  return books;
}
