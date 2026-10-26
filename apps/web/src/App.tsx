import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { accountAccess, accountGateHref } from "./Auth";
import { api, setToken } from "./api";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { Studio } from "./Studio";
import { ConnectionRetry } from "./BackendStatus";

function demoIdFromSearch(search: string): string | null {
  const q = new URLSearchParams(search);
  const ex = q.get("exemplo");
  return ex && ex.trim() ? ex.trim() : null;
}

/**
 * Estúdio exige conta registrada (exceto visualização de exemplo ?exemplo=).
 * Sem sessão, convidado, e-mail pendente ou endereço vazio → cadastro.
 * Só a sessão inválida (401) e o convidado legado são deslogados.
 */
export function App() {
  usePageMeta(staticPageMeta("/app"));
  const location = useLocation();
  const navigate = useNavigate();
  const isDemo = Boolean(demoIdFromSearch(location.search));
  const [gate, setGate] = useState<"loading" | "ok" | "need-account" | "error">(
    isDemo ? "ok" : "loading",
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (isDemo) {
      setGate("ok");
      return;
    }
    let cancelled = false;
    (async () => {
      const openAccount = (me: Awaited<ReturnType<typeof api.me>>) => {
        if (cancelled) return;
        const access = accountAccess(me);
        if (access === "guest") api.logout();
        setGate(access === "ok" ? "ok" : "need-account");
      };
      try {
        openAccount(await api.me());
      } catch (error) {
        if (cancelled) return;
        if (!/^401:/.test((error as Error).message)) {
          setGate("error");
          return;
        }
        // Token antigo do login por senha: solta e tenta a sessão do Clerk.
        setToken(null);
        try {
          openAccount(await api.me());
        } catch (retryError) {
          if (cancelled) return;
          if (/^401:/.test((retryError as Error).message)) {
            api.logout();
            setGate("need-account");
          } else {
            setGate("error");
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isDemo, location.search, attempt]);

  if (gate === "loading") return null;
  if (gate === "error") return <ConnectionRetry onRetry={() => {
    setGate("loading");
    setAttempt((value) => value + 1);
  }} />;
  if (gate === "need-account") {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={accountGateHref(next)} replace />;
  }

  return (
    <Studio
      onLogout={() => {
        api.logout();
        navigate("/entrar", { replace: true });
      }}
    />
  );
}
