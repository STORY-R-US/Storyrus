import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { Project } from "../types";

const COPY = {
  pt: { heading: "Revisar os textos antes de tentar novamente", hint: "Você pode encurtar o título ou os trechos. Salvar apenas corrige os textos; não gera imagens nem faz novas cobranças de geração.", title: "Título da capa", left: "Primeiro trecho", right: "Segundo trecho", save: "Salvar textos", saving: "Salvando…", saved: "Textos salvos. Use Tentar prévia de novo para continuar." },
  en: { heading: "Review the text before retrying", hint: "You can shorten the title or passages. Saving only updates the text; it does not generate images or incur new generation charges.", title: "Cover title", left: "First passage", right: "Second passage", save: "Save text", saving: "Saving…", saved: "Text saved. Use Retry preview to continue." },
  es: { heading: "Revisar los textos antes de reintentar", hint: "Puedes acortar el título o los fragmentos. Guardar solo corrige los textos; no genera imágenes ni produce nuevos cargos de generación.", title: "Título de la portada", left: "Primer fragmento", right: "Segundo fragmento", save: "Guardar textos", saving: "Guardando…", saved: "Textos guardados. Usa Reintentar vista previa para continuar." },
};

export function PreviewCopyRecovery({ project, lang, onSaved }: { project: Project; lang: "pt" | "en" | "es"; onSaved: (project: Project) => void }) {
  const initial = project.book_profile?.locales?.[project.language || "pt-BR"];
  const [draft, setDraft] = useState(initial || { title: "", left: "", right: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const t = COPY[lang];
  if (!initial) return null;
  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      onSaved(await api.savePreviewCopy(project.id, draft));
      setMessage(t.saved);
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  return <details className="master-child-edit" data-testid="preview-copy-recovery">
    <summary>{t.heading}</summary>
    <form onSubmit={(event) => void save(event)}>
      <p>{t.hint}</p>
      <label className="studio-field">{t.title}<input required maxLength={120} value={draft.title} disabled={busy} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
      {(["left", "right"] as const).map((key) => <label className="studio-field" key={key}>{t[key]}<textarea required maxLength={2000} rows={4} value={draft[key]} disabled={busy} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} /></label>)}
      <button type="submit" className="kbtn kbtn-soft" disabled={busy}>{busy ? t.saving : t.save}</button>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </form>
  </details>;
}
