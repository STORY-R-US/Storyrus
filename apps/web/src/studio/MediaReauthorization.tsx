import { useState } from "react";
import { api } from "../api";
import type { Lang } from "../i18n/lang";
import { PRIVACY_NOTICE } from "../privacyNotice";

export function MediaReauthorization({ projectId, lang, onAuthorized }: {
  projectId: string; lang: Lang; onAuthorized: () => void;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const t = PRIVACY_NOTICE[lang];
  return <aside className="studio-card studio-privacy-notice" aria-label={t.title}>
    <span className="studio-privacy-symbol" aria-hidden="true">✓</span>
    <div><h3>{t.title}</h3><p>{t.text}</p><p>{t.rights}</p>
      <a href={lang === "en" ? "/privacy" : "/privacidade"} target="_blank" rel="noreferrer">{t.link}</a>
      <label className="studio-consent"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        {lang === "pt" ? "Sou adulto responsável e autorizo novos usos das fotos deste projeto conforme o aviso." : lang === "en" ? "I am an authorized adult and authorize further use of this project's photos under this notice." : "Soy adulto responsable y autorizo nuevos usos de las fotos de este proyecto según el aviso."}
      </label>
      <button className="kbtn kbtn-primary" type="button" disabled={!confirmed || busy} onClick={async () => {
        setBusy(true); setError("");
        try { await api.authorizeBookMedia(projectId, confirmed); onAuthorized(); }
        catch (reason) { setError((reason as Error).message); }
        finally { setBusy(false); }
      }}>{lang === "pt" ? "Confirmar autorização" : lang === "en" ? "Confirm authorization" : "Confirmar autorización"}</button>
      {error && <p className="studio-error" role="alert">{error}</p>}
    </div>
  </aside>;
}
