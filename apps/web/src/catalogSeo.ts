import type { CatalogBookSeo } from "./pageMeta";
import catalogPublication from "./catalogPublication20261124.json";

/**
 * Índice fora da página de livro: `toCatalogCard` devolve null para o 3
 * (alfabeto da Sofia), o 4 (Cristobal), o 13 (aniversário da Ester), o 16
 * (Abigail), o 17 (Miriam), o 32 (Nossa Família) e o 48 (Mãos Que Consertam Motores).
 */
export const SKIP_BOOK_INDEXES = new Set([3, 4, 13, 16, 17, 32, 48, 50, 58, 61]);

/** Lê as posições existentes e acrescenta a publicação compartilhada com a vitrine. */
export function parsePtCatalog(source: string): CatalogBookSeo[] {
  const start = source.indexOf("catalog: [");
  if (start < 0) throw new Error("catalog array not found in Landing.tsx");
  const end = source.indexOf("],", start);
  if (end < 0) throw new Error("catalog array end not found in Landing.tsx");
  const body = source.slice(start, end);
  const re = /\{\s*(?:"t"|t):\s*"((?:\\.|[^"\\])*)",\s*(?:"p"|p):\s*"((?:\\.|[^"\\])*)"/g;
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
  for (const book of catalogPublication) {
    if (book.catalog_index !== index) {
      throw new Error(`catalog publication index ${book.catalog_index} does not follow ${index - 1}`);
    }
    books.push({ index, title: book.locales.pt.t, description: book.locales.pt.p });
    index += 1;
  }
  return books;
}
