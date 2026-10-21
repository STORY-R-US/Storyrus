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
import type { UsageEvent, UsageReport } from "./types";
import "./usage.css";

const STEP_LABEL: Record<string, string> = {
  AVATAR: "Personagem",
  REALISTIC: "Retrato",
  STORY: "História",
  EBOOK: "E-book",
  STORYBOARD: "Roteiro",
  VIDEO: "Vídeo",
  EXTRA_CHARACTER: "Personagem extra",
  NARRATED_VIDEO: "Vídeo narrado",
};

const PROVIDER_LABEL: Record<string, string> = {
  openai: "OpenAI",
  claude: "Claude",
  kling: "Kling",
  elevenlabs: "ElevenLabs",
  // Legado (extrato antigo)
  gemini: "Gemini",
  fal: "Fal",
  "nano-banana": "Gemini",
};

function money(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

function when(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function Usage() {
  useOwnerPageTitle("/gastos");
  const [password, setPassword] = useState(() => readOwnerSecret());
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<UsageReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessionTried, setSessionTried] = useState(false);
  const [lastStatus, setLastStatus] = useState<number | undefined>();
  const autoRetryUsed = useRef(false);

  const load = useCallback(async (secret: string) => {
    setLoading(true);
    setError(null);
    setLastStatus(undefined);
    try {
      const report = await api.usage(apiOwnerPassword(secret), "2026-09-01", "2026-09-30");
      setData(report);
      const next = apiOwnerPassword(secret) ? secret.trim() : OWNER_SESSION_TOKEN;
      persistOwnerSecret(next);
      setPassword(next);
      autoRetryUsed.current = false;
    } catch (err) {
      const status = (err as Error & { status?: number }).status;
      const raw = err instanceof Error ? err.message : "Falha ao carregar gastos.";
      setLastStatus(status);
      if (isOwnerAuthFailure(status)) {
        clearOwnerSecret();
        setPassword("");
        setData(null);
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

  useEffect(() => {
    if (data !== null || loading || !error || autoRetryUsed.current) return;
    if (!isOwnerTransientFailure(lastStatus, error)) return;
    if (!canTryOwnerSession() && !password) return;
    autoRetryUsed.current = true;
    const id = window.setTimeout(() => {
      void load(password || OWNER_SESSION_TOKEN);
    }, 3500);
    return () => window.clearTimeout(id);
  }, [data, loading, error, lastStatus, password, load]);

  useEffect(() => {
    if (!password || data === null) return;
    const id = window.setInterval(() => void load(password), 20_000);
    return () => window.clearInterval(id);
  }, [password, load, data]);

  function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    const next = draft.trim();
    if (next) void load(next);
  }

  const unlocked = data !== null;
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
        title="Gastos da plataforma"
        loginNext="/gastos"
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
          <h1>Gastos da plataforma</h1>
          <p className="muted">Atualiza a cada 20s · fuso de Brasília · extrato de setembro/2026</p>
        </div>
        <OwnerNav current="gastos" />
        <button
          className="link"
          type="button"
          onClick={() => {
            clearOwnerSecret();
            setPassword("");
            setData(null);
            setDraft("");
            setSessionTried(true);
          }}
        >
          Sair
        </button>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="usage-panel" data-testid="owner-orders">
        <h2>Pedidos</h2>
        <p className="muted">
          Livros pedidos pela família, depois que a foto chega. A imagem abre no pedido.
        </p>
        {(data?.orders ?? []).length ? (
          <div>
            {(data?.orders ?? []).map((order) => (
              <article key={order.id} className="usage-order">
                <pre>{order.summary}</pre>
                {(order.photo_urls ?? []).length > 0 && (
                  <div className="usage-order-photos">
                    {(order.photo_urls ?? []).map((url) => (
                      <figure key={url}>
                        <img src={url} alt="Foto enviada no pedido" />
                        <a href={url} target="_blank" rel="noreferrer">
                          Abrir imagem
                        </a>
                      </figure>
                    ))}
                  </div>
                )}
                <small className="muted">
                  {when(order.created_at)} · Projeto {order.project_id}
                </small>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Nenhum pedido ainda.</p>
        )}
      </section>

      {(data?.anomalies?.length ?? 0) > 0 && (
        <section className="usage-anomalies" aria-live="polite">
          <h2>Alertas de custo</h2>
          <ul>
            {data!.anomalies!.map((a) => (
              <li key={`${a.kind}-${a.message}`} data-severity={a.severity}>
                <strong>{a.severity === "critical" ? "Crítico" : a.severity === "warn" ? "Atenção" : "Info"}</strong>
                <span>{a.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="usage-cards">
        <article>
          <span>Hoje</span>
          <strong>{money(data?.today_usd)}</strong>
          {data?.daily_spend_usd_ceiling != null && (
            <small className="muted">teto {money(data.daily_spend_usd_ceiling)}</small>
          )}
        </article>
        <article>
          <span>Mês</span>
          <strong>{money(data?.month_usd)}</strong>
        </article>
        <article>
          <span>Ticket médio / livro</span>
          <strong>{money(data?.avg_book_usd)}</strong>
        </article>
      </section>

      <section className="usage-panel">
        <h2>Por etapa</h2>
        {data?.by_type.length ? (
          <ul className="usage-bars">
            {data.by_type.map((b) => (
              <li key={b.key}>
                <span>{STEP_LABEL[b.key] ?? b.key}</span>
                <em>{money(b.usd)}</em>
                <small>{b.jobs} job{b.jobs === 1 ? "" : "s"}</small>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Nenhum custo medido neste mês ainda.</p>
        )}
      </section>

      <section className="usage-panel">
        <h2>Por provedor</h2>
        {data?.by_provider.length ? (
          <ul className="usage-bars">
            {data.by_provider.map((b) => (
              <li key={b.key}>
                <span>{PROVIDER_LABEL[b.key] ?? b.key}</span>
                <em>{money(b.usd)}</em>
                <small>{b.jobs} job{b.jobs === 1 ? "" : "s"}</small>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Nenhum provedor medido neste mês ainda.</p>
        )}
      </section>

      <section className="usage-panel">
        <h2>Extrato — cada geração de imagem</h2>
        <p className="muted">
          Setembro/2026 · {data?.events_count ?? 0} linha{(data?.events_count ?? 0) === 1 ? "" : "s"}.
          Jobs antigos aparecem como “sem extrato”.
        </p>
        <div className="usage-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Quando</th>
                <th>Criança</th>
                <th>Chamada</th>
                <th>Provedor</th>
                <th>USD</th>
              </tr>
            </thead>
            <tbody>
              {(data?.events ?? []).map((ev: UsageEvent, idx) => (
                <tr key={ev.id ?? `${ev.job_id}-${idx}`}>
                  <td>{when(ev.created_at)}</td>
                  <td>{ev.child_name || "Sem nome"}</td>
                  <td>{ev.label}</td>
                  <td>{PROVIDER_LABEL[ev.provider] ?? ev.provider}</td>
                  <td>{money(ev.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data?.events?.length && (
            <p className="muted">Nenhuma geração nomeada neste período ainda.</p>
          )}
        </div>
      </section>

      <section className="usage-panel">
        <h2>Livros do período</h2>
        <div className="usage-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Criança</th>
                <th>Status</th>
                <th>USD</th>
                <th>Atualizado</th>
              </tr>
            </thead>
            <tbody>
              {(data?.books ?? []).map((book) => (
                <tr key={book.project_id}>
                  <td>{book.child_name || "Sem nome"}</td>
                  <td>{book.status}</td>
                  <td>
                    {money(book.usd)}
                    {book.unmeasured_jobs > 0 && (
                      <small className="muted"> · {book.unmeasured_jobs} sem medição</small>
                    )}
                  </td>
                  <td>{when(book.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data?.books.length && <p className="muted">Nenhum livro no período.</p>}
        </div>
      </section>
    </div>
  );
}
