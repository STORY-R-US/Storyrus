import { Link } from "react-router-dom";
import logo from "./assets/logo.png";
import { NOT_FOUND_PAGE, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import { useResolvedLang } from "./i18n/lang";
import "./landing.css";

export function NotFound() {
  const [lang] = useResolvedLang();
  const copy = {
    pt: { title: "Página Não Encontrada", description: "Esse endereço não existe. Volte à página inicial ou abra o estúdio.", home: "Início", create: "Criar Minha História" },
    en: { title: "Page Not Found", description: "This address does not exist. Return to the homepage or open the studio.", home: "Home", create: "Create My Story" },
    es: { title: "Página No Encontrada", description: "Esta dirección no existe. Vuelve a la página de inicio o abre el estudio.", home: "Inicio", create: "Crear Mi Historia" },
  }[lang];
  usePageMeta({ ...NOT_FOUND_PAGE, title: copy.title, description: copy.description });
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story R Us" /></Link>
      </header>
      <main className="ksection" style={{ textAlign: "center" }}>
        <SiteBackNav className="site-back-nav-center" />
        <h1 className="ktitle" data-testid="not-found-title">{copy.title}</h1>
        <p className="ksub">{copy.description}</p>
        <p style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/" className="kbtn kbtn-primary" data-testid="not-found-home">{copy.home}</Link>
          <Link to="/app" className="kbtn kbtn-soft" data-testid="not-found-studio">{copy.create}</Link>
        </p>
      </main>
    </div>
  );
}
