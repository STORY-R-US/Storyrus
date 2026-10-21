import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import logo from "./assets/logo.png";
import { api } from "./api";
import { readAuthQueryEmail, readAuthQueryToken, safeNextPath } from "./Auth";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

/**
 * Confirma o e-mail via token da query e abre sessão no estúdio.
 */
export function VerifyEmail() {
  usePageMeta(staticPageMeta("/verificar-email"));
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const token = useMemo(
    () => readAuthQueryToken(location.search),
    [location.search],
  );
  const email = useMemo(
    () => readAuthQueryEmail(location.search),
    [location.search],
  );
  const next = useMemo(() => safeNextPath(params.get("next")), [params]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [resendHint, setResendHint] = useState<string | null>(null);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!token) {
        if (!cancelled) {
          setError("Link inválido. Solicite um novo cadastro.");
          setBusy(false);
        }
        return;
      }
      try {
        await api.verifyEmail(token);
        if (!cancelled) navigate(next, { replace: true });
      } catch (err) {
        if (!cancelled) {
          const raw = ((err as Error).message || "").trim();
          const friendly =
            /^502\b|^503\b|^504\b/i.test(raw) ||
            /failed to fetch|networkerror|load failed|demorou demais|abort/i.test(raw)
              ? "Não foi possível confirmar agora. Tente de novo em instantes."
              : raw.replace(/^\d{3}:\s*/i, "").trim() || "Link inválido ou expirado.";
          setError(friendly);
          setBusy(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate, next, token]);

  async function onResend() {
    if (!email) return;
    setResending(true);
    setResendHint(null);
    try {
      await api.resendVerify(email);
      setResendHint("Se a conta estiver pendente, enviamos um novo link.");
    } catch {
      setResendHint("Se a conta estiver pendente, enviamos um novo link.");
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="kid auth-kid" data-testid="verify-email-page">
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-logo">
            <Link to="/">
              <img src={logo} alt="Story R Us" />
            </Link>
          </div>
          <SiteBackNav />
          <h1>Confirmando E-mail</h1>
          {email ? (
            <p className="auth-lead" data-testid="verify-email-address">
              {email}
            </p>
          ) : null}
          {busy && !error && (
            <p className="auth-lead" data-testid="verify-email-busy">
              Aguarde…
            </p>
          )}
          {error && (
            <>
              <p className="auth-error" role="alert" data-testid="verify-email-error">
                {error}
              </p>
              {resendHint && (
                <p className="auth-lead auth-check-hint" data-testid="verify-email-resend-hint">
                  {resendHint}
                </p>
              )}
              {email ? (
                <p className="auth-foot">
                  <button
                    type="button"
                    disabled={resending}
                    onClick={() => void onResend()}
                    data-testid="verify-email-resend"
                  >
                    {resending ? "Enviando…" : "Reenviar E-mail De Confirmação"}
                  </button>
                </p>
              ) : null}
              <p className="auth-foot">
                <Link to="/cadastro" data-testid="verify-email-signup">
                  Criar Conta De Novo
                </Link>
              </p>
              <p className="auth-foot">
                <Link to="/entrar" data-testid="verify-email-login">
                  Já Confirmei — Entrar
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
