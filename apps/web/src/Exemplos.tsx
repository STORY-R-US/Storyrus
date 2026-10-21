import { Link } from "react-router-dom";
import logo from "./assets/logo.png";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

const PAGE = staticPageMeta("/exemplos");

/** Página pública que a política de privacidade cita. As imagens ficam em /exemplos/. */
export function Exemplos() {
  usePageMeta(PAGE);
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story R Us" /></Link>
        <nav className="klinks">
          <Link to="/" className="kbtn kbtn-go">Início</Link>
        </nav>
      </header>
      <main className="ksection" style={{ maxWidth: 720, margin: "0 auto", textAlign: "left" }}>
        <SiteBackNav />
        <h1 className="ktitle" data-testid="exemplos-title">Exemplos Da Plataforma</h1>
        <p className="ksub" style={{ textAlign: "left" }}>
          As fotos, capas e vídeos que aparecem no site são demonstrações feitas pela Story R Us.
          Eles não são livros de clientes e ficam separados do que você envia no estúdio.
        </p>
        <p>
          A vitrine com esses exemplos está na página inicial e na página de livros cartoon.
          A política de privacidade descreve o que fazemos com a foto que você envia de verdade.
        </p>
        <p style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/#catalogo" className="kbtn kbtn-primary">Ver os livros</Link>
          <Link to="/cartoon" className="kbtn kbtn-soft">Livros Cartoon</Link>
          <Link to="/privacidade" className="kbtn kbtn-soft">Privacidade</Link>
        </p>
      </main>
    </div>
  );
}
