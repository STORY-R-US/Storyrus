import { FormEvent, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import logo from "./assets/logo.png";
import { api } from "./api";
import { readAuthQueryToken, safeNextPath } from "./Auth";
import { PasswordField } from "./PasswordField";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

/**
 * Define nova senha a partir do token do e-mail e abre sessão no estúdio.
 */
export function ResetPassword() {
  usePageMeta(staticPageMeta("/redefinir-senha"));
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const token = useMemo(() => readAuthQueryToken(location.search), [location.search]);
  const next = useMemo(() => safeNextPath(params.get("next")), [params]);
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) {
      setError("Link inválido. Solicite um novo em Esqueci A Senha.");
      return;
    }
    if (password !== passwordConfirm) {
      setError("As senhas não coincidem.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(token, password, passwordConfirm);
      navigate(next, { replace: true });
    } catch (err) {
      const msg = ((err as Error).message || "").trim();
      if (
        /^502\b|^503\b|^504\b/i.test(msg) ||
        /failed to fetch|networkerror|load failed|demorou demais|abort/i.test(msg)
      ) {
        setError("Não foi possível redefinir agora. Tente de novo em instantes.");
      } else {
        setError(
          msg.replace(/^\d{3}:\s*/i, "").trim() || "Link inválido ou expirado.",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="kid auth-kid" data-testid="reset-password-page">
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-logo">
            <Link to="/">
              <img src={logo} alt="Story R Us" />
            </Link>
          </div>
          <SiteBackNav />
          <h1>Nova Senha</h1>
          <p className="auth-lead">Escolha uma senha nova para a sua conta.</p>
          {!token ? (
            <>
              <p className="auth-error" role="alert" data-testid="reset-password-error">
                Link inválido. Solicite um novo em Esqueci A Senha.
              </p>
              <p className="auth-foot">
                <Link to="/esqueci-senha" data-testid="reset-password-forgot">
                  Esqueci A Senha
                </Link>
              </p>
            </>
          ) : (
            <form className="auth-form" onSubmit={onSubmit} data-testid="reset-password-form">
              <PasswordField
                label="Nova Senha (Mín. 8)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                testId="reset-password-password"
              />
              <PasswordField
                label="Confirmar Senha"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                autoComplete="new-password"
                testId="reset-password-confirm"
              />
              {error && (
                <p className="auth-error" role="alert" data-testid="reset-password-error">
                  {error}
                </p>
              )}
              <button
                type="submit"
                className="kbtn kbtn-primary auth-cta"
                disabled={busy}
                data-testid="reset-password-submit"
              >
                {busy ? "Aguarde…" : "Salvar Senha"}
              </button>
            </form>
          )}
          <p className="auth-foot">
            <Link to="/entrar" data-testid="reset-password-login">
              Voltar Ao Login
            </Link>
          </p>
          <p className="auth-foot">
            <Link to="/" data-testid="reset-password-home">
              Voltar Ao Início
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
