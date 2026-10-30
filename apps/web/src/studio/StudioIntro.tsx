import type { Lang } from "../i18n/lang";

const COPY = {
  pt: { label: "Estúdio Story R Us", title: "Um livro com a sua história.", lead: "Pessoas especiais, memórias bonitas e uma história que só vocês poderiam viver.", book: "Era uma vez…", note: "Feito para guardar. E para abraçar.", characters: "Personagens e história", details: "Os detalhes do seu livro", photos: "Fotos e autorização" },
  en: { label: "Story R Us Studio", title: "A book with your story.", lead: "Special people, beautiful memories, and a story only you could live.", book: "Once upon a time…", note: "Made to treasure. And to hold close.", characters: "Characters and story", details: "Your book's details", photos: "Photos and authorization" },
  es: { label: "Estudio Story R Us", title: "Un libro con tu historia.", lead: "Personas especiales, recuerdos bonitos y una historia que solo ustedes podrían vivir.", book: "Érase una vez…", note: "Hecho para guardar. Y para abrazar.", characters: "Personajes e historia", details: "Los detalles de tu libro", photos: "Fotos y autorización" },
};

export function studioDesignCopy(lang: Lang) { return COPY[lang]; }

export function StudioIntro({ lang }: { lang: Lang }) {
  const copy = COPY[lang];
  return (
    <section className="studio-intro" aria-labelledby="studio-intro-heading">
      <div className="studio-intro-copy">
        <p className="studio-eyebrow"><span aria-hidden="true">✦</span> {copy.label}</p>
        <h1 id="studio-intro-heading">{copy.title}</h1>
        <p>{copy.lead}</p>
        <span className="studio-intro-note">{copy.note}</span>
      </div>
      <div className="studio-book-art" aria-hidden="true">
        <span className="studio-art-star star-one">✦</span>
        <span className="studio-art-star star-two">✧</span>
        <div className="studio-art-book"><span className="studio-art-sun" /><span className="studio-art-name">{copy.book}</span><span className="studio-art-hill" /><span className="studio-art-brand">STORY R US</span></div>
        <span className="studio-art-star star-three">✦</span>
      </div>
    </section>
  );
}
