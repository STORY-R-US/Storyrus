import type { Lang } from "../i18n/lang";
import { localizedExample } from "../localizedExamples";

const COPY = {
  pt: { label: "Story R Us", title: "Transformamos a sua história em um livro único.", lead: "Reunimos quem você ama e os momentos que marcaram a sua vida em uma obra exclusiva — feita para presentear e colecionar.", book: "Era uma vez…", note: "Pessoas inesquecíveis, memórias eternas.", characters: "Personagens e história", details: "Os detalhes do seu livro", photos: "Fotos e autorização", start: "Começar meu livro" },
  en: { label: "Story R Us", title: "We Turn Your Story Into a One-of-a-Kind Book.", lead: "We bring together the people you love and the moments that marked your life in an exclusive keepsake — made to gift and to collect.", book: "Once upon a time…", note: "Unforgettable people, everlasting memories.", characters: "Characters And Story", details: "Your Book's Details", photos: "Photos And Authorization", start: "Start my book" },
  es: { label: "Story R Us", title: "Transformamos tu historia en un libro único.", lead: "Reunimos a quienes amas y los momentos que marcaron tu vida en una obra exclusiva — hecha para regalar y coleccionar.", book: "Érase una vez…", note: "Personas inolvidables, recuerdos eternos.", characters: "Personajes e historia", details: "Los detalles de tu libro", photos: "Fotos y autorización", start: "Empezar mi libro" },
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
