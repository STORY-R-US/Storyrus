import type { Lang } from "../i18n/lang";
import { localizedExample } from "../localizedExamples";

const COPY = {
  pt: { label: "Story R Us", title: "Transformamos a Sua História em um Livro Único.", lead: "Reunimos quem você ama e os momentos que marcaram a sua vida em uma obra exclusiva — feita para presentear e colecionar.", book: "Era uma vez…", note: "Pessoas inesquecíveis, memórias eternas.", characters: "Personagens E História", details: "Os Detalhes Do Seu Livro", photos: "Fotos E Autorização", start: "Começar meu livro" },
  en: { label: "Story R Us", title: "We Turn Your Story Into a One-of-a-Kind Book.", lead: "We bring together the people you love and the moments that marked your life in an exclusive keepsake — made to gift and to collect.", book: "Once upon a time…", note: "Unforgettable people, everlasting memories.", characters: "Characters And Story", details: "Your Book's Details", photos: "Photos And Authorization", start: "Start my book" },
  es: { label: "Story R Us", title: "Transformamos Tu Historia en un Libro Único.", lead: "Reunimos a quienes amas y los momentos que marcaron tu vida en una obra exclusiva — hecha para regalar y coleccionar.", book: "Érase una vez…", note: "Personas inolvidables, recuerdos eternos.", characters: "Personajes E Historia", details: "Los Detalles De Tu Libro", photos: "Fotos Y Autorización", start: "Empezar mi libro" },
};

export function studioDesignCopy(lang: Lang) { return COPY[lang]; }

export function StudioIntro({ lang }: { lang: Lang }) {
  const copy = COPY[lang];
  // Capa do livro "O Amor de Mãe" no idioma da página.
  const cover = `${import.meta.env.BASE_URL}exemplos/${localizedExample("capa-amordemae.jpg", lang)}`;
  return (
    <section className="studio-intro" aria-labelledby="studio-intro-heading">
      <div className="studio-intro-copy">
        <p className="studio-eyebrow"><span aria-hidden="true">✦</span> {copy.label}</p>
        <h1 id="studio-intro-heading">{copy.title}</h1>
        <span className="studio-intro-note">{copy.note}</span>
        <p>{copy.lead}</p>
        <button type="button" className="kbtn kbtn-primary studio-intro-start" data-testid="studio-intro-start"
          onClick={() => document.getElementById("studio-create-heading")?.scrollIntoView?.({ behavior: "smooth", block: "start" })}>
          {copy.start} ↓
        </button>
      </div>
      <div className="studio-book-art" aria-hidden="true">
        <span className="studio-art-star star-one">✦</span>
        <span className="studio-art-star star-two">✧</span>
        <div className="studio-art-book has-cover"><img src={cover} alt="" decoding="async" /></div>
        <span className="studio-art-star star-three">✦</span>
      </div>
    </section>
  );
}
