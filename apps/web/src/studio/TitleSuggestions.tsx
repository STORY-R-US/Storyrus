import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStudioI18n } from "./useStudioI18n";

const COPY = {
  pt: {
    heading: "Um título ainda mais especial", description: "A IA lê o tema e a história do livro para sugerir cinco novos títulos. Escolha seu favorito e confirme em Atualizar título.",
    guidance: "Como você gostaria de melhorar o título? (opcional)", placeholder: "Ex.: mais divertido, curto ou com um toque de aventura",
    generate: "Sugerir 5 títulos com IA", loading: "A IA está preparando cinco sugestões…", again: "Gerar outras 5 opções com IA",
    results: "Sugestões geradas pela IA", choose: "Escolher", selected: "Selecionado", failure: "Não foi possível gerar as sugestões. Tente novamente.",
  },
  en: {
    heading: "An even more special title", description: "AI uses the book's theme and story to suggest five new titles. Choose your favorite and confirm with Update title.",
    guidance: "How would you like to improve the title? (optional)", placeholder: "E.g. more playful, shorter or more adventurous",
    generate: "Suggest 5 titles with AI", loading: "AI is preparing five suggestions…", again: "Generate 5 more options with AI",
    results: "AI-generated suggestions", choose: "Choose", selected: "Selected", failure: "Could not generate suggestions. Please try again.",
  },
  es: {
    heading: "Un título aún más especial", description: "La IA usa el tema y la historia del libro para sugerir cinco títulos nuevos. Elige tu favorito y confirma con Actualizar título.",
    guidance: "¿Cómo te gustaría mejorar el título? (opcional)", placeholder: "Ej.: más divertido, corto o con un toque de aventura",
    generate: "Sugerir 5 títulos con IA", loading: "La IA está preparando cinco sugerencias…", again: "Generar otras 5 opciones con IA",
    results: "Sugerencias generadas por IA", choose: "Elegir", selected: "Seleccionado", failure: "No se pudieron generar las sugerencias. Inténtalo de nuevo.",
  },
};

export function TitleSuggestions({ projectId, currentTitle, selectedTitle, disabled, onSelect }: {
  projectId: string; currentTitle: string; selectedTitle: string; disabled: boolean; onSelect: (title: string) => void;
}) {
  const { lang } = useStudioI18n();
  const t = COPY[lang];
  const [guidance, setGuidance] = useState("");
  const [titles, setTitles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);
  useEffect(() => {
    request.current += 1;
    setTitles([]);
    setError("");
    setLoading(false);
    return () => { request.current += 1; };
  }, [projectId, currentTitle]);

  async function generate() {
    if (disabled || loading) return;
    const id = ++request.current;
    setLoading(true);
    setError("");
    try {
      const result = await api.suggestPreviewTitles(projectId, guidance.trim());
      if (id === request.current) setTitles(result.titles);
    } catch (e) {
      if (id === request.current) setError((e as Error).message || t.failure);
    } finally {
      if (id === request.current) setLoading(false);
    }
  }

  return (
    <section className="master-title-suggestions" aria-label={t.heading}>
      <h4>{t.heading}</h4>
      <p className="master-title-hint">{t.description}</p>
      <label className="studio-field">
        {t.guidance}
        <textarea value={guidance} onChange={(e) => setGuidance(e.target.value)} maxLength={500}
          rows={2} placeholder={t.placeholder} disabled={disabled || loading} />
      </label>
      <button type="button" className="kbtn kbtn-soft" disabled={disabled || loading} onClick={() => void generate()}>
        {loading ? t.loading : titles.length ? t.again : t.generate}
      </button>
      <div aria-live="polite" aria-busy={loading}>
        {loading && <p className="master-title-hint" role="status">{t.loading}</p>}
        {error && <p className="studio-error" role="alert">{error}</p>}
        {titles.length > 0 && (
          <ol className="master-title-options" aria-label={t.results}>
            {titles.map((title) => (
              <li key={title}>
                <button type="button" className={selectedTitle === title ? "is-selected" : ""}
                  aria-pressed={selectedTitle === title} disabled={disabled || loading} onClick={() => onSelect(title)}>
                  <span>{title}</span><span className="master-title-choice">{selectedTitle === title ? t.selected : t.choose}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
