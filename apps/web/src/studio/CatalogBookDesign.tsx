import { useState } from "react";
import { PreviewImageViewer } from "./PreviewImageViewer";

type Lang = "pt" | "en" | "es";
export type CatalogDesignId = "auto" | "family" | "adventure" | "cartoon";
type Model = { name: string; sources: { cover: string; page: string; holding: string } };
const MODELS: Record<Exclude<CatalogDesignId, "auto">, Model> = {
  family: { name: "Amor de Bisavó", sources: { cover: "capa-amordebisavo.jpg", page: "pagina-amordebisavo.jpg", holding: "foto-amordebisavo.jpg" } },
  adventure: { name: "Meu Pai, Meu Herói", sources: { cover: "capa-meupai-heroi.png", page: "pagina-meupai-heroi.png", holding: "foto-meupai-heroi.png" } },
  cartoon: { name: "Amor de Mãe — cartoon", sources: { cover: "cartoon-capa-amordemae.jpg", page: "cartoon-pagina-amordemae.jpg", holding: "cartoon-foto-amordemae.jpg" } },
};
const COPY = {
  pt: { title: "Padrão visual do livro", hint: "Este modelo define o conjunto: capa, título, texto, miolo e apresentação do livro nas mãos. A história e as pessoas serão as suas.", auto: "Definir pelo tema", sample: "Ver o modelo completo do Catálogo", cover: "Capa", page: "Livro aberto", holding: "Segurando o livro", enlarge: "Ampliar referência" },
  en: { title: "Book visual design", hint: "This model defines the complete book: cover, title, text, interior and held-book presentation. The story and people will be yours.", auto: "Choose by theme", sample: "View the complete catalog model", cover: "Cover", page: "Open book", holding: "Holding the book", enlarge: "Enlarge reference" },
  es: { title: "Diseño visual del libro", hint: "Este modelo define el conjunto: portada, título, texto, interior y presentación en las manos. La historia y las personas serán las tuyas.", auto: "Elegir según el tema", sample: "Ver el modelo completo del Catálogo", cover: "Portada", page: "Libro abierto", holding: "Sosteniendo el libro", enlarge: "Ampliar referencia" },
};

export function CatalogDesignSamples({ model, lang }: { model: Model; lang: Lang }) {
  const [expanded, setExpanded] = useState<{ url: string; title: string } | null>(null);
  const t = COPY[lang];
  return <details className="catalog-book-design-samples">
    <summary>{t.sample}: {model.name}</summary>
    <div className="catalog-book-design-trio">
      {(["cover", "page", "holding"] as const).map((role) => <figure key={role}>
        <img src={`/exemplos/${model.sources[role]}`} alt={`${model.name} · ${t[role]}`} loading="lazy" />
        <figcaption>{t[role]} <button type="button" onClick={() => setExpanded({ url: `/exemplos/${model.sources[role]}`, title: `${model.name} · ${t[role]}` })}>{t.enlarge}</button></figcaption>
      </figure>)}
    </div>
    {expanded && <PreviewImageViewer src={expanded.url} title={expanded.title} lang={lang} onClose={() => setExpanded(null)} />}
  </details>;
}

export function CatalogBookDesign({ value, onChange, cartoon, disabled, lang }: {
  value: CatalogDesignId; onChange: (value: CatalogDesignId) => void; cartoon: boolean; disabled: boolean; lang: Lang;
}) {
  const t = COPY[lang];
  return <section className="catalog-book-design-choice">
    <label className="studio-field">{t.title}
      <select aria-label={t.title} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value as CatalogDesignId)}>
        <option value="auto">{t.auto}</option>
        {(cartoon ? ["cartoon"] as const : ["family", "adventure"] as const).map((id) => <option key={id} value={id}>{MODELS[id].name}</option>)}
      </select>
    </label>
    <p className="muted field-hint">{t.hint}</p>
    {value !== "auto" && <CatalogDesignSamples model={MODELS[value]} lang={lang} />}
  </section>;
}
