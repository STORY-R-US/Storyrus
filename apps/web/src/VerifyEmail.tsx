import { Navigate, useSearchParams } from "react-router-dom";
import { accountGateHref, safeNextPath } from "./Auth";

/** O Clerk confirma o e-mail. Este endereço antigo volta para o cadastro. */
export function VerifyEmail() {
  const [params] = useSearchParams();
  return <Navigate to={accountGateHref(safeNextPath(params.get("next")))} replace />;
}
