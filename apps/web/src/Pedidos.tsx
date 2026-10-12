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
      awaiting_spec: "Aguardando especificação",
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
  const [stats, setStats] = useState<{
    users: number;
    projects: number;
    awaitingPhoto: number;
  } | null>(null);

  const load = useCallback(async (secret: string) => {
    setLoading(true);
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

  useEffect(() => {
    if (password) {
      void load(password);
      return;
    }
    if (!sessionTried && canTryOwnerSession()) {
      setSessionTried(true);
      void load(OWNER_SESSION_TOKEN);
    }
  }, [password, load, sessionTried]);

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
  const unlocked = orders !== null;
  const transient = Boolean(error && isOwnerTransientFailure(lastStatus, error));
  const opening =
    !unlocked &&
    (loading ||
      Boolean(password) ||
      (!sessionTried && canTryOwnerSession()) ||
      (transient && canTryOwnerSession()));

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
                  onClick={() => setSelected(order.id)}
                >
                  <strong>{titleOf(order.summary)}</strong>
                  <span>{when(order.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
          {current && (
            <article className="usage-order-detail" data-testid="order-detail">
              <h2>{titleOf(current.summary)}</h2>
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
                <ol>
                  <li>Pedido aberto com os dados da família e a foto.</li>
                  <li>
                    {current.has_story || (current.book_files ?? []).length > 0
                      ? "Livro guardado neste pedido."
                      : "Livro ainda sendo gerado. Personagem, história e imagens entram aqui."}
                  </li>
                  <li>
                    Faturar
                    {current.payment_status === "paid"
                      ? " — faturado."
                      : current.payment_status === "pending"
                        ? " — fatura em aberto."
                        : " — ainda a faturar."}
                  </li>
                  <li>
                    Gráfica
                    {current.print_status === "files_ready" || current.print_status === "approved"
                      ? " — pacote pronto para envio."
                      : current.print_status === "sent_for_validation"
                        ? " — pacote em validação."
                        : current.block_reason
                          ? ` — ${current.block_reason}`
                          : " — aguardando o livro para montar o pacote."}
                  </li>
                </ol>
                {(current.book_files ?? []).length > 0 && (
                  <ul className="order-os-files" data-testid="order-book-files">
                    {(current.book_files ?? []).map((file) => (
                      <li key={`${file.label}-${file.url}`}>
                        <a href={file.url} target="_blank" rel="noreferrer">
                          {file.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <p className="muted">
                {when(current.created_at)} · Projeto {current.project_id}
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
            </article>
          )}
        </div>
      )}
    </div>
  );
}
