import type { Lang } from "./i18n/lang";

/** Quem o livro coloca no centro. O estúdio troca o rótulo e pergunta o gênero. */
export type StudioWho =
  | "child"
  | "pet"
  | "father"
  | "mother"
  | "aunt"
  | "great_grandmother"
  | "cousin"
  | "grandmother"
  | "grandfather";

export type StudioGender = "f" | "m";

export type StudioCast = {
  who: StudioWho;
  gender: StudioGender | null;
  also: { who: StudioWho; gender: StudioGender | null; hero: string | null } | null;
  askGender: boolean;
};

const WHO_CODE: Record<string, StudioWho> = {
  crianca: "child",
  pet: "pet",
  pai: "father",
  mae: "mother",
  tia: "aunt",
  bisavo: "great_grandmother",
  primo: "cousin",
  avo: "grandmother",
  avoh: "grandfather",
};

const CODE_OF: Record<StudioWho, string> = {
  child: "crianca",
  pet: "pet",
  father: "pai",
  mother: "mae",
  aunt: "tia",
  great_grandmother: "bisavo",
  cousin: "primo",
  grandmother: "avo",
  grandfather: "avoh",
};

/** Índice do catálogo → quem entra no formulário. O gênero do exemplo só vem pré-marcado. */
export const CAST_BY_CATALOG: Record<number, { quem: string; genero: StudioGender; quem2?: string; genero2?: StudioGender; heroi2?: string }> = {
  0: { quem: "crianca", genero: "m" },
  1: { quem: "crianca", genero: "f" },
  2: { quem: "crianca", genero: "m" },
  3: { quem: "crianca", genero: "f" },
  4: { quem: "crianca", genero: "m" },
  5: { quem: "crianca", genero: "m" },
  6: { quem: "crianca", genero: "m" },
  7: { quem: "mae", genero: "f" },
  8: { quem: "crianca", genero: "m" },
  9: { quem: "bisavo", genero: "f" },
  10: { quem: "avos", genero: "f" },
  11: { quem: "crianca", genero: "m" },
  12: { quem: "pet", genero: "f" },
  13: { quem: "pet", genero: "m" },
  14: { quem: "crianca", genero: "f" },
  15: { quem: "crianca", genero: "f", quem2: "pai", genero2: "m" },
  16: { quem: "crianca", genero: "f" },
  17: { quem: "crianca", genero: "f" },
  18: { quem: "crianca", genero: "f" },
  19: { quem: "crianca", genero: "m" },
  20: { quem: "tia", genero: "f" },
  21: { quem: "crianca", genero: "m" },
  22: { quem: "pai", genero: "m" },
  23: { quem: "primo", genero: "m" },
  24: { quem: "crianca", genero: "m", quem2: "pet", genero2: "m", heroi2: "Max" },
  25: { quem: "crianca", genero: "f" },
};

type Copy = {
  name: string;
  namePh: string;
  age: string;
  photo: string;
  extras: string;
};

