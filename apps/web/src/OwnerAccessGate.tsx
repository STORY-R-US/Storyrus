import { FormEvent, useState } from "react";
import logo from "./assets/logo.png";
import { getToken } from "./api";
import { canTryOwnerSession } from "./ownerSession";

type Props = {
  title: string;
  loginNext: string;
  draft: string;
  onDraftChange: (value: string) => void;
  onSubmitPassword: (ev: FormEvent) => void;
  onRetrySession: () => void;
  loading: boolean;
  error: string | null;
  /** Tentando JWT / senha salva — não mostra o form de senha como caminho principal. */
  opening: boolean;
  /** Falha temporária (rede / cold start); oferece tentar de novo com a sessão. */
  transient: boolean;
};

/**
 * Portão dos painéis. Com a sessão da conta, abre sozinho.
 * A senha do painel fica escondida, como alternativa.
 */
export function OwnerAccessGate({
  title,
  loginNext,
  draft,
  onDraftChange,
  onSubmitPassword,
  onRetrySession,
  loading,
  error,
  opening,
  transient,
}: Props) {
  const [showPassword, setShowPassword] = useState(false);
  const hasSession = canTryOwnerSession();
  const preferSession = hasSession && (opening || transient) && !showPassword;

  if (preferSession) {
    return (
      <div className="usage">
        <div className="usage-gate card auth" data-testid="owner-access-opening">
          <img className="auth-logo" src={logo} alt="Story R Us" />
          <h1>{title}</h1>
          <p className="muted">
            {loading
              ? "Abrindo os pedidos da conta da Story R Us…"
              : "Não deu para abrir agora. Tente de novo."}
          </p>
          {error && <p className="error">{error}</p>}
          <button
            type="button"
            data-testid="owner-access-retry"
            disabled={loading}
            onClick={onRetrySession}
          >
            {loading ? "Abrindo…" : "Tentar de novo"}
          </button>
          <p className="muted" style={{ marginTop: "1rem" }}>
            <button
              type="button"
              className="link"
              data-testid="owner-access-show-password"
              onClick={() => setShowPassword(true)}
            >
              Usar senha do painel
            </button>
            {" · "}
            <a href={`/entrar?next=${encodeURIComponent(loginNext)}`}>Trocar de conta</a>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="usage">
      <div className="usage-gate card auth" data-testid="owner-access-gate">
        <img className="auth-logo" src={logo} alt="Story R Us" />
        <h1>{title}</h1>
        <p className="muted">
          Entre com a conta da Story R Us. O painel abre com essa sessão.
        </p>
        <a className="order-open" href={`/entrar?next=${encodeURIComponent(loginNext)}`}>
          Entrar
        </a>
        {hasSession ? (
          <p className="muted">
            <button
              type="button"
              className="link"
              data-testid="owner-access-use-session"
              disabled={loading}
              onClick={onRetrySession}
            >
              Abrir com a sessão atual
            </button>
          </p>
        ) : null}
        {getToken() && loading && <p className="muted">Abrindo os pedidos…</p>}
        <details className="order-panel-secret">
          <summary>Usar a senha do painel</summary>
          <form onSubmit={onSubmitPassword}>
            <label>
              Senha do painel
              <input
                type="password"
                name="panel-secret"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                value={draft}
                onChange={(e) => onDraftChange(e.target.value)}
              />
            </label>
            <button type="submit" disabled={!draft.trim() || loading}>
              {loading ? "Abrindo…" : "Entrar"}
            </button>
          </form>
        </details>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
