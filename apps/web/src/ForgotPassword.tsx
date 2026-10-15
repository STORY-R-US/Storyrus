import { FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import logo from "./assets/logo.png";
import { api } from "./api";
import { safeNextPath } from "./Auth";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

/**
 * Pedido de link para redefinir senha (a partir do login).
 */
export function ForgotPassword() {
  usePageMeta(staticPageMeta("/esqueci-senha"));
  const [params] = useSearchParams();
  const next = useMemo(() => safeNextPath(params.get("next")), [params]);
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      const msg = ((err as Error).message || "").trim();
      if (
        /^429\b/i.test(msg) ||
        /muitos pedidos|too many|rate/i.test(msg)
      ) {
        setError("Muitos pedidos. Aguarde alguns minutos e tente de novo.");
      } else if (
        /^502\b|^503\b|^504\b/i.test(msg) ||
        /failed to fetch|networkerror|load failed|demorou demais|abort/i.test(msg)
      ) {
        setError("Não foi possível enviar agora. Tente de novo em instantes.");
      } else {
        setError(msg.replace(/^\d{3}:\s*/i, "").trim() || "Algo deu errado.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="kid auth-kid" data-testid="forgot-password-page">
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-logo">
            <Link to="/">
              <img src={logo} alt="Story R Us" />
            </Link>
          </div>
          <SiteBackNav />
          {sent ? (
            <>
              <h1>Verifique Seu E-mail</h1>
              <p className="auth-lead" data-testid="forgot-password-sent">
                Se este e-mail estiver cadastrado, enviamos um link para redefinir a senha.
              </p>
              <p className="auth-lead auth-check-hint">
                Não recebeu? Confira o spam ou tente de novo em alguns minutos.
              </p>
            </>
          ) : (
            <>
              <h1>Esqueci A Senha</h1>
              <p className="auth-lead">
                Informe o e-mail da conta. Enviaremos um link para escolher uma nova senha.
              </p>
              <form className="auth-form" onSubmit={onSubmit} data-testid="forgot-password-form">
                <label>
                  E-mail
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    data-testid="forgot-password-email"
                  />
                </label>
                {error && (
                  <p className="auth-error" role="alert" data-testid="forgot-password-error">
                    {error}
                  </p>
                )}
                <button
                  type="submit"
                  className="kbtn kbtn-primary auth-cta"
                  disabled={busy}
                  data-testid="forgot-password-submit"
                >
                  {busy ? "Aguarde…" : "Enviar Link"}
                </button>
              </form>
            </>
          )}
          <p className="auth-foot">
            <Link
              to={`/entrar?next=${encodeURIComponent(next)}`}
              data-testid="forgot-password-login"
            >
              Voltar Ao Login
            </Link>
          </p>
          <p className="auth-foot">
            <Link to="/" data-testid="forgot-password-back">
              Voltar Ao Início
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
