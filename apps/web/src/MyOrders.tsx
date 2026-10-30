import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { accountAccess, accountGateHref } from "./Auth";
import { api, getToken } from "./api";
import type { Project } from "./types";
import { SiteBackNav } from "./SiteBackNav";
import { useResolvedLang } from "./i18n/lang";
import { purchaseCopy } from "./studio/purchaseCopy";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import "./landing.css";
import "./studio.css";
import logo from "./assets/logo.png";
import { StudioStageHeading } from "./studio/StudioStageHeading";

export function MyOrders() {
  usePageMeta(staticPageMeta("/meus-pedidos"));
  const [lang] = useResolvedLang();
  const t = purchaseCopy(lang);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gate, setGate] = useState<"loading" | "ok" | "entrar" | "cadastro">(
    getToken() ? "loading" : "entrar",
  );
  const [attempt, setAttempt] = useState(0);
  const [removing, setRemoving] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  useEffect(() => {
    if (gate !== "loading" && gate !== "ok") return;
    let cancelled = false;
    async function load() {
      try {
        const me = await api.me();
        if (cancelled) return;
        const access = accountAccess(me);
        if (access === "guest") api.logout();
        if (access !== "ok") {
          setGate("cadastro");
          return;
        }
        const next = await api.myProjects();
        if (!cancelled) {
          setProjects(next);
          setError(null);
          setGate("ok");
        }
      } catch (err) {
        if (!cancelled) {
          const message = (err as Error).message;
          if (/^401:/.test(message)) {
            api.logout();
            setGate("entrar");
          } else {
            setError(message);
            setGate("ok");
          }
        }
      }
    }
    void load();
    const id = window.setInterval(() => {
      void load();
    }, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [gate, attempt]);
  if (gate === "entrar") return <Navigate to="/entrar?next=%2Fmeus-pedidos" replace />;
  if (gate === "cadastro") return <Navigate to={accountGateHref("/meus-pedidos")} replace />;
  if (gate === "loading") return null;
  async function removeProject(id: string) {
    if (!window.confirm(t.deleteConfirm)) return;
    setRemoving(id);
    setError(null);
    try {
      await api.deleteProject(id);
      setProjects((prev) => prev?.filter((item) => item.id !== id) ?? null);
    } catch (err) {
      setError((err as Error).message || t.deleteFailed);
    } finally {
      setRemoving(null);
    }
  }
  function status(p: Project) {
    if (p.book_profile?.credits_fallback) return t.steps[0];
    if (p.book_approved_at && p.purchase_flow?.full_book_ready_at)
      return t.approved;
    if (p.purchase_flow?.full_book_ready_at) return t.full;
    if (p.purchase_flow?.stage === "generating_book") return t.generating;
    if (p.purchase_flow?.stage === "awaiting_payment_confirmation")
      return t.paymentPending;
    if (p.purchase_flow?.preview_approved_at) return t.quotation;
    if (p.purchase_flow?.preview_ready_at || p.ebook_url) return t.steps[0];
    return t.preview;
  }
  return (
    <div className="studio-app kid studio-orders-page">
      <header className="khead"><div className="khead-inner">
        <a href="/" className="kbrand" aria-label="Story R Us"><img className="hdr-logo" src={logo} alt="Story R Us" /></a>
      </div></header>
      <div className="ksection site-back-wrap"><SiteBackNav /></div>
      <main className="studio-page"><section className="studio-card purchase-orders">
        <StudioStageHeading title={t.myOrders} level="h1" illustration={3}>
          <p>{lang === "pt" ? "Acompanhe seus livros e retome a criação de onde parou." : lang === "en" ? "Follow your books and pick up creating where you left off." : "Sigue tus libros y continúa la creación donde la dejaste."}</p>
        </StudioStageHeading>
        <p className="studio-slogan"><a href={lang === "en" ? "/privacy" : "/privacidade"}>{lang === "pt" ? "Seus dados e como pedir a exclusão" : lang === "en" ? "Your information and deletion rights" : "Tus datos y cómo solicitar su eliminación"}</a></p>
        <a className="kbtn kbtn-primary" href="/app">
          {t.create}
        </a>
        {error && (
          <p className="studio-error" role="alert">
            {error}
            <button className="kbtn kbtn-soft" type="button" onClick={() => setAttempt((n) => n + 1)}>
              {t.retry}
            </button>
          </p>
        )}
        {!projects && !error && <p className="studio-state-message" role="status">{t.loading}</p>}
        {projects?.length === 0 && <p className="studio-state-message">{t.empty}</p>}
        <div className="purchase-order-list">
          {projects?.map((p) => (
            <article key={p.id}>
              <p className="muted">
                {new Date(p.created_at).toLocaleDateString(
                  lang === "pt" ? "pt-BR" : lang,
                )}
              </p>
              <h2>
                {p.purchase_flow?.title ||
                  p.story_text?.match(/^T[íi]tulo:\s*([^\n]+)/i)?.[1] ||
                  p.child_name ||
                  t.steps[0]}
              </h2>
              <p className="purchase-order-status" role="status">{status(p)}</p>
              <p>
                {p.book_size === "P" ? "15 × 15 cm" : "20 × 20 cm"} ·{" "}
                {p.cover_type === "hard" ? t.hard : t.soft}
              </p>
              <a
                className="kbtn kbtn-primary"
                href={`/app?projeto=${encodeURIComponent(p.id)}`}
              >
                {lang === "en" ? "View order" : "Ver pedido"} →
              </a>
              <button
                type="button" className="kbtn kbtn-soft" data-testid="order-revoke"
                disabled={removing === p.id || revoking === p.id || !!p.processing_revoked_at}
                onClick={async () => {
                  setRevoking(p.id); setError(null);
                  try {
                    const updated = await api.revokeBookMedia(p.id);
                    setProjects((prev) => prev?.map((item) => item.id === p.id ? updated : item) ?? null);
                  } catch (reason) { setError((reason as Error).message); }
                  finally { setRevoking(null); }
                }}
              >{p.processing_revoked_at
                ? (lang === "pt" ? "Novas gerações bloqueadas" : lang === "en" ? "Further generation blocked" : "Nuevas generaciones bloqueadas")
                : (lang === "pt" ? "Retirar autorização de novos usos" : lang === "en" ? "Withdraw authorization for further use" : "Retirar autorización para nuevos usos")}</button>
              <button
                type="button"
                className="kbtn kbtn-soft purchase-order-delete"
                data-testid="order-delete"
                disabled={removing === p.id || revoking === p.id}
                onClick={() => void removeProject(p.id)}
              >
                {removing === p.id ? t.deleteBusy : t.deleteProject}
              </button>
            </article>
          ))}
        </div>
      </section></main>
    </div>
  );
}
