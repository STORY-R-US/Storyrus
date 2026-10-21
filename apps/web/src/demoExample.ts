import type { Project } from "./types";

const ex = (file: string) => `${import.meta.env.BASE_URL}exemplos/${file}`;

export const DEMO_EXAMPLE_ID = "dinosaurs";

const DEMO_AT = "2026-01-01T00:00:00.000Z";

const DEMO_STORY = `Página 1: Matteo acordou com um rugido suave no quintal. Era um dinossauro amigo, com olhos gentis, pronto para mostrar um caminho secreto entre as árvores.
Página 2: Juntos atravessaram o vale escondido, onde os dinossauros brincavam entre as pedras quentes e as folhas dançavam no vento da manhã.
Página 3: Um filhote perdido chorava atrás de uma folha gigante. Matteo segurou a pata dele com cuidado e prometeu ajudá-lo a encontrar o caminho de casa.
Página 4: Seguindo pegadas na terra vermelha, acharam o ninho e a família que esperava, com um abraço grande e cheio de alívio.
Página 5: Na volta, o vale inteiro acompanhou Matteo até o portão de casa, em festa silenciosa, como se o dia inteiro tivesse sido um sonho bom.
Página 6: Na cama, Matteo sonhou de novo com o vale — e soube que a coragem mora perto de quem a gente ama, em cada aventura compartilhada.`;

export type DemoAssets = {
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

export function getDemoExample(): DemoExample {
  return {
    childName: "Matteo",
    childAge: "5",
    dedication: "Para o Matteo, com amor.",
    bookTitle: "Matteo e o vale dos dinossauros",
    themeText: "Aventura com dinossauros amigáveis e coragem",
    project: {
      id: "demo-dinosaurs",
      status: "VIDEO_READY",
      style: "cgi_3d",
      theme: "dinosaurs",
      extra_theme: null,
      child_name: "Matteo",
      child_age: 5,
      dedication: "Para o Matteo, com amor.",
      language: "pt",
      extra_characters: [],
      story_text: DEMO_STORY,
      ebook_url: null,
      video_url: null,
      narrated_video_url: ex("video-dino.mp4"),
      character_approved_at: DEMO_AT,
      book_approved_at: DEMO_AT,
      print_requested_at: null,
      print_status: null,
      created_at: DEMO_AT,
    },
    assets: {
      character_url: ex("personagem-dino.jpg"),
      realistic_url: null,
      extra_characters: [],
      page_images: [
        ex("capa-dino2.jpg"),
        ex("dino-1.jpg"),
        ex("dino-3.jpg"),
        ex("dino-4.jpg"),
        ex("dino-5.jpg"),
        ex("dino-6.jpg"),
      ],
      ebook_url: null,
      video_url: null,
      narrated_video_url: ex("video-dino.mp4"),
    },
  };
}