const COPY: Record<Lang, Record<StudioWho, Copy>> = {
  pt: {
    child: {
      name: "Nome do protagonista",
      namePh: "Ex.: Lila",
      age: "Idade",
      photo: "Foto da criança",
      extras: "Nomes separados por vírgula. A criança já entra como protagonista.",
    },
    pet: {
      name: "Nome do pet",
      namePh: "Ex.: Maya",
      age: "Idade do pet",
      photo: "Foto do pet",
      extras: "Nomes separados por vírgula. O pet já entra como protagonista.",
    },
    father: {
      name: "Nome do pai",
      namePh: "Ex.: André",
      age: "Idade do pai",
      photo: "Foto do pai",
      extras: "Nomes separados por vírgula. O pai já entra como protagonista.",
    },
    mother: {
      name: "Nome da mãe",
      namePh: "Ex.: Ana",
      age: "Idade da mãe",
      photo: "Foto da mãe",
      extras: "Nomes separados por vírgula. A mãe já entra como protagonista.",
    },
    aunt: {
      name: "Nome da tia",
      namePh: "Ex.: Helena",
      age: "Idade da tia",
      photo: "Foto da tia",
      extras: "Nomes separados por vírgula. A tia já entra como protagonista.",
    },
    great_grandmother: {
      name: "Nome da bisavó",
      namePh: "Ex.: Rosa",
      age: "Idade da bisavó",
      photo: "Foto da bisavó",
      extras: "Nomes separados por vírgula. A bisavó já entra como protagonista.",
    },
    cousin: {
      name: "Nome do primo",
      namePh: "Ex.: Enzo",
      age: "Idade do primo",
      photo: "Foto do primo",
      extras: "Nomes separados por vírgula. O primo já entra como protagonista.",
    },
    grandmother: {
      name: "Nome da avó",
      namePh: "Ex.: Meme",
      age: "Idade",
      photo: "Foto da avó e do avô",
      extras: "Nomes separados por vírgula. A avó e o avô já entram na história.",
    },
    grandfather: {
      name: "Nome do avô",
      namePh: "Ex.: Tata",
      age: "Idade do avô",
      photo: "Foto do avô",
      extras: "Nomes separados por vírgula. O avô já entra como protagonista.",
    },
  },
  en: {
    child: {
      name: "Protagonist's name",
      namePh: "e.g. Lila",
      age: "Age",
      photo: "Child's photo",
      extras: "Separate names with commas. The child is already the hero.",
    },
    pet: {
      name: "Pet's name",
      namePh: "e.g. Maya",
      age: "Pet's age",
      photo: "Pet's photo",
      extras: "Separate names with commas. The pet is already the hero.",
    },
    father: {
      name: "Father's name",
      namePh: "e.g. Andrew",
      age: "Father's age",
      photo: "Father's photo",
      extras: "Separate names with commas. The father is already the hero.",
    },
    mother: {
      name: "Mother's name",
      namePh: "e.g. Ana",
      age: "Mother's age",
      photo: "Mother's photo",
      extras: "Separate names with commas. The mother is already the hero.",
    },
    aunt: {
      name: "Aunt's name",
      namePh: "e.g. Helena",
      age: "Aunt's age",
      photo: "Aunt's photo",
      extras: "Separate names with commas. The aunt is already the hero.",
    },
    great_grandmother: {
      name: "Great-grandmother's name",
      namePh: "e.g. Rosa",
      age: "Great-grandmother's age",
      photo: "Great-grandmother's photo",
      extras: "Separate names with commas. The great-grandmother is already the hero.",
    },
    cousin: {
      name: "Cousin's name",
      namePh: "e.g. Enzo",
      age: "Cousin's age",
      photo: "Cousin's photo",
      extras: "Separate names with commas. The cousin is already the hero.",
    },
    grandmother: {
      name: "Grandmother's name",
      namePh: "e.g. Meme",
      age: "Age",
      photo: "Photo of grandma and grandpa",
      extras: "Separate names with commas. Grandma and grandpa are already in the story.",
    },
    grandfather: {
      name: "Grandfather's name",
      namePh: "e.g. Tata",
      age: "Grandfather's age",
      photo: "Grandfather's photo",
      extras: "Separate names with commas. The grandfather is already the hero.",
    },
  },
  es: {
    child: {
      name: "Nombre del protagonista",
      namePh: "Ej.: Lila",
      age: "Edad",
      photo: "Foto del niño/a",
      extras: "Separa los nombres con comas. El niño ya entra como protagonista.",
    },
    pet: {
      name: "Nombre de la mascota",
      namePh: "Ej.: Maya",
      age: "Edad de la mascota",
      photo: "Foto de la mascota",
      extras: "Separa los nombres con comas. La mascota ya entra como protagonista.",
    },
    father: {
      name: "Nombre del papá",
      namePh: "Ej.: Andrés",
      age: "Edad del papá",
      photo: "Foto del papá",
      extras: "Separa los nombres con comas. El papá ya entra como protagonista.",
    },
    mother: {
      name: "Nombre de la mamá",
      namePh: "Ej.: Ana",
      age: "Edad de la mamá",
      photo: "Foto de la mamá",
      extras: "Separa los nombres con comas. La mamá ya entra como protagonista.",
    },
    aunt: {
      name: "Nombre de la tía",
      namePh: "Ej.: Helena",
      age: "Edad de la tía",
      photo: "Foto de la tía",
      extras: "Separa los nombres con comas. La tía ya entra como protagonista.",
    },
    great_grandmother: {
      name: "Nombre de la bisabuela",
      namePh: "Ej.: Rosa",
      age: "Edad de la bisabuela",
      photo: "Foto de la bisabuela",
      extras: "Separa los nombres con comas. La bisabuela ya entra como protagonista.",
    },
    cousin: {
      name: "Nombre del primo",
      namePh: "Ej.: Enzo",
      age: "Edad del primo",
      photo: "Foto del primo",
      extras: "Separa los nombres con comas. El primo ya entra como protagonista.",
    },
    grandmother: {
      name: "Nombre de la abuela",
      namePh: "Ej.: Meme",
      age: "Edad",
      photo: "Foto de la abuela y el abuelo",
      extras: "Separa los nombres con comas. La abuela y el abuelo ya entran en la historia.",
    },
    grandfather: {
      name: "Nombre del abuelo",
      namePh: "Ej.: Tata",
      age: "Edad del abuelo",
      photo: "Foto del abuelo",
      extras: "Separa los nombres con comas. El abuelo ya entra como protagonista.",
    },
  },
};

