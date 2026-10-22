import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import logo from "./assets/logo.png";
import { api, getToken } from "./api";
import { OwnerAccessGate } from "./OwnerAccessGate";
import { OwnerNav } from "./OwnerNav";
import {
  OWNER_SESSION_TOKEN,
  apiOwnerPassword,
  canTryOwnerSession,
  clearOwnerSecret,
  isOwnerAuthFailure,
  isOwnerTransientFailure,
  ownerGateError,
  persistOwnerSecret,
  readOwnerSecret,
} from "./ownerSession";
import { useOwnerPageTitle } from "./useOwnerPageTitle";
import type { OrderTicket } from "./types";
import "./usage.css";

function when(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function titleOf(summary: string): string {
  return summary.split("\n")[0]?.trim() || "Pedido";
}

function nameOf(order: OrderTicket): string {
  const name = order.summary.split("\n").find((line) => /^Nome:/i.test(line));
  return name ? `Livro de ${name.slice(name.indexOf(":") + 1).trim()}` : titleOf(order.summary);
}

function generationLabel(order: OrderTicket): string {
  const stages: Record<string, string> = { AVATAR: "Criando personagem", STORY: "Preparando história", EBOOK: "Gerando imagens" };
  const labels: Record<string, string> = {
    queued: "Na fila de geração", generating: order.generation_stage === "EBOOK" ? `Gerando imagens · ${order.generated_images ?? 0}/3` : stages[order.generation_stage ?? ""] ?? "Gerando prévia",
    ready: "Prévia pronta", partial: "Prévia incompleta", failed: "Geração interrompida", demo: "Imagens de demonstração",
  };
  return labels[order.generation_status ?? ""] ?? ((order.book_files ?? []).length ? "Prévia disponível" : "Aguardando geração");
}

function printDescription(order: OrderTicket): string {
  const labels: Record<string, string> = {
    awaiting_spec: "Configuração da gráfica pendente", awaiting_pages: "Aguardando páginas para impressão",
    awaiting_payment: "Pedido em cotação", generating_book: "Gerando livro completo", awaiting_customer_approval: "Aguardando revisão da família",
    held: "Formato aguardando liberação", files_ready: "Arquivos prontos", sent_for_validation: "Pacote em validação",
    approved: "Produção aprovada", rejected: "Ajustes solicitados pela gráfica",
  };
  return labels[order.print_status ?? ""] ?? "Aguardando preparação do impresso";
}

function printRequirements(reason: string): string {
  const labels: Record<string, string> = {
    bleed_mm: "sangria", safety_mm: "margem de segurança", spine_mm: "largura da lombada",
    score_mm: "medida do vinco", pdf_x: "padrão PDF/X", color_profile: "perfil de cor", filename_pattern: "padrão dos nomes dos arquivos",
  };
  return reason.replace(/Especificação de produção incompleta:\s*/i, "A gráfica precisa informar: ")
    .replace(/\b(bleed_mm|safety_mm|spine_mm|score_mm|pdf_x|color_profile|filename_pattern)\b/g, (key) => labels[key]);
}

function generationFailure(error?: string | null): string {
  const text = error ?? "";
  if (/credit_balance_exhausted|insufficient_quota|no credits remaining/i.test(text)) {
    return "A conta da OpenAI está sem créditos. Recarregue o saldo e clique em gerar de novo. Os dados e as fotos continuam salvos.";
  }
  if (/Ficha visual/i.test(text)) {
    return "A ficha visual veio incompleta. Clique em gerar de novo para completar e seguir com as imagens.";
  }
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean && clean.length <= 220) return clean;
  return "A geração foi interrompida. Seus dados e fotos continuam salvos para uma nova tentativa.";
}

