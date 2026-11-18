import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { accountAccess, accountGateHref } from "./Auth";
import { api, getToken } from "./api";
import type { Project } from "./types";
import { SiteBackNav } from "./SiteBackNav";
import { useResolvedLang, type Lang } from "./i18n/lang";
import { purchaseCopy } from "./studio/purchaseCopy";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import "./landing.css";
import "./studio.css";
import logo from "./assets/logo.png";
import { StudioStageHeading } from "./studio/StudioStageHeading";

type Tone = "action" | "money" | "wait" | "done";

const COPY = {
  pt: {
    intro: "Acompanhe seus livros e continue de onde parou.",
    newBook: "Criar novo livro",
    inProgress: "Em andamento",
    finished: "Concluídos",
    privacy: "Seus dados e como pedir a exclusão",
    more: "Mais opções",
    redo: "Sua vez: refazer a prévia",
    approvedBook: "Aprovado para impressão",
    reviewBook: "Sua vez: revisar o livro completo",
    generating: "Criando o livro completo…",
    paying: "Confirmando o pagamento…",
    approvePreview: "Sua vez: aprovar a prévia e fazer o pedido",
    approveStory: "Sua vez: aprovar a história",
    seePreview: "Sua vez: ver a prévia",
    approveCover: "Sua vez: aprovar a capa",
    creating: "Criando as imagens…",
    draft: "Criação não concluída",
    open: "Ver pedido",
    follow: "Acompanhar",
    resume: "Continuar",
    readStory: "Ler a história",
    seePreviewCta: "Ver a prévia",
    reviewBookCta: "Revisar o livro",
    seeBook: "Ver livro",
    revoke: "Retirar autorização de novos usos",
    revoked: "Novas gerações bloqueadas",
    revokeConfirm:
      "Retirar a autorização? As fotos deste livro não serão usadas em novas gerações. O pedido continua disponível para consulta.",
  },
  en: {
    intro: "Follow your books and pick up where you left off.",
    newBook: "Create a new book",
    inProgress: "In progress",
    finished: "Finished",
    privacy: "Your information and deletion rights",
    more: "More options",
    redo: "Your turn: redo the preview",
    approvedBook: "Approved for printing",
    reviewBook: "Your turn: review the complete book",
    generating: "Creating the complete book…",
    paying: "Confirming payment…",
    approvePreview: "Your turn: approve the preview and order",
    approveStory: "Your turn: approve the story",
    seePreview: "Your turn: see the preview",
    approveCover: "Your turn: approve the cover",
    creating: "Creating the images…",
    draft: "Creation not finished",
    open: "View order",
    follow: "Follow",
    resume: "Continue",
    readStory: "Read the story",
    seePreviewCta: "See the preview",
    reviewBookCta: "Review the book",
    seeBook: "See the book",
    revoke: "Withdraw authorization for further use",
    revoked: "Further generation blocked",
    revokeConfirm:
      "Withdraw authorization? This book's photos won't be used for new generations. The order stays available to view.",
  },
  es: {
    intro: "Sigue tus libros y continúa donde lo dejaste.",
    newBook: "Crear un libro nuevo",
    inProgress: "En curso",
    finished: "Terminados",
    privacy: "Tus datos y cómo solicitar su eliminación",
    more: "Más opciones",
    redo: "Tu turno: rehacer la vista previa",
    approvedBook: "Aprobado para impresión",
    reviewBook: "Tu turno: revisar el libro completo",
    generating: "Creando el libro completo…",
    paying: "Confirmando el pago…",
    approvePreview: "Tu turno: aprobar la vista previa y hacer el pedido",
    approveStory: "Tu turno: aprobar la historia",
    seePreview: "Tu turno: ver la vista previa",
    approveCover: "Tu turno: aprobar la portada",
    creating: "Creando las imágenes…",
    draft: "Creación sin terminar",
    open: "Ver pedido",
    follow: "Seguir",
    resume: "Continuar",
    readStory: "Leer la historia",
    seePreviewCta: "Ver la vista previa",
    reviewBookCta: "Revisar el libro",
    seeBook: "Ver el libro",
    revoke: "Retirar autorización para nuevos usos",
    revoked: "Nuevas generaciones bloqueadas",
    revokeConfirm:
      "¿Retirar la autorización? Las fotos de este libro no se usarán en nuevas generaciones. El pedido sigue disponible para consultar.",
  },
} satisfies Record<Lang, Record<string, string>>;

type Copy = (typeof COPY)["pt"];

type OrderState = { label: string; tone: Tone; cta: string; done: boolean };

/** What the family sees on the card: where the book is and what to do next. */
function orderState(p: Project, c: Copy, quotation: string): OrderState {
  const flow = p.purchase_flow;
  const stage = p.book_profile?.stage;
  const state = (label: string, tone: Tone, cta: string, done = false): OrderState => ({ label, tone, cta, done });
  if (p.book_profile?.credits_fallback) return state(c.redo, "action", c.resume);
  if (p.book_approved_at && flow?.full_book_ready_at) return state(c.approvedBook, "done", c.seeBook, true);
  if (flow?.full_book_ready_at) return state(c.reviewBook, "action", c.reviewBookCta);
  if (flow?.stage === "generating_book") return state(c.generating, "wait", c.follow);
  if (flow?.stage === "awaiting_payment_confirmation") return state(c.paying, "wait", c.follow);
  if (flow?.preview_approved_at) return state(quotation, "money", c.open);
  if (stage === "story_approved") return state(c.approvePreview, "action", c.resume);
  if (stage === "story_ready") return state(c.approveStory, "action", c.readStory);
  if (stage === "cover_ready") return state(c.approveCover, "action", c.seePreviewCta);
  if (stage === "preview_ready" || (!p.book_profile && (flow?.preview_ready_at || p.ebook_url)))
    return state(c.seePreview, "action", c.seePreviewCta);
  if (flow?.stage === "preview_generating") return state(c.creating, "wait", c.follow);
  return state(c.draft, "wait", c.resume);
}

