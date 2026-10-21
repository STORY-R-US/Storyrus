import { Link } from "react-router-dom";
import logo from "./assets/logo.png";
import { NOT_FOUND_PAGE, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

export function NotFound() {
  usePageMeta(NOT_FOUND_PAGE);
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story R Us" /></Link>
      </header>
      <main className="ksection" style={{ textAlign: "center" }}>
        <SiteBackNav className="site-back-nav-center" />
        <h1 className="ktitle" data-testid="not-found-title">Página Não Encontrada</h1>
        <p className="ksub">Esse endereço não existe. Volte à página inicial ou abra o estúdio.</p>
        <p style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/" className="kbtn kbtn-primary" data-testid="not-found-home">Início</Link>
          <Link to="/app" className="kbtn kbtn-soft" data-testid="not-found-studio">Criar Minha História</Link>
        </p>
      </main>
    </div>
  );
}
