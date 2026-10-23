import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import logo from "./assets/logo.png";
import { applyDocumentLang, useResolvedLang } from "./i18n/lang";
import { LEGAL_CONTACT, legalDocument, legalLang, type LegalBlock } from "./legalCopy";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

function Block({ block }: { block: LegalBlock }) {
  if (block.type === "h") return <h2>{block.text}</h2>;
  if (block.type === "ul") {
    return (
      <ul>
        {block.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    );
  }
  if (block.type === "link") {
    return (
      <p>
        {block.before}
        <Link to={block.href}>{block.label}</Link>
        {block.after}
      </p>
    );
  }
  if (block.type === "contact") {
    return (
      <p>
        {block.before}
        <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>
      </p>
    );
  }
  return <p>{block.text}</p>;
}

export function Legal({ kind }: { kind: "privacy" | "terms" }) {
  const { pathname } = useLocation();
  const [siteLang] = useResolvedLang();
  const lang = legalLang(pathname, siteLang);
  const doc = legalDocument(lang, kind);
  useEffect(() => {
    const previous = document.documentElement.lang;
    applyDocumentLang(lang);
    return () => {
      document.documentElement.lang = previous;
    };
  }, [lang]);
  usePageMeta(
    kind === "privacy"
      ? staticPageMeta(pathname === "/privacy" ? "/privacy" : "/privacidade")
      : staticPageMeta(pathname === "/terms" ? "/terms" : "/termos"),
  );
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand">
          <img src={logo} alt="Story R Us" />
        </Link>
        <nav className="klinks">
          <Link to="/" className="kbtn kbtn-go">
            {doc.home}
          </Link>
        </nav>
      </header>
      <main className="ksection" style={{ maxWidth: 720, margin: "0 auto", textAlign: "left" }}>
        <SiteBackNav lang={lang} />
        <h1 className="ktitle">{doc.title}</h1>
        <p className="ksub" style={{ textAlign: "left" }}>
          {doc.updated}
        </p>
        {doc.blocks.map((block, index) => (
          <Block key={`${block.type}-${index}`} block={block} />
        ))}
        <p style={{ marginTop: 28 }}>
          <Link to="/" className="kbtn kbtn-primary">
            {doc.back}
          </Link>
        </p>
      </main>
    </div>
  );
}