function OrderPreview({ order }: { order: OrderTicket }) {
  const files = order.book_files ?? [];
  const slots = [
    { kind: "character", label: "Personagem" }, { kind: "cover", label: "Capa" },
    { kind: "page_image", label: "Página 1" }, { kind: "in_hand", label: "Livro na mão" },
  ];
  const pdf = files.find((file) => file.kind === "ebook" || file.label === "PDF do livro");
  return (
    <section className="order-preview" aria-label="Prévia do livro">
      <div className="order-preview-heading">
        <h3>Prévia do livro</h3>
        <span className={`order-status is-${order.generation_status ?? "queued"}`} role="status">{generationLabel(order)}</span>
      </div>
      <p className="muted">Capa, uma página da história e o livro na mão.</p>
      <div className="order-preview-grid" data-testid="order-book-files">
        {slots.map((slot) => {
          const file = files.find((item) => item.kind === slot.kind || item.label === slot.label || (slot.kind === "page_image" && /^Página/.test(item.label)));
          return (
            <figure className="order-preview-card" key={slot.kind}>
              {file ? (
                <a href={file.url} target="_blank" rel="noreferrer" aria-label={`Abrir ${slot.label.toLowerCase()}`}>
                  <img src={file.url} alt={slot.label} loading="lazy" />
                </a>
              ) : <div className="order-preview-placeholder">{order.generation_status === "failed" ? "Imagem pendente" : "Aguardando imagem"}</div>}
              <figcaption>{slot.label}</figcaption>
            </figure>
          );
        })}
      </div>
      {order.generation_status === "partial" && <p className="order-notice">Alguns arquivos da prévia ainda não foram concluídos. As imagens disponíveis ficam salvas no pedido.</p>}
      {order.generation_status === "demo" && <p className="order-notice">Estas imagens foram criadas no modo de demonstração. A equipe pode gerar a prévia com OpenAI neste pedido.</p>}
      {order.generation_status === "failed" && <p className="order-notice">{generationFailure(order.generation_error)}</p>}
      {pdf && <a className="order-file-button" href={pdf.url} target="_blank" rel="noreferrer">PDF do livro <span>· prévia</span></a>}
    </section>
  );
}

