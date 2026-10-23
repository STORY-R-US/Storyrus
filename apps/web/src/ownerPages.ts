import { applyPageMeta, siteTitle } from "./pageMeta";

export type OwnerPage = {
  path: "/gastos" | "/pedidos" | "/usuarios";
  file: string;
  title: string;
  description: string;
};

export const OWNER_PAGES: readonly OwnerPage[] = [
  {
    path: "/gastos",
    file: "gastos.html",
    title: siteTitle("Gastos"),
    description: "Painel privado de custos da plataforma.",
  },
  {
    path: "/pedidos",
    file: "pedidos.html",
    title: siteTitle("Pedidos"),
    description: "Painel privado dos livros enviados com foto.",
  },
  {
    path: "/usuarios",
    file: "usuarios.html",
    title: siteTitle("Usuários"),
    description: "Painel privado das contas cadastradas.",
  },
];

export function applyOwnerPageMeta(html: string, page: OwnerPage): string {
  return applyPageMeta(html, {
    path: page.path,
    title: page.title,
    description: page.description,
    robots: "noindex, nofollow",
    sitemap: false,
    prerender: false,
  });
}
