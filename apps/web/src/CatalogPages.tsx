import { useState, useEffect, type CSSProperties } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import logo from "./assets/logo.png";
import "./landing.css";
import { NotFound } from "./NotFound";
import { catalogModel, catalogModelId } from "./catalogModel";
import { bookPageMeta, categoryPageMeta, staticPageMeta, usePageMeta } from "./pageMeta";
import { useResolvedLang, type Lang } from "./i18n/lang";
import { SiteBackNav } from "./SiteBackNav";
import { CatalogBrowser } from "./CatalogBrowser";
import {
  CatalogBookCard,
  catalogCategory,
  catalogCoverFile,
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

function ThemeIcon({ theme }: { theme: "light" | "dark" }) {
  if (theme === "dark") {
    return (
      <svg className="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2.5v2.4M12 19.1v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7" />
      </svg>
    );
  }
  return (
    <svg className="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <path d="M20 15A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 11z" />
    </svg>
  );
}

function CatalogSiteHeader({ lang, setLang }: { lang: Lang; setLang: (lang: Lang) => void }) {
  const { search } = useLocation();
  const catalogHref = new URLSearchParams(search).get("modo") === "cartoon" ? "/catalogo?modo=cartoon" : "/catalogo";
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const stored = localStorage.getItem("theme");
      if (stored === "light" || stored === "dark") return stored;
    } catch { /* ignore */ }
    return "dark";
  });
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
  }, [theme]);
  const copy = catalogPageCopy(lang);
  const closeMenu = () => setMenuOpen(false);
  const links = [
    { href: catalogHref, label: copy.cats, color: "#9b8cff" },
    { href: "/#como", label: copy.hiw, color: "#7aa2ff" },
    { href: "/#passo", label: copy.passo, color: "#f08a4b" },
    { href: "/cartoon", label: copy.cartoon, color: "#3ecf8e" },
    { href: "/#videos", label: copy.videos, color: "#e07a9a" },
    { href: "/#reviews", label: copy.reviews, color: "#f4b740" },
  ];
  return (
    <header className="khead">
      <div className="khead-inner">
        <Link to="/" className="kbrand"><img src={logo} alt="Story.R.Us" /></Link>
        <div className="khead-main">
          <div className="khead-bar">
            <div className="khead-bar-inner">
              <nav className="kcats" aria-label={copy.cats}>
                {links.map((item) => (
                  <Link key={item.href} to={item.href} className="kcat-btn" style={{ "--cat": item.color } as CSSProperties} onClick={closeMenu}>
                    <span className="kcat-dot" style={{ background: item.color, boxShadow: `0 0 10px ${item.color}` }} />
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
        <div className="khead-actions">
          <div className="khead-utils">
            <button className="theme-toggle" type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={copy.theme}>
              <ThemeIcon theme={theme} />
              <span className="theme-toggle-label">{theme === "dark" ? copy.themeLight : copy.themeDark}</span>
            </button>
            <LangSwitch lang={lang} setLang={setLang} />
            <div className="khead-links">
              <Link to="/entrar" className="kbtn kbtn-login">{copy.login}</Link>
              <Link to="/cadastro" className="kbtn kbtn-primary">{copy.signup}</Link>
            </div>
          </div>
          <button className="khamb" type="button" aria-label={copy.menu} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>☰</button>
        </div>
        <nav className={`kmobile${menuOpen ? " open" : ""}`} hidden={!menuOpen}>
          <div className="kmobile-tools"><button type="button" className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            <ThemeIcon theme={theme} /><span className="theme-toggle-label">{theme === "dark" ? copy.themeLight : copy.themeDark}</span>
          </button></div>
          {links.map((item) => (
            <Link key={item.href} to={item.href} className="kmobile-link" onClick={closeMenu}>{item.label}</Link>
          ))}
        </nav>
      </div>
    </header>
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
  const [lang, setLang] = useSiteLang();
  usePageMeta(staticPageMeta("/catalogo", lang));
  const copy = catalogPageCopy(lang);
  const { hash, search } = useLocation();
  const cartoon = new URLSearchParams(search).get("modo") === "cartoon";
  const sections = catalogSections(lang, cartoon ? "cartoon" : "photo");
  return (
    <div className="kid">
      <CatalogSiteHeader lang={lang} setLang={setLang} />
      <main className="ksection catalog-page" id="catalogo">
        <h1 className="ktitle">{copy.title}</h1>
        <CatalogBrowser books={sections.flatMap((section) => section.books)} sections={sections} hash={hash} lang={lang}
          renderBook={(book) => <CatalogBookCard book={book} lang={lang} personalize={copy.personalize} modo={cartoon ? "cartoon" : "realista"} />} />
      </main>
    </div>
  );
}

export function CategoryCatalogPage() {
  const [lang, setLang] = useSiteLang();
  const params = useParams();
  const { search } = useLocation();
  const cartoon = new URLSearchParams(search).get("modo") === "cartoon";
  const section = catalogCategory(lang, params.categoria ?? "", cartoon ? "cartoon" : "photo");
  usePageMeta(section ? categoryPageMeta(section.id, section.name, lang) : null);
  if (!section) return <NotFound />;
  const copy = catalogPageCopy(lang);
  return (
    <div className="kid">
      <CatalogSiteHeader lang={lang} setLang={setLang} />
      <main className="ksection catalog-page" id="catalogo">
        <section className="catalog-section" id={section.id} style={{ "--group": section.color } as CSSProperties}>
          <CatalogSectionTitle name={section.name} color={section.color} as="h1" />
          <CatalogBrowser key={section.id} books={section.books} lang={lang}
            renderBook={(book) => <CatalogBookCard book={book} lang={lang} personalize={copy.personalize} modo={cartoon ? "cartoon" : "realista"} />} />
        </section>
      </main>
    </div>
  );
}

export function BookPage() {
  const [lang, setLang] = useSiteLang();
  const params = useParams();
  const index = Number(params.indice);
  const { search } = useLocation();
  const cartoon = new URLSearchParams(search).get("modo") === "cartoon";
  const entry = Number.isInteger(index) ? catalogEntry(lang, index) : null;
  const model = cartoon ? catalogModel(catalogModelId(index, true)) : undefined;
  const book = entry && (!cartoon || model) ? {...entry, img: catalogCoverFile(index, lang, cartoon ? "cartoon" : "photo")} : null;
  usePageMeta(
    book
      ? bookPageMeta({ index, title: book.t, description: book.story || book.t })
      : null,
  );
  if (!book) return <NotFound />;
  const copy = catalogPageCopy(lang);
  return (
    <div className="kid">
      <CatalogSiteHeader lang={lang} setLang={setLang} />
      <main className="ksection book-page" id="catalogo">
        <SiteBackNav />
        <div className="book-page-card">
          <CatalogBookCard book={book} lang={lang} personalize={copy.personalize} linkBook={false} layout="page" modo={cartoon ? "cartoon" : "realista"} />
        </div>
      </main>
    </div>
  );
}
