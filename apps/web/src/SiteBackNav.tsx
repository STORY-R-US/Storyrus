import { useResolvedLang, type Lang } from "./i18n/lang";

const COPY: Record<Lang, { back: string; home: string; aria: string }> = {
  pt: { back: "Voltar", home: "Início", aria: "Navegação" },
  en: { back: "Back", home: "Home", aria: "Navigation" },
  es: { back: "Volver", home: "Inicio", aria: "Navegación" },
};

function goBackOrHome() {
  const idx = (window.history.state as { idx?: number } | null)?.idx;
  if (typeof idx === "number" && idx > 0) {
    window.history.back();
    return;
  }
  if (document.referrer) {
    try {
      if (new URL(document.referrer).origin === window.location.origin) {
        window.history.back();
        return;
      }
    } catch {
      /* ignore */
    }
  }
  window.location.assign("/");
}

/** Voltar à página anterior (histórico) ou à inicial — em todas as páginas internas. */
export function SiteBackNav({ className }: { className?: string }) {
  const [lang] = useResolvedLang();
  const t = COPY[lang];
  return (
    <nav
      className={["site-back-nav", className].filter(Boolean).join(" ")}
      aria-label={t.aria}
      data-testid="site-back-nav"
    >
      <button
        type="button"
        className="site-back-prev"
        data-testid="site-back-prev"
        onClick={goBackOrHome}
      >
        {t.back}
      </button>
      <span className="site-back-sep" aria-hidden>
        ·
      </span>
      <a href="/" data-testid="site-back-home">
        {t.home}
      </a>
    </nav>
  );
}