const COUSIN_F: Record<Lang, Pick<Copy, "name" | "namePh" | "age" | "photo" | "extras">> = {
  pt: {
    name: "Nome da prima",
    namePh: "Ex.: Enza",
    age: "Idade da prima",
    photo: "Foto da prima",
    extras: "Nomes separados por vírgula. A prima já entra como protagonista.",
  },
  en: {
    name: "Cousin's name",
    namePh: "e.g. Enza",
    age: "Cousin's age",
    photo: "Cousin's photo",
    extras: "Separate names with commas. The cousin is already the hero.",
  },
  es: {
    name: "Nombre de la prima",
    namePh: "Ej.: Enza",
    age: "Edad de la prima",
    photo: "Foto de la prima",
    extras: "Separa los nombres con comas. La prima ya entra como protagonista.",
  },
};

function asGender(raw: string | null): StudioGender | null {
  return raw === "f" || raw === "m" ? raw : null;
}

function asWho(raw: string | null): StudioWho | null {
  if (!raw) return null;
  return WHO_CODE[raw] ?? null;
}

export function emptyCast(): StudioCast {
  return { who: "child", gender: null, also: null, askGender: true };
}

export function castFromQuery(q: URLSearchParams): StudioCast {
  const quem = q.get("quem");
  if (quem === "avos") {
    return {
      who: "grandmother",
      gender: "f",
      also: { who: "grandfather", gender: "m", hero: q.get("heroi2") },
      askGender: false,
    };
  }
  const who = asWho(quem) ?? "child";
  const alsoWho = asWho(q.get("quem2"));
  return {
    who,
    gender: asGender(q.get("genero")),
    also: alsoWho
      ? { who: alsoWho, gender: asGender(q.get("genero2")), hero: q.get("heroi2") }
      : null,
    askGender: true,
  };
}

export function subjectCode(who: StudioWho): string {
  return CODE_OF[who];
}

export function ageLimit(who: StudioWho): number {
  if (who === "pet") return 25;
  if (
    who === "father" ||
    who === "mother" ||
    who === "aunt" ||
    who === "great_grandmother" ||
    who === "grandmother" ||
    who === "grandfather"
  ) {
    return 99;
  }
  return 12;
}

export function subjectCopy(lang: Lang, who: StudioWho, gender: StudioGender | null): Copy {
  if (who === "cousin" && gender === "f") return COUSIN_F[lang];
  return COPY[lang][who];
}
