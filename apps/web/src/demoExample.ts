import type { Project } from "./types";
import type { Lang } from "./i18n/lang";
import { localizedExample } from "./localizedExamples";

const ex = (file: string) => `${import.meta.env.BASE_URL}exemplos/${file}`;

export const DEMO_EXAMPLE_ID = "dinosaurs";

const DEMO_AT = "2026-01-01T00:00:00.000Z";

const DEMO_STORY = `Página 1: Noé acordou com um rugido suave no quintal. Era um dinossauro amigo, com olhos gentis, pronto para mostrar um caminho secreto entre as árvores.
Página 2: Juntos atravessaram o vale escondido, onde os dinossauros brincavam entre as pedras quentes e as folhas dançavam no vento da manhã.
Página 3: Um filhote perdido chorava atrás de uma folha gigante. Noé segurou a pata dele com cuidado e prometeu ajudá-lo a encontrar o caminho de casa.
Página 4: Seguindo pegadas na terra vermelha, acharam o ninho e a família que esperava, com um abraço grande e cheio de alívio.
Página 5: Na volta, o vale inteiro acompanhou Noé até o portão de casa, em festa silenciosa, como se o dia inteiro tivesse sido um sonho bom.
Página 6: Na cama, Noé sonhou de novo com o vale — e soube que a coragem mora perto de quem a gente ama, em cada aventura compartilhada.`;

const DEMO_TRANSLATIONS = {
  en: {
    title: "Noah In The Land Of Dinosaurs", name: "Noah", dedication: "For Noah, with love.", theme: "An adventure with friendly dinosaurs and courage",
    story: `Page 1: Noah woke to a gentle roar in the backyard. A friendly dinosaur with kind eyes was ready to show him a secret path between the trees.
Page 2: Together they crossed the hidden valley, where dinosaurs played among warm rocks and leaves danced in the morning breeze.
Page 3: A lost baby dinosaur was crying behind a giant leaf. Noah gently held its paw and promised to help it find the way home.
Page 4: Following footprints in the red earth, they found the nest and the waiting family, with a big hug full of relief.
Page 5: On the way back, the whole valley accompanied Noah to his gate in a quiet celebration, as though the entire day had been a happy dream.
Page 6: In bed, Noah dreamed of the valley again — and knew that courage lives close to those we love, in every adventure we share.`,
  },
  es: {
    title: "Noé En La Tierra De Los Dinosaurios", name: "Noé", dedication: "Para Noé, con amor.", theme: "Una aventura con dinosaurios amigables y valentía",
    story: `Página 1: Noé despertó con un suave rugido en el patio. Era un dinosaurio amigo, de ojos amables, listo para mostrarle un camino secreto entre los árboles.
Página 2: Juntos cruzaron el valle escondido, donde los dinosaurios jugaban entre las piedras tibias y las hojas bailaban con la brisa de la mañana.
Página 3: Una cría perdida lloraba detrás de una hoja gigante. Noé le tomó la pata con cuidado y prometió ayudarla a encontrar el camino a casa.
Página 4: Siguiendo huellas en la tierra roja, encontraron el nido y a la familia que esperaba, con un gran abrazo lleno de alivio.
Página 5: De regreso, todo el valle acompañó a Noé hasta la puerta de su casa, en una fiesta silenciosa, como si todo el día hubiera sido un sueño bonito.
Página 6: En la cama, Noé volvió a soñar con el valle — y supo que la valentía vive cerca de quienes amamos, en cada aventura compartida.`,
  },
};

export type DemoAssets = {
  cover_url: string;
  in_hand_url: string;
  character_url: string | null;
  realistic_url: string | null;
  extra_characters: { name: string; url: string }[];
  page_images: string[];
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url: string | null;
};

export type DemoExample = {
  project: Project;
  assets: DemoAssets;
  childName: string;
  childAge: string;
  dedication: string;
  bookTitle: string;
  themeText: string;
};

export function demoIdFromSearch(search = window.location.search): string | null {
  const id = new URLSearchParams(search).get("exemplo");
  if (id === DEMO_EXAMPLE_ID || id === "dino" || id === "matteo") return DEMO_EXAMPLE_ID;
  return null;
}

export function getDemoExample(lang: Lang = "pt"): DemoExample {
  const copy = lang === "pt" ? { title: "Noé Na Terra Dos Dinossauros", name: "Noé", dedication: "Para o Noé, com amor.", theme: "Aventura com dinossauros amigáveis e coragem", story: DEMO_STORY } : DEMO_TRANSLATIONS[lang];
  const image = (file: string) => ex(localizedExample(file, lang));
  return {
    childName: copy.name,
    childAge: "5",
    dedication: copy.dedication,
    bookTitle: copy.title,
    themeText: copy.theme,
    project: {
      id: "demo-dinosaurs",
      status: "PREVIEW_READY",
      style: "realistic",
      theme: "dinosaurs",
      extra_theme: null,
      child_name: copy.name,
      child_age: 5,
      dedication: copy.dedication,
      language: lang,
      extra_characters: [],
      story_text: copy.story,
      ebook_url: null,
      video_url: null,
      narrated_video_url: null,
      character_approved_at: DEMO_AT,
      book_approved_at: null,
      print_requested_at: null,
      print_status: null,
      created_at: DEMO_AT,
    },
    assets: {
      cover_url: image("capa-noe.png"),
      in_hand_url: image("foto-noe.png"),
      character_url: null,
      realistic_url: null,
      extra_characters: [],
      page_images: [image("pagina-noe.png")],
      ebook_url: null,
      video_url: null,
      narrated_video_url: null,
    },
  };
}
