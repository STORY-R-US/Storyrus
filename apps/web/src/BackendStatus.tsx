import { useSyncExternalStore } from "react";
import { isBackendWarming, subscribeBackendConnection } from "./backendConnection";
import { readStoredLang } from "./i18n/lang";

const COPY = {
  pt: {
    warming: "Estamos preparando sua conexão. Isso pode levar até um minuto e meio. Aguarde…",
    failed: "Não foi possível conectar agora. Sua sessão foi mantida.",
    retry: "Tentar novamente",
  },
  en: {
    warming: "We’re preparing your connection. This may take up to a minute and a half. Please wait…",
    failed: "We couldn’t connect right now. You’re still signed in.",
    retry: "Try again",
  },
  es: {
    warming: "Estamos preparando tu conexión. Puede tardar hasta un minuto y medio. Espera…",
    failed: "No pudimos conectar ahora. Tu sesión se ha conservado.",
    retry: "Intentar de nuevo",
  },
};

export function BackendStatus() {
  const warming = useSyncExternalStore(subscribeBackendConnection, isBackendWarming);
  if (!warming) return null;
  return <div className="backend-status" role="status">{COPY[readStoredLang()].warming}</div>;
}

export function ConnectionRetry({ onRetry }: { onRetry: () => void }) {
  const copy = COPY[readStoredLang()];
  return (
    <div className="card" role="alert" data-testid="connection-error">
      <p>{copy.failed}</p>
      <button type="button" onClick={onRetry}>{copy.retry}</button>
    </div>
  );
}
