import { Link } from "react-router-dom";
import logo from "./assets/logo.png";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import { useResolvedLang } from "./i18n/lang";
import "./landing.css";

const COPY = {
  pt: {
    home: "Início", title: "Exemplos Da Plataforma",
    intro: "As fotos, capas e vídeos que aparecem no site são demonstrações feitas pela Story R Us. Eles não são livros de clientes e ficam separados do que você envia no estúdio.",
    detail: "A vitrine com esses exemplos está na página inicial e na página de livros cartoon. A política de privacidade descreve o que fazemos com a foto que você envia de verdade.",
    books: "Ver os livros", cartoon: "Livros Cartoon", privacy: "Privacidade",
  },
  en: {
    home: "Home", title: "Platform Examples",
    intro: "The photos, covers and videos on this website are demonstrations created by Story R Us. They are not customers' books and are kept separate from what you upload to the studio.",
    detail: "You can find these examples on the homepage and the cartoon books page. The privacy policy describes how we use the photo you actually upload.",
    books: "View the books", cartoon: "Cartoon Books", privacy: "Privacy",
  },
  es: {
    home: "Inicio", title: "Ejemplos De La Plataforma",
    intro: "Las fotos, portadas y videos del sitio son demostraciones creadas por Story R Us. No son libros de clientes y se mantienen separados de lo que envías al estudio.",
    detail: "Estos ejemplos están en la página de inicio y en la página de libros cartoon. La política de privacidad describe cómo usamos la foto que envías de verdad.",
    books: "Ver los libros", cartoon: "Libros Cartoon", privacy: "Privacidad",
  },
};

/** Página pública que a política de privacidade cita. As imagens ficam em /exemplos/. */
export function Exemplos() {
  const [lang] = useResolvedLang();
  const copy = COPY[lang];
  usePageMeta(staticPageMeta("/exemplos", lang));
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story R Us" /></Link>
        <nav className="klinks">
          <Link to="/" className="kbtn kbtn-go">{copy.home}</Link>
        </nav>
      </header>
      <main className="ksection" style={{ maxWidth: 720, margin: "0 auto", textAlign: "left" }}>
        <SiteBackNav />
        <h1 className="ktitle" data-testid="exemplos-title">{copy.title}</h1>
        <p className="ksub" style={{ textAlign: "left" }}>
          {copy.intro}
        </p>
        <p>
          {copy.detail}
        </p>
        <p style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/#catalogo" className="kbtn kbtn-primary">{copy.books}</Link>
          <Link to="/cartoon" className="kbtn kbtn-soft">{copy.cartoon}</Link>
          <Link to={lang === "en" ? "/privacy" : "/privacidade"} className="kbtn kbtn-soft">{copy.privacy}</Link>
        </p>
      </main>
    </div>
  );
}
