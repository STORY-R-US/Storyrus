import definitions from "./catalogModels.json";
export type CatalogModel = {
  id: string; catalog_index: number; style: string; available: boolean;
  reason: string | null; titles: Record<"pt" | "en" | "es", string>;
  example_name: string; example_names?: Partial<Record<"pt" | "en" | "es", string>>;
  sources: { cover: string; page: string; holding: string };
};
const models = definitions as Record<string, CatalogModel>;
export function catalogModel(id: string | null | undefined): CatalogModel | undefined {
  return id ? models[id] : undefined;
}
export function catalogModelId(index: number, cartoon = false): string {
  return `catalog-${cartoon ? "cartoon" : "realistic"}-${index}`;
}
export function unavailableCatalogCopy(lang: "pt" | "en" | "es") {
  return {pt:"Personalização indisponível: aguardando referência do miolo.", en:"Personalization unavailable: interior reference pending.", es:"Personalización no disponible: falta la referencia del interior."}[lang];
}
