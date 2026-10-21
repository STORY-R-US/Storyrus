import type { Theme, ThemeGroup } from "./types";

/** Catálogo espelhado do web (`studio/constants.ts`) — labels PT para o app. */
export const THEMES: { id: Theme; emoji: string; group: ThemeGroup; label: string }[] = [
  { id: "adventure", emoji: "🗺️", group: "aventura", label: "Aventura" },
  { id: "princess", emoji: "👑", group: "aventura", label: "Princesas" },
  { id: "superhero", emoji: "🦸", group: "aventura", label: "Super-heróis" },
  { id: "space", emoji: "🚀", group: "aventura", label: "Espaço" },
  { id: "underwater", emoji: "🐠", group: "aventura", label: "Fundo do Mar" },
  { id: "dinosaurs", emoji: "🦕", group: "aventura", label: "Dinossauros" },
  { id: "fantasy", emoji: "🧚", group: "aventura", label: "Fantasia" },
  { id: "birthday", emoji: "🎂", group: "datas", label: "Aniversário" },
  { id: "christmas", emoji: "🎄", group: "datas", label: "Natal" },
  { id: "easter", emoji: "🐣", group: "datas", label: "Páscoa" },
  { id: "childrens_day", emoji: "🎈", group: "datas", label: "Dia das Crianças" },
  { id: "mothers_day", emoji: "💐", group: "datas", label: "Dia das Mães" },
  { id: "fathers_day", emoji: "👔", group: "datas", label: "Dia dos Pais" },
  { id: "new_year", emoji: "🎉", group: "datas", label: "Ano Novo" },
  { id: "alfabetizacao_inicial", emoji: "🔤", group: "educativo", label: "Alfabetização" },
  { id: "pensamento_matematico", emoji: "🔢", group: "educativo", label: "Matemática" },
  { id: "cores", emoji: "🎨", group: "educativo", label: "Cores" },
  { id: "opostos_espacial", emoji: "↕️", group: "educativo", label: "Opostos" },
  { id: "higiene_desfralde", emoji: "🧼", group: "educativo", label: "Higiene" },
  { id: "rotina_dormir", emoji: "🌙", group: "educativo", label: "Hora de Dormir" },
  { id: "alimentacao_saudavel", emoji: "🥗", group: "educativo", label: "Alimentação" },
  { id: "vestir_autonomia", emoji: "👕", group: "educativo", label: "Vestir-se" },
  { id: "literacia_emocional", emoji: "💗", group: "educativo", label: "Sentimentos" },
  { id: "consciencia_corporal", emoji: "🙆", group: "educativo", label: "Corpo" },
  { id: "compartilhar_revezar", emoji: "🤝", group: "educativo", label: "Compartilhar" },
  { id: "animais_sons", emoji: "🐾", group: "educativo", label: "Animais e Sons" },
  { id: "transporte_ajudantes", emoji: "🚚", group: "educativo", label: "Transporte" },
  { id: "clima_estacoes", emoji: "⛅", group: "educativo", label: "Clima e Estações" },
];

export const THEME_GROUP_LABEL: Record<ThemeGroup, string> = {
  aventura: "Aventura e Fantasia",
  datas: "Datas Comemorativas",
  educativo: "Temas Educativos",
};

export function themeLabel(id: string | null | undefined): string {
  if (!id) return "—";
  return THEMES.find((t) => t.id === id)?.label ?? id;
}
