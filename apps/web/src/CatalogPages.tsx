import { useEffect, type CSSProperties } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import logo from "./assets/logo.png";
import "./landing.css";
import { NotFound } from "./NotFound";
import { bookPageMeta, categoryPageMeta, NOT_FOUND_PAGE, staticPageMeta, usePageMeta } from "./pageMeta";
import { useResolvedLang, type Lang } from "./i18n/lang";
import { SiteBackNav } from "./SiteBackNav";
import {
  CatalogBookCard,
  catalogCategory,
  catalogEntry,
  catalogPageCopy,
  catalogSections,
} from "./Landing";

function useSiteLang() {
  const [lang, setLang] = useResolvedLang();
  useEffect(() => {
    try {
      const theme = localStorage.getItem("theme");
      if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
    } catch { /* ignore */ }
  }, []);
  return [lang, setLang] as const;
}

function CatalogBannerNav({ lang }: { lang: Lang }) {
  const copy = catalogPageCopy(lang);
  const sections = catalogSections(lang);
  const extras = [
    { href: "/#como", label: copy.hiw, color: "#7aa2ff" },
    { href: "/#passo", label: copy.passo, color: "#f08a4b" },
    { href: "/cartoon", label: copy.cartoon, color: "#3ecf8e" },
    { href: "/#videos", label: copy.videos, color: "#e07a9a" },
    { href: "/#reviews", label: copy.reviews, color: "#f4b740" },
  ];
  return (
    <nav className="catalog-banner-nav" aria-label={copy.cats}>
      {sections.map((section) => (
        <Link key={section.id} to={`/catalogo#${section.id}`} className="kcat-btn">
          <span className="kcat-dot" style={{ background: section.color, boxShadow: `0 0 10px ${section.color}` }} />
          {section.name}
        </Link>
      ))}
      {extras.map((item) => (
        <a key={item.label} href={item.href} className="kcat-btn">
          <span className="kcat-dot" style={{ background: item.color, boxShadow: `0 0 10px ${item.color}` }} />
          {item.label}
        </a>
      ))}
    </nav>
  );
}

function LangSwitch({ lang, setLang }: { lang: Lang; setLang: (lang: Lang) => void }) {
  return (
    <div className="lang" role="group" aria-label="Idioma / Language / Idioma">
      <button className={lang === "pt" ? "on" : ""} onClick={() => setLang("pt")} data-testid="landing-lang-pt">PT</button>
      <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")} data-testid="landing-lang-en">EN</button>
      <button className={lang === "es" ? "on" : ""} onClick={() => setLang("es")} data-testid="landing-lang-es">ES</button>
    </div>
  );
}

function CatalogSectionTitle({
  name,
  color,
  as: Tag = "h2",
}: {
  name: string;
  color: string;
  as?: "h1" | "h2";
}) {
  return (
    <Tag className="catalog-section-title">
      <span className="kcat-btn catalog-section-pill">
        <span className="kcat-dot" style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
        {name}
      </span>
    </Tag>
  );
}

export function CatalogPage() {
  usePageMeta(staticPageMeta("/catalogo"));
  const [lang, setLang] = useSiteLang();
  const copy = catalogPageCopy(lang);
  const sections = catalogSections(lang);
  const { hash } = useLocation();
  useEffect(() => {
    const id = hash.replace("#", "");
    if (!id) return;
    const scrollToSection = () => {
      const el = document.getElementById(id);
      if (!el) return false;
      const header = document.querySelector(".catalog-knav");
      const offset = header ? header.getBoundingClientRect().height + 12 : 0;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top });
      return true;
    };
    // Retenta: capas/lazy-load mudam a altura depois do 1º paint.
    scrollToSection();
    const t1 = window.setTimeout(scrollToSection, 80);
    const t2 = window.setTimeout(scrollToSection, 320);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [sections, hash]);
  return (
    <div className="kid">
      <header className="knav catalog-knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story.R.Us" /></Link>
        <LangSwitch lang={lang} setLang={setLang} />
        <CatalogBannerNav lang={lang} />
      </header>
      <main className="ksection catalog-page" id="catalogo">
        <h1 className="ktitle">{copy.title}</h1>
        {sections.map((section) => (
          <section key={section.id} id={section.id} className="catalog-section" style={{ "--group": section.color } as CSSProperties}>
            {section.subs.map((sub) => (
              <div key={sub.id} id={`${section.id}-${sub.id}`} className="catalog-sub">
                <h3 className="catalog-sub-title">{sub.name}</h3>
                <div className="cat-grid">
                  {sub.books.map((book) => (
                    <CatalogBookCard key={book.catalogI} book={book} lang={lang} personalize={copy.personalize} />
                  ))}
                </div>
              </div>
            ))}
          </section>
        ))}
      </main>
    </div>
  );
}

export function CategoryCatalogPage() {
  const [lang, setLang] = useSiteLang();
  const params = useParams();
  const section = catalogCategory(lang, params.categoria ?? "");
  usePageMeta(section ? categoryPageMeta(section.id, section.name) : NOT_FOUND_PAGE);
  if (!section) return <NotFound />;
  const copy = catalogPageCopy(lang);
  return (
    <div className="kid">
      <header className="knav catalog-knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story.R.Us" /></Link>
        <LangSwitch lang={lang} setLang={setLang} />
        <CatalogBannerNav lang={lang} />
      </header>
      <main className="ksection catalog-page" id="catalogo">
        <section className="catalog-section" id={section.id} style={{ "--group": section.color } as CSSProperties}>
          <CatalogSectionTitle name={section.name} color={section.color} as="h1" />
          {section.subs.length > 0 ? (
            section.subs.map((sub) => (
              <div key={sub.id} id={`${section.id}-${sub.id}`} className="catalog-sub">
                <h3 className="catalog-sub-title">{sub.name}</h3>
                <div className="cat-grid">
                  {sub.books.map((book) => (
                    <CatalogBookCard key={book.catalogI} book={book} lang={lang} personalize={copy.personalize} />
                  ))}
                </div>
              </div>
            ))
          ) : (
            <p className="kcat-empty">{copy.empty}</p>
          )}
        </section>
      </main>
    </div>
  );
}

export function BookPage() {
  const [lang, setLang] = useSiteLang();
  const params = useParams();
  const index = Number(params.indice);
  const book = Number.isInteger(index) ? catalogEntry(lang, index) : null;
  usePageMeta(
    book
      ? bookPageMeta({ index, title: book.t, description: book.story || book.t })
      : NOT_FOUND_PAGE,
  );
  if (!book) return <NotFound />;
  const copy = catalogPageCopy(lang);
  return (
    <div className="kid">
      <header className="knav catalog-knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story.R.Us" /></Link>
        <LangSwitch lang={lang} setLang={setLang} />
        <CatalogBannerNav lang={lang} />
      </header>
      <main className="ksection book-page" id="catalogo">
        <SiteBackNav />
        <div className="book-page-card">
          <CatalogBookCard book={book} lang={lang} personalize={copy.personalize} linkBook={false} layout="page" />
        </div>
      </main>
    </div>
  );
}
