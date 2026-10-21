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
 * Portão dos painéis admin. Com sessão do estúdio, prioriza abrir sozinho e
 * retry no cold start do Render — a senha do painel fica como alternativa.
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
              ? "Abrindo com a sua sessão… Se a API estiver acordando (Render free), pode levar cerca de um minuto."
              : "Não deu para abrir agora. O servidor pode estar acordando — tente de novo."}
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
          Painel admin. O caminho mais simples:{" "}
          <a href={`/entrar?next=${encodeURIComponent(loginNext)}`}>entrar com a conta admin</a> — o
          painel abre sozinho.
          {hasSession ? (
            <>
              {" "}
              Você já está logado:{" "}
              <button
                type="button"
                className="link"
                data-testid="owner-access-use-session"
                disabled={loading}
                onClick={onRetrySession}
              >
                abrir com esta sessão
              </button>
              .
            </>
          ) : null}{" "}
          Alternativa: senha do painel no Render (<code>USAGE_DASHBOARD_PASSWORD</code>), não a senha
          da conta.
        </p>
        {getToken() && loading && <p className="muted">Abrindo com a sessão do estúdio…</p>}
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
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