function bookTitle(p: Project, fallback: string) {
  return (
    p.purchase_flow?.title ||
    p.book_profile?.title ||
    p.book_profile?.locales?.[p.language || "pt-BR"]?.title ||
    Object.values(p.book_profile?.locales ?? {})[0]?.title ||
    p.story_text?.match(/^T[íi]tulo:\s*([^\n]+)/i)?.[1] ||
    p.child_name ||
    fallback
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z" />
      <path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5" />
      <path d="M9 8h7" />
    </svg>
  );
}

export function MyOrders() {
  usePageMeta(staticPageMeta("/meus-pedidos"));
  const [lang] = useResolvedLang();
  const t = purchaseCopy(lang);
  const c = COPY[lang] ?? COPY.pt;
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
  async function revokeProject(id: string) {
    if (!window.confirm(c.revokeConfirm)) return;
    setRevoking(id);
    setError(null);
    try {
      const updated = await api.revokeBookMedia(id);
      setProjects((prev) => prev?.map((item) => (item.id === id ? updated : item)) ?? null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setRevoking(null);
    }
  }
  const locale = lang === "pt" ? "pt-BR" : lang;
  const cards = (projects ?? []).map((p) => ({ p, state: orderState(p, c, t.quotation) }));
  // The family's turn comes first; otherwise the newest book first (API order).
  const active = cards
    .filter((card) => !card.state.done)
    .sort((a, b) => Number(b.state.tone === "action") - Number(a.state.tone === "action"));
  const finished = cards.filter((card) => card.state.done);
  function renderCard({ p, state }: (typeof cards)[number]) {
    const title = bookTitle(p, t.steps[0]);
    const child = p.child_name && p.child_name !== title ? p.child_name : null;
    const busy = removing === p.id || revoking === p.id;
    return (
      <article key={p.id} className={`order-card is-${state.tone}`} data-testid="order-card">
        <div className="order-card-cover">
          {p.cover_thumb_url ? <img src={p.cover_thumb_url} alt="" loading="lazy" /> : <BookIcon />}
        </div>
        <div className="order-card-body">
          <h3>{title}</h3>
          <p className="order-card-meta">
            {[
              child,
              p.book_size === "P" ? "15 × 15 cm" : "20 × 20 cm",
              p.cover_type === "hard" ? t.hard : t.soft,
              new Date(p.created_at).toLocaleDateString(locale),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <p className="purchase-order-status order-card-status" role="status">{state.label}</p>
          {p.processing_revoked_at && <p className="order-card-note">{c.revoked}</p>}
        </div>
        <div className="order-card-actions">
          <a className="kbtn kbtn-primary" href={`/app?projeto=${encodeURIComponent(p.id)}`}>
            {state.cta} →
          </a>
          <details className="order-more">
            <summary aria-label={c.more} title={c.more}>
              <span aria-hidden="true">⋯</span>
            </summary>
            <div className="order-more-menu">
              <button
                type="button"
                data-testid="order-revoke"
                disabled={busy || !!p.processing_revoked_at}
                onClick={() => void revokeProject(p.id)}
              >
                {p.processing_revoked_at ? c.revoked : c.revoke}
              </button>
              <button
                type="button"
                className="purchase-order-delete"
                data-testid="order-delete"
                disabled={busy}
                onClick={() => void removeProject(p.id)}
              >
                {removing === p.id ? t.deleteBusy : t.deleteProject}
              </button>
            </div>
          </details>
        </div>
      </article>
    );
  }
  return (
    <div className="studio-app kid studio-orders-page">
      <header className="khead"><div className="khead-inner">
        <a href="/" className="kbrand" aria-label="Story R Us"><img className="hdr-logo" src={logo} alt="Story R Us" /></a>
      </div></header>
      <div className="ksection site-back-wrap"><SiteBackNav /></div>
      <main className="studio-page"><section className="studio-card purchase-orders">
        <StudioStageHeading title={t.myOrders} level="h1" illustration={3}>
          <p>{c.intro}</p>
        </StudioStageHeading>
        <div className="orders-toolbar">
          <a className="kbtn kbtn-primary" href="/app">{c.newBook}</a>
        </div>
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
        {active.length > 0 && (
          <section className="orders-group" aria-labelledby="orders-active">
            <h2 id="orders-active">{c.inProgress} <span>· {active.length}</span></h2>
            <div className="purchase-order-list order-list">{active.map(renderCard)}</div>
          </section>
        )}
        {finished.length > 0 && (
          <section className="orders-group" aria-labelledby="orders-finished">
            <h2 id="orders-finished">{c.finished} <span>· {finished.length}</span></h2>
            <div className="purchase-order-list order-list">{finished.map(renderCard)}</div>
          </section>
        )}
        <p className="orders-privacy">
          <a href={lang === "en" ? "/privacy" : "/privacidade"}>{c.privacy}</a>
        </p>
      </section></main>
    </div>
  );
}
