import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { CatalogCardBook, catalogSections } from "./Landing";
import type { Lang } from "./i18n/lang";

const COPY = {
  pt: { more: "Mostrar mais livros", next: "Próxima data", empty: "Nenhum livro disponível nesta seleção.", reset: "Limpar filtros", catalog: "Ver todo o catálogo", create: "Criar minha história" },
  en: { more: "Show more books", next: "Coming up", empty: "No books available in this selection.", reset: "Clear filters", catalog: "View the full catalog", create: "Create my story" },
  es: { more: "Mostrar más libros", next: "Próxima fecha", empty: "No hay libros disponibles en esta selección.", reset: "Borrar filtros", catalog: "Ver todo el catálogo", create: "Crear mi historia" },
};

type Sections = ReturnType<typeof catalogSections>;
type Shelf = { id: string; name: string; color: string; note?: string; books: CatalogCardBook[]; subs: { id: string; name: string; books: CatalogCardBook[] }[] };
/** As datas comemorativas abrem o catálogo, com a mais próxima em destaque. */
const LEAD_SECTION = "ocasioes";
const bookKey = (book: CatalogCardBook) => book.catalogI ?? book.t;

/** Uma faixa por categoria; cada livro aparece uma vez só, na categoria do seu tema. */
function catalogShelves(sections: Sections, subSections: Sections, nextLabel: string): Shelf[] {
  const lead = sections.find((section) => section.id === LEAD_SECTION);
  const nearest = lead?.subs[0];
  const home = new Map<string | number, string>();
  for (const book of nearest?.books ?? []) home.set(bookKey(book), LEAD_SECTION);
  for (const section of sections) {
    for (const sub of section.subs) {
      for (const book of sub.books) {
        if (sub.id === book.theme && !home.has(bookKey(book))) home.set(bookKey(book), section.id);
      }
    }
  }
  for (const section of sections) {
    for (const book of section.books) {
      if (!home.has(bookKey(book))) home.set(bookKey(book), section.id);
    }
  }
  const ordered = lead ? [lead, ...sections.filter((section) => section !== lead)] : sections;
  return ordered.flatMap((section) => {
    const books = section.books.filter((book) => home.get(bookKey(book)) === section.id);
    if (!books.length) return [];
    const note = section === lead && nearest ? `${nextLabel}: ${nearest.name}` : undefined;
    // Subcategorias como no menu; cada livro fica na primeira subcategoria que o contém.
    const placed = new Set<string | number>();
    const subs = (subSections.find((item) => item.id === section.id) ?? section).subs.flatMap((sub) => {
      const own = sub.books
        .filter((book) => home.get(bookKey(book)) === section.id && !placed.has(bookKey(book)))
        .map((book) => books.find((item) => bookKey(item) === bookKey(book)) ?? book);
      own.forEach((book) => placed.add(bookKey(book)));
      return own.length ? [{ id: sub.id, name: sub.name, books: own }] : [];
    });
    const rest = books.filter((book) => !placed.has(bookKey(book)));
    if (rest.length) subs.push({ id: "outros", name: "", books: rest });
    return [{ id: section.id, name: section.name, color: section.color, note, books: subs.flatMap((sub) => sub.books), subs }];
  });
}

/** One inventory, shared by all locales; pagination never repeats a book. */
export function CatalogBrowser({ books, sections = [], subSections, aliases = [], hash = "", showAll = false, lang, renderBook }: {
  books: CatalogCardBook[];
  sections?: Sections;
  /** Subcategorias mostradas dentro de cada faixa (as do menu); sem isso, usa as de `sections`. */
  subSections?: Sections;
  /** Página do catálogo: todos os livros de uma vez, sem "Mostrar mais". */
  showAll?: boolean;
  /** Seleções extras aceitas no endereço (ex.: o grupo de duplas do menu). */
  aliases?: { id: string; name: string; color: string; books: CatalogCardBook[] }[];
  hash?: string;
  lang: Lang;
  renderBook: (book: CatalogCardBook) => ReactNode;
}) {
  const [group, setGroup] = useState(hash.replace(/^#/, ""));
  const [more, setLimit] = useState(12);
  const limit = showAll ? Number.POSITIVE_INFINITY : more;
  useEffect(() => { setGroup(hash.replace(/^#/, "")); setLimit(12); }, [hash]);
  const t = COPY[lang];
  const options = [
    ...sections.flatMap((section) => [
      { id: section.id, name: section.name, color: section.color, books: section.books },
      ...section.subs.map((sub) => ({ id: `${section.id}-${sub.id}`, name: `${section.name} — ${sub.name}`, color: section.color, books: sub.books })),
    ]),
    ...aliases,
  ];
  const selected = options.find((option) => option.id === group);
  const unique = [...new Map((selected?.books ?? books).map((book) => [bookKey(book), book])).values()];
  const shelves = !selected && sections.length ? catalogShelves(sections, subSections ?? sections, t.next) : [];
  const matches = shelves.length ? shelves.flatMap((shelf) => shelf.books) : unique;
  const shownKeys = new Set(matches.slice(0, limit).map(bookKey));
  const card = (book: CatalogCardBook) => <div className="catalog-result" key={bookKey(book)}>{renderBook(book)}</div>;
  return <div className="catalog-browser">
    {selected && <h2 className="catalog-sub-title catalog-bar" id={selected.id} style={{ "--group": selected.color } as CSSProperties}>
      <span className="catalog-bar-name">{selected.name}</span>
    </h2>}
    {shelves.length ? shelves.map((shelf) => {
      const visible = shelf.subs
        .map((sub) => ({ ...sub, books: sub.books.filter((book) => shownKeys.has(bookKey(book))) }))
        .filter((sub) => sub.books.length);
      if (!visible.length) return null;
      return <section className={`catalog-shelf${shelf.note ? " is-lead" : ""}`} key={shelf.id} data-shelf={shelf.id} style={{ "--group": shelf.color } as CSSProperties}>
        <h2 className="catalog-bar">
          <span className="catalog-bar-name">{shelf.name}</span>
          {shelf.note && <span className="catalog-bar-note">{shelf.note}</span>}
        </h2>
        <div className="cat-grid catalog-subs">
          {visible.map((sub) => <div className={`catalog-subgroup span-${Math.min(sub.books.length, 3)}`} key={sub.id} data-sub={sub.id}>
            {sub.name ? <h3 className="catalog-subgroup-title">{sub.name}</h3> : <span className="catalog-subgroup-title" aria-hidden="true">&nbsp;</span>}
            {sub.books.map(card)}
          </div>)}
        </div>
      </section>;
    }) : matches.length ? <div className="cat-grid">{matches.slice(0, limit).map(card)}</div> : <p className="kcat-empty">{t.empty}</p>}
    <div className="catalog-actions">
      {matches.length > limit && <button type="button" className="kbtn" data-testid="catalog-more" onClick={() => setLimit((value) => value + 12)}>{t.more}</button>}
      {selected && <button type="button" className="kbtn" onClick={() => { setGroup(""); setLimit(12); }}>{t.reset}</button>}
      {!matches.length && <><Link to="/catalogo" className="kbtn">{t.catalog}</Link><Link to="/app" className="kbtn kbtn-primary">{t.create}</Link></>}
    </div>
  </div>;
}