function fieldsOf(order: OrderTicket): { label: string; value: string }[] {
  const rows = order.summary
    .split("\n")
    .slice(1)
    .map((line) => {
      const cut = line.indexOf(":");
      if (cut === -1) return { label: line, value: "" };
      return { label: line.slice(0, cut).trim(), value: line.slice(cut + 1).trim() };
    })
    .filter((row) => row.label);
  if (order.child_age != null) rows.push({ label: "Idade", value: String(order.child_age) });
  if (order.book_size === "M" || order.book_size === "P") {
    rows.push({
      label: "Tamanho",
      value: order.book_size === "P" ? "P — 15 × 15 cm" : "M — 20 × 20 cm",
    });
  }
  if (order.cover_type === "soft" || order.cover_type === "hard") {
    rows.push({
      label: "Capa",
      value: order.cover_type === "soft" ? "Capa flexível" : "Capa dura",
    });
  }
  if (order.style) {
    rows.push({
      label: "Estilo",
      value: order.style === "cartoon" ? "Cartoon" : "Realista",
    });
  }
  if (order.print_code) rows.push({ label: "OS", value: order.print_code });
  if (order.print_status) {
    const labels: Record<string, string> = {
      awaiting_spec: "Configuração da gráfica pendente",
      awaiting_payment: "Pedido em cotação", generating_book: "Gerando livro completo", awaiting_customer_approval: "Aguardando revisão da família",
      awaiting_pages: "Aguardando páginas",
      held: "Formato ainda não liberado",
      files_ready: "Arquivos prontos",
      sent_for_validation: "Enviado para validação",
      approved: "Aprovado",
      rejected: "Recusado",
    };
    rows.push({ label: "Produção", value: labels[order.print_status] ?? order.print_status });
  }
  if (order.payment_status) {
    const payment: Record<string, string> = {
      unpaid: "A faturar",
      pending: "Fatura em aberto",
      paid: "Faturado",
    };
    rows.push({ label: "Faturamento", value: payment[order.payment_status] ?? order.payment_status });
  }
  if (order.amount_cents != null) {
    rows.push({
      label: "Valor",
      value: (order.amount_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
    });
  }
  if (order.tracking_code) rows.push({ label: "Rastreio", value: order.tracking_code });
  return rows;
}

/** Visão de leitura do cliente: só os pedidos da própria conta, com status e arquivos. */
function PersonalOrders({
  orders,
  loading,
  error,
}: {
  orders: OrderTicket[] | null;
  loading: boolean;
  error: string | null;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const current = orders?.find((order) => order.id === selected) ?? orders?.[0] ?? null;

  return (
    <div className="usage">
      <header className="usage-head">
        <img className="hdr-logo" src={logo} alt="Story R Us" />
        <div>
          <h1>Meus Pedidos</h1>
          <p className="muted">
            Aqui ficam os livros que você criou, com o status de produção e os arquivos.
          </p>
        </div>
        <a className="link" href="/app">
          Voltar ao estúdio
        </a>
      </header>

      {error && <p className="error">{error}</p>}

      {loading && orders === null ? (
        <p className="muted" data-testid="pedidos-loading">
          Carregando seus pedidos…
        </p>
      ) : (orders ?? []).length === 0 ? (
        <p className="muted" data-testid="pedidos-empty">
          Você ainda não tem pedidos. Crie um livro no estúdio e ele aparece aqui.
        </p>
      ) : (
        <div className="usage-orders">
          <ul className="usage-order-list" aria-label="Lista de pedidos">
            {(orders ?? []).map((order) => (
              <li key={order.id}>
                <button
                  type="button"
                  className={order.id === current?.id ? "is-on" : ""}
                  aria-pressed={order.id === current?.id}
                  onClick={() => setSelected(order.id)}
                >
                  <strong>{nameOf(order)}</strong>
                  <span>{generationLabel(order)}</span>
                  <span>{when(order.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
          {current && (
            <article className="usage-order-detail" data-testid="order-detail">
              <h2>{nameOf(current)}</h2>
              <OrderPreview order={current} />
              <dl>
                {fieldsOf(current).map((row) => (
                  <div key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.value || "—"}</dd>
                  </div>
                ))}
              </dl>
              {(current.photo_urls ?? []).length > 0 && (
                <div className="usage-order-photos">
                  {(current.photo_urls ?? []).map((url) => (
                    <figure key={url}>
                      <img src={url} alt="Foto enviada no pedido" />
                      <a href={url} target="_blank" rel="noreferrer">
                        Abrir imagem
                      </a>
                    </figure>
                  ))}
                </div>
              )}
              <a className="btn" href={`/app?projeto=${encodeURIComponent(current.project_id)}`}>Continuar pedido</a>
              <p className="muted">{when(current.created_at)}</p>
            </article>
          )}
        </div>
      )}
    </div>
  );
}

export function Pedidos() {
  useOwnerPageTitle("/pedidos");
  const [password, setPassword] = useState(() => readOwnerSecret());
  const [draft, setDraft] = useState("");
  const [orders, setOrders] = useState<OrderTicket[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessionTried, setSessionTried] = useState(false);
  const [lastStatus, setLastStatus] = useState<number | undefined>();
  const autoRetryUsed = useRef(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [stats, setStats] = useState<{
    users: number;
    projects: number;
    awaitingPhoto: number;
  } | null>(null);
  // Papel da conta: admin vê o painel geral; os demais veem só os próprios pedidos.
  const [role, setRole] = useState<"unknown" | "admin" | "member">("unknown");
  const [personal, setPersonal] = useState<OrderTicket[] | null>(null);
  const [personalError, setPersonalError] = useState<string | null>(null);
  const [personalLoading, setPersonalLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const hasOrders = orders !== null;
  const hasActiveGeneration = (orders ?? []).some((order) => order.generation_status === "generating" || (order.generation_status === "queued" && Boolean(order.generation_stage)));

  const load = useCallback(async (secret: string, quiet = false) => {
    if (!quiet) setLoading(true);
    setError(null);
    setLastStatus(undefined);
    try {
      const report = await api.usage(apiOwnerPassword(secret), undefined, undefined, "orders");
      const list = report.orders ?? [];
      setOrders(list);
      setStats({
        users: report.users_total ?? 0,
        projects: report.projects_total ?? 0,
        awaitingPhoto: report.projects_awaiting_photo ?? 0,
      });
      setSelected((cur) => (cur && list.some((order) => order.id === cur) ? cur : list[0]?.id ?? null));
      if (!quiet) setConfirmDelete(false);
      const next = apiOwnerPassword(secret) ? secret.trim() : OWNER_SESSION_TOKEN;
      persistOwnerSecret(next);
      setPassword(next);
      autoRetryUsed.current = false;
    } catch (err) {
      const status = (err as Error & { status?: number }).status;
      const raw = err instanceof Error ? err.message : "Falha ao carregar pedidos.";
      setLastStatus(status);
      if (isOwnerAuthFailure(status)) {
        clearOwnerSecret();
        setPassword("");
        setOrders(null);
      }
      setError(
        ownerGateError(status, raw, {
          usedSession: !apiOwnerPassword(secret) && Boolean(getToken()),
        }),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Descobre o papel da conta: admin mantém o painel geral; os demais veem só os
  // próprios pedidos. Sem sessão, cai no portão com a senha do painel (dono).
  useEffect(() => {
    if (!getToken()) {
      setRole("admin");
      return;
    }
    let alive = true;
    api
      .me()
      .then((me) => {
        if (alive) setRole(me.is_admin || me.is_owner ? "admin" : "member");
      })
      .catch(() => {
        if (alive) setRole("member");
      });
    return () => {
      alive = false;
    };
  }, []);

  // Pedidos da própria conta (cliente): leitura, sem senha e sem controles de admin.
  useEffect(() => {
    if (role !== "member") return;
    let alive = true;
    let inFlight = false;
    let watching = true;
    setPersonalLoading(true);
    setPersonalError(null);
    const refresh = () => {
      if (inFlight || document.visibilityState === "hidden") return;
      inFlight = true;
      void api.myOrders()
      .then((list) => {
        if (alive) {
          setPersonal(list);
          watching = list.some((order) => order.generation_status === "generating" || (order.generation_status === "queued" && Boolean(order.generation_stage)));
        }
      })
      .catch((err: Error) => {
        if (!alive) return;
        setPersonal((current) => current ?? []);
        setPersonalError(err.message || "Falha ao carregar seus pedidos.");
      })
      .finally(() => {
        inFlight = false;
        if (alive) setPersonalLoading(false);
      });
    };
    refresh();
    const timer = window.setInterval(() => { if (watching) refresh(); }, 15000);
    window.addEventListener("focus", refresh);
    return () => {
      alive = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [role]);

  useEffect(() => {
    if (role !== "admin") return;
    if (password) {
      void load(password);
      return;
    }
    if (!sessionTried && canTryOwnerSession()) {
      setSessionTried(true);
      void load(OWNER_SESSION_TOKEN);
    }
  }, [role, password, load, sessionTried]);

  useEffect(() => {
    if (role !== "admin" || !password || !hasOrders) return;
    const refresh = () => {
      if (document.visibilityState !== "hidden") void load(password, true);
    };
    const timer = hasActiveGeneration ? window.setInterval(refresh, 15000) : undefined;
    window.addEventListener("focus", refresh);
    return () => { if (timer !== undefined) window.clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [role, password, hasOrders, hasActiveGeneration, load]);

  // Cold start: uma nova tentativa automática após falha transitória.
  useEffect(() => {
    if (orders !== null || loading || !error || autoRetryUsed.current) return;
    if (!isOwnerTransientFailure(lastStatus, error)) return;
    if (!canTryOwnerSession() && !password) return;
    autoRetryUsed.current = true;
    const id = window.setTimeout(() => {
      void load(password || OWNER_SESSION_TOKEN);
    }, 3500);
    return () => window.clearTimeout(id);
  }, [orders, loading, error, lastStatus, password, load]);

  function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    const next = draft.trim();
    if (next) void load(next);
  }

  const current = orders?.find((order) => order.id === selected) ?? null;
  const ownerSecret = apiOwnerPassword(password);

  async function generateImages() {
    if (!current || generating) return;
    setGenerating(true);
    setError(null);
    try {
      await api.generateOrderImages(ownerSecret, current.id);
      await load(password, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível iniciar a geração.");
    } finally {
      setGenerating(false);
    }
  }

  async function removeOrder() {
    if (!current) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteOrder(ownerSecret, current.id);
      const next = (orders ?? []).filter((order) => order.id !== current.id);
      setOrders(next);
      setSelected(next[0]?.id ?? null);
      setConfirmDelete(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir o pedido.");
    } finally {
      setDeleting(false);
    }
  }

  const unlocked = orders !== null;
  const transient = Boolean(error && isOwnerTransientFailure(lastStatus, error));
  const opening =
    !unlocked &&
    (loading ||
      Boolean(password) ||
      (!sessionTried && canTryOwnerSession()) ||
      (transient && canTryOwnerSession()));

  if (role === "unknown") {
    return (
      <OwnerAccessGate
        title="Pedidos"
        loginNext="/pedidos"
        draft={draft}
        onDraftChange={setDraft}
        onSubmitPassword={onSubmit}
        onRetrySession={() => void load(password || OWNER_SESSION_TOKEN)}
        loading={canTryOwnerSession()}
        error={null}
        opening={canTryOwnerSession()}
        transient={false}
      />
    );
  }

  if (role === "member") {
    return <PersonalOrders orders={personal} loading={personalLoading} error={personalError} />;
  }

  if (!unlocked) {
    return (
      <OwnerAccessGate
        title="Pedidos"
        loginNext="/pedidos"
        draft={draft}
        onDraftChange={setDraft}
        onSubmitPassword={onSubmit}
        onRetrySession={() => void load(password || OWNER_SESSION_TOKEN)}
        loading={loading || (!sessionTried && canTryOwnerSession() && !error)}
        error={error}
        opening={opening && !isOwnerAuthFailure(lastStatus)}
        transient={transient}
      />
    );
  }

  return (
    <div className="usage">
      <header className="usage-head">
        <img className="hdr-logo" src={logo} alt="Story R Us" />
        <div>
          <h1>Pedidos</h1>
          <p className="muted">
            Cada pedido abre uma OS para faturar e mandar para a gráfica. O livro gerado fica
            guardado nesse pedido.
          </p>
        </div>
        <OwnerNav current="pedidos" />
        <button className="link" type="button" disabled={loading} onClick={() => void load(password)}>
          {loading ? "Atualizando…" : "Atualizar pedidos"}
        </button>
        <button
          className="link"
          type="button"
          onClick={() => {
            clearOwnerSecret();
            setPassword("");
            setOrders(null);
            setDraft("");
            setSessionTried(true);
          }}
        >
          Sair
        </button>
      </header>

      {error && <p className="error">{error}</p>}

      {(orders ?? []).length === 0 ? (
        <div className="muted" data-testid="pedidos-empty">
          <p>
            Nenhum pedido com foto ainda. O pedido entra aqui quando a família cria o livro no
            estúdio e envia a foto — cadastro em Usuários sozinho não gera pedido.
          </p>
          {stats && (stats.users > 0 || stats.projects > 0) && (
            <p data-testid="pedidos-empty-stats">
              Agora: {stats.users} conta(s), {stats.projects} projeto(s)
              {stats.awaitingPhoto > 0
                ? `, ${stats.awaitingPhoto} projeto(s) ainda sem foto/pedido.`
                : "."}
            </p>
          )}
        </div>
      ) : (
        <div className="usage-orders">
          <ul className="usage-order-list" aria-label="Lista de pedidos">
            {(orders ?? []).map((order) => (
              <li key={order.id}>
                <button
                  type="button"
                  className={order.id === selected ? "is-on" : ""}
                  aria-pressed={order.id === selected}
                  onClick={() => {
                    setSelected(order.id);
                    setConfirmDelete(false);
                  }}
                >
                  <strong>{nameOf(order)}</strong>
                  <span>{generationLabel(order)}</span>
                  <span>{when(order.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
          {current && (
            <article className="usage-order-detail" data-testid="order-detail">
              <h2>{nameOf(current)}</h2>
              <OrderPreview order={current} />
              {current.payment_status !== "paid" && (
                <button
                  type="button" className="order-generate-button" data-testid="order-generate"
                  disabled={generating || current.generation_status === "generating" || (current.generation_status === "queued" && Boolean(current.generation_stage))}
                  onClick={() => void generateImages()}
                >
                  {generating ? "Iniciando geração…" : current.generation_status === "generating" || (current.generation_status === "queued" && current.generation_stage)
                    ? "Geração em andamento" : current.image_provider === "openai" ? "Gerar novamente com OpenAI" : "Gerar imagens com OpenAI"}
                </button>
              )}
              <dl>
                {fieldsOf(current).map((row) => (
                  <div key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.value || "—"}</dd>
                  </div>
                ))}
              </dl>
              {(current.photo_urls ?? []).length > 0 && (
                <div className="usage-order-photos">
                  {(current.photo_urls ?? []).map((url) => (
                    <figure key={url}>
                      <img src={url} alt="Foto enviada no pedido" />
                      <a href={url} target="_blank" rel="noreferrer">
                        Abrir imagem
                      </a>
                    </figure>
                  ))}
                </div>
              )}
              <section className="order-os" data-testid="order-os">
                <h3>Ordem de serviço {current.print_code || "—"}</h3>
                <div className="order-workflow">
                  <div><span>Prévia</span><strong>{generationLabel(current)}</strong><p>As imagens e o PDF ficam salvos neste pedido.</p></div>
                  <div><span>Faturamento</span><strong>{current.payment_status === "paid" ? "Faturado" : current.payment_status === "pending" ? "Fatura em aberto" : "A faturar"}</strong><p>{current.payment_status === "paid" ? "Pagamento confirmado." : "Faturamento do livro impresso."}</p></div>
                  <div><span>Impressão</span><strong>{printDescription(current)}</strong><p>{current.print_status === "awaiting_spec" ? "O pacote de impressão depende das medidas e do padrão da gráfica." : "Acompanhe a preparação e a validação dos arquivos."}</p></div>
                </div>
                {current.block_reason && <details className="order-print-details"><summary>O que falta para impressão?</summary><p>{printRequirements(current.block_reason)}</p></details>}
              </section>
              <p className="muted">
                Pedido recebido em {when(current.created_at)}
              </p>
              {current.print_order_id && current.print_status === "files_ready" && (
                <button
                  type="button"
                  onClick={() =>
                    void api
                      .setPrintValidation(ownerSecret, current.print_order_id as string, "sent_for_validation")
                      .then(() => load(password))
                      .catch((err: Error) => setError(err.message))
                  }
                >
                  Enviar para validação
                </button>
              )}
              {current.print_order_id && current.print_status === "sent_for_validation" && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    onClick={() =>
                      void api
                        .setPrintValidation(ownerSecret, current.print_order_id as string, "approved")
                        .then(() => load(password))
                        .catch((err: Error) => setError(err.message))
                    }
                  >
                    Aprovar produção
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void api
                        .setPrintValidation(ownerSecret, current.print_order_id as string, "rejected")
                        .then(() => load(password))
                        .catch((err: Error) => setError(err.message))
                    }
                  >
                    Recusar produção
                  </button>
                </div>
              )}
              {current.print_order_id &&
                ["files_ready", "sent_for_validation", "approved", "rejected"].includes(
                  current.print_status ?? "",
                ) && (
                  <button
                    type="button"
                    onClick={() =>
                      void api.downloadPrintPackage(ownerSecret, current.print_order_id as string).then((blob) => {
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = `${current.print_code ?? "impresso"}.zip`;
                        link.click();
                        URL.revokeObjectURL(url);
                      })
                    }
                  >
                    Baixar pacote
                  </button>
                )}
              <div className="usage-user-danger" data-testid="order-danger">
                {confirmDelete ? (
                  <>
                    <p className="error">
                      Apaga o livro de {titleOf(current.summary)} por completo: fotos, história,
                      páginas, arquivos e a OS. A conta da família permanece. Isso não volta atrás.
                    </p>
                    <button
                      type="button"
                      className="usage-btn-danger"
                      disabled={deleting}
                      onClick={() => void removeOrder()}
                      data-testid="order-delete-confirm"
                    >
                      {deleting ? "Excluindo…" : "Confirmar exclusão"}
                    </button>
                    <button
                      type="button"
                      className="link"
                      disabled={deleting}
                      onClick={() => setConfirmDelete(false)}
                    >
                      Cancelar
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="usage-btn-danger"
                    onClick={() => setConfirmDelete(true)}
                    data-testid="order-delete"
                  >
                    Excluir pedido
                  </button>
                )}
              </div>
            </article>
          )}
        </div>
      )}
    </div>
  );
}
