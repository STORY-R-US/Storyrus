import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { CatalogCardBook, catalogSections } from "./Landing";
import type { Lang } from "./i18n/lang";

const COPY = {
  pt: { search: "Buscar livro", category: "Categoria", all: "Todas as categorias", more: "Mostrar mais livros", count: "livros encontrados", empty: "Nenhum livro disponível nesta seleção.", reset: "Limpar filtros", catalog: "Ver todo o catálogo", create: "Criar minha história" },
  en: { search: "Search books", category: "Category", all: "All categories", more: "Show more books", count: "books found", empty: "No books available in this selection.", reset: "Clear filters", catalog: "View the full catalog", create: "Create my story" },
  es: { search: "Buscar libro", category: "Categoría", all: "Todas las categorías", more: "Mostrar más libros", count: "libros encontrados", empty: "No hay libros disponibles en esta selección.", reset: "Borrar filtros", catalog: "Ver todo el catálogo", create: "Crear mi historia" },
};
const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();

/** One inventory, shared by all locales; pagination never repeats a book. */
export function CatalogBrowser({ books, sections = [], hash = "", lang, renderBook }: {
  books: CatalogCardBook[];
  sections?: ReturnType<typeof catalogSections>;
  hash?: string;
  lang: Lang;
  renderBook: (book: CatalogCardBook) => ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState(hash.replace(/^#/, ""));
  const [limit, setLimit] = useState(12);
  useEffect(() => { setGroup(hash.replace(/^#/, "")); setLimit(12); }, [hash]);
  const t = COPY[lang];
  const options = sections.flatMap((section) => [
    { id: section.id, name: section.name, books: section.books },
    ...section.subs.map((sub) => ({ id: `${section.id}-${sub.id}`, name: `${section.name} — ${sub.name}`, books: sub.books })),
  ]);
  const selected = options.find((option) => option.id === group);
  const unique = [...new Map((selected?.books ?? books).map((book) => [book.catalogI ?? book.t, book])).values()];
  const matches = unique.filter((book) => normalize(`${book.t} ${book.tag ?? ""} ${book.story ?? ""}`).includes(normalize(query.trim())));
  return <div className="catalog-browser">
    <div className="catalog-filters">
      <label>{t.search}<input type="search" value={query} placeholder={t.search} onChange={(event) => { setQuery(event.target.value); setLimit(12); }} data-testid="catalog-search" /></label>
      {sections.length > 0 && <label>{t.category}<select value={selected?.id ?? ""} onChange={(event) => { setGroup(event.target.value); setLimit(12); }} data-testid="catalog-category">
        <option value="">{t.all}</option>
        {options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
      </select></label>}
    </div>
    {selected && <h2 className="catalog-sub-title" id={selected.id}>{selected.name}</h2>}
    <p className="catalog-count" role="status">{matches.length} {t.count}</p>
    {matches.length ? <div className="cat-grid">{matches.slice(0, limit).map((book) => <div className="catalog-result" key={book.catalogI ?? book.t}>{renderBook(book)}</div>)}</div> : <p className="kcat-empty">{t.empty}</p>}
    <div className="catalog-actions">
      {matches.length > limit && <button type="button" className="kbtn" data-testid="catalog-more" onClick={() => setLimit((value) => value + 12)}>{t.more}</button>}
      {(query || selected) && <button type="button" className="kbtn" onClick={() => { setQuery(""); setGroup(""); setLimit(12); }}>{t.reset}</button>}
      {!matches.length && <><Link to="/catalogo" className="kbtn">{t.catalog}</Link><Link to="/app" className="kbtn kbtn-primary">{t.create}</Link></>}
    </div>
  </div>;
}
