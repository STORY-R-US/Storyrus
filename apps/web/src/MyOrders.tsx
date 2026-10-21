import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, getToken } from "./api";
import type { Project } from "./types";
import { SiteBackNav } from "./SiteBackNav";
import { useResolvedLang } from "./i18n/lang";
import { purchaseCopy } from "./studio/purchaseCopy";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import "./landing.css";
import "./studio.css";

export function MyOrders() {
  usePageMeta(staticPageMeta("/meus-pedidos"));
  const [lang] = useResolvedLang();
  const t = purchaseCopy(lang);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [login, setLogin] = useState(!getToken());
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (login) return;
    let cancelled = false;
    async function load() {
      try {
        const me = await api.me();
        if (cancelled) return;
        if (me.is_guest || !me.email_verified) {
          setLogin(true);
          return;
        }
        const next = await api.myProjects();
        if (!cancelled) {
          setProjects(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          const message = (err as Error).message;
          if (/^(401|403):/.test(message)) setLogin(true);
          else setError(message);
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
  }, [login, attempt]);
  if (login) return <Navigate to="/entrar?next=%2Fmeus-pedidos" replace />;
  function status(p: Project) {
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
    <div className="studio-app kid">
      <SiteBackNav />
      <main className="studio-card purchase-orders">
        <h1>{t.myOrders}</h1>
        <a className="kbtn" href="/app">
          {t.create}
        </a>
        {error && (
          <p role="alert">
            {error}
            <button type="button" onClick={() => setAttempt((n) => n + 1)}>
              {t.retry}
            </button>
          </p>
        )}
        {!projects && !error && <p role="status">{t.loading}</p>}
        {projects?.length === 0 && <p>{t.empty}</p>}
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
              <p role="status">{status(p)}</p>
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
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
