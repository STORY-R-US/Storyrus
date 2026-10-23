import { Navigate, useSearchParams } from "react-router-dom";
import { safeNextPath } from "./Auth";

/** Senha ficou no Clerk. O link antigo abre o login. */
export function ForgotPassword() {
  const [params] = useSearchParams();
  const next = safeNextPath(params.get("next"));
  return <Navigate to={`/entrar?next=${encodeURIComponent(next)}`} replace />;
}
