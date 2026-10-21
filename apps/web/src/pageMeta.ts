import { useEffect } from "react";

export const SITE_ORIGIN = "https://storyrus.ai";

export type HtmlPage = {
  path: string;
  title: string;
  description: string;
  /** Default: indexável. */
  robots?: string;
  /** Default: o próprio path. */
  canonicalPath?: string;
  sitemap?: boolean;
  /** Fallback visível dentro de #root. Default true. */
  prerender?: boolean;
};

export type CatalogBookSeo = {
  index: number;
  title: string;
  description: string;
};

const HOME_DESCRIPTION =
  "Envie uma foto e a Story R Us cria um personagem ilustrado, um livro em PDF e um vídeo narrado com seu filho como herói.";

export const NOT_FOUND_PAGE: HtmlPage = {
  path: "/404",
  title: "Página Não Encontrada — Story R Us",
  description: "Esse endereço não existe. Volte à página inicial ou abra o estúdio.",
  robots: "noindex, nofollow",
  canonicalPath: "/404",
  sitemap: false,
  prerender: true,
};

export const CATALOG_CATEGORIES: readonly { id: string; name: string }[] = [
  { id: "aventuras", name: "Temáticas" },
  { id: "voce-e-eu", name: "Você e Eu" },
  { id: "ocasioes", name: "Ocasiões Especiais" },
  { id: "educativo", name: "Educativo" },
  { id: "sentimentos", name: "Sentimentos" },
];

function categoryDescription(name: string): string {
  return `Livros ilustrados de ${name}. Escolha um tema e a Story R Us cria uma história com a foto do seu filho.`;
}

export const STATIC_PAGES: readonly HtmlPage[] = [
  {
    path: "/",
    title: "Story R Us — Histórias Ilustradas Com A Foto Do Seu Filho",
    description: HOME_DESCRIPTION,
    sitemap: true,
  },
  {
    path: "/cartoon",
    title: "Livros Cartoon — Story R Us",
    description:
      "Livros ilustrados em desenho, com a foto do seu filho como herói. Veja os exemplos cartoon e crie o seu.",
    sitemap: true,
  },
  {
    path: "/catalogo",
    title: "Nossos Livros — Story R Us",
    description:
      "Catálogo de livros ilustrados personalizados. Escolha um tema e crie com a foto da criança.",
    sitemap: true,
  },
  {
    path: "/exemplos",
    title: "Exemplos Da Plataforma — Story R Us",
    description:
      "As fotos e vídeos de demonstração do site são materiais da Story R Us, separados do que você envia no estúdio.",
    sitemap: true,
  },
  {
    path: "/privacidade",
    title: "Política De Privacidade — Story R Us",
    description:
      "Quais dados a Story R Us trata, para quê, com quem compartilha e como pedir acesso ou exclusão.",
    sitemap: true,
  },
  {
    path: "/termos",
    title: "Termos De Uso — Story R Us",
    description:
      "Regras de uso da Story R Us para criar livros ilustrados personalizados e pedir a impressão.",
    sitemap: true,
  },
  {
    path: "/privacy",
    title: "Política De Privacidade — Story R Us",
    description:
      "Quais dados a Story R Us trata, para quê, com quem compartilha e como pedir acesso ou exclusão.",
    canonicalPath: "/privacidade",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/terms",
    title: "Termos De Uso — Story R Us",
    description:
      "Regras de uso da Story R Us para criar livros ilustrados personalizados e pedir a impressão.",
    canonicalPath: "/termos",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/landing",
    title: "Story R Us — Histórias Ilustradas Com A Foto Do Seu Filho",
    description: HOME_DESCRIPTION,
    canonicalPath: "/",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/entrar",
    title: "Entrar — Story R Us",
    description: "Entre na sua conta para criar livros ilustrados personalizados.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/cadastro",
    title: "Criar Conta — Story R Us",
    description: "Crie sua conta Story R Us para transformar uma foto em um livro ilustrado.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/verificar-email",
    title: "Confirmar E-mail — Story R Us",
    description: "Confirme o e-mail da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/esqueci-senha",
    title: "Esqueci A Senha — Story R Us",
    description: "Peça um link para redefinir a senha da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/redefinir-senha",
    title: "Redefinir Senha — Story R Us",
    description: "Escolha uma nova senha para a sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/app",
    title: "Estúdio — Story R Us",
    description: "Estúdio para criar o livro ilustrado a partir da foto.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/conta",
    title: "Meu Perfil — Story R Us",
    description: "Atualize nome, telefone e endereço da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
];

export function staticPageMeta(pathname: string): HtmlPage | null {
  const path = pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  return STATIC_PAGES.find((page) => page.path === path) ?? null;
}

export function categoryPageMeta(id: string, name: string): HtmlPage {
  return {
    path: `/catalogo/${id}`,
    title: `${name} — Story R Us`,
    description: categoryDescription(name),
    sitemap: true,
  };
}

export function bookPageMeta(book: CatalogBookSeo): HtmlPage {
  return {
    path: `/livro/${book.index}`,
    title: `${book.title} — Story R Us`,
    description: book.description,
    sitemap: true,
  };
}

export function publicHtmlPages(books: readonly CatalogBookSeo[]): HtmlPage[] {
  return [
    ...STATIC_PAGES,
    ...CATALOG_CATEGORIES.map((category) => categoryPageMeta(category.id, category.name)),
    ...books.map((book) => bookPageMeta(book)),
  ];
}

export function htmlFileForPath(path: string): string {
  if (path === "/") return "index.html";
  return `${path.replace(/^\//, "")}.html`;
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function upsertMetaTag(html: string, attr: "name" | "property", key: string, content: string): string {
  const escaped = escapeHtml(content);
  const re = new RegExp(`(<meta\\s+${attr}="${key}"\\s+content=")[^"]*("\\s*/?>)`, "i");
  if (re.test(html)) return html.replace(re, `$1${escaped}$2`);
  return html.replace(/<head>/i, `<head>\n    <meta ${attr}="${key}" content="${escaped}" />`);
}

function upsertCanonical(html: string, href: string): string {
  const escaped = escapeHtml(href);
  const re = /(rel="canonical"\s+href=")[^"]*(")/i;
  if (re.test(html)) return html.replace(re, `$1${escaped}$2`);
  return html.replace(/<head>/i, `<head>\n    <link rel="canonical" href="${escaped}" />`);
}

export function applyPageMeta(html: string, page: HtmlPage): string {
  const title = escapeHtml(page.title);
  const description = escapeHtml(page.description);
  const canonical = `${SITE_ORIGIN}${page.canonicalPath ?? page.path}`;
  let next = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${title}</title>`);
  next = upsertMetaTag(next, "name", "description", page.description);
  next = upsertMetaTag(next, "property", "og:title", page.title);
  next = upsertMetaTag(next, "property", "og:description", page.description);
  next = upsertMetaTag(next, "property", "og:url", canonical);
  next = upsertMetaTag(next, "name", "twitter:title", page.title);
  next = upsertMetaTag(next, "name", "twitter:description", page.description);
  next = upsertCanonical(next, canonical);
  if (page.robots) {
    next = upsertMetaTag(next, "name", "robots", page.robots);
  }
  if (page.prerender !== false && /<div id="root">\s*<\/div>/.test(next)) {
    next = next.replace(
      /<div id="root">\s*<\/div>/,
      `<div id="root"><main><h1>${title}</h1><p>${description}</p></main></div>`,
    );
  }
  return next;
}

export function renderSitemap(pages: readonly HtmlPage[]): string {
  const urls = pages
    .filter((page) => page.sitemap)
    .map((page) => `  <url>\n    <loc>${SITE_ORIGIN}${page.path}</loc>\n  </url>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
}

function rememberAttr(el: Element, name: string, value: string): () => void {
  const previous = el.getAttribute(name);
  el.setAttribute(name, value);
  return () => {
    if (previous == null) el.removeAttribute(name);
    else el.setAttribute(name, previous);
  };
}

function upsertHeadMeta(attr: "name" | "property", key: string, content: string): () => void {
  const selector = `meta[${attr}="${key}"]`;
  const existing = document.head.querySelector(selector);
  if (!existing) {
    const created = document.createElement("meta");
    created.setAttribute(attr, key);
    created.setAttribute("content", content);
    document.head.appendChild(created);
    return () => created.remove();
  }
  return rememberAttr(existing, "content", content);
}

/** Atualiza title, description, canonical e Open Graph da rota atual. */
export function usePageMeta(page: HtmlPage | null) {
  const title = page?.title ?? null;
  const description = page?.description ?? null;
  const path = page?.canonicalPath ?? page?.path ?? null;
  const robots = page?.robots ?? null;
  useEffect(() => {
    if (!title || !description || !path) return;
    const previousTitle = document.title;
    document.title = title;
    const restore: Array<() => void> = [
      upsertHeadMeta("name", "description", description),
      upsertHeadMeta("property", "og:title", title),
      upsertHeadMeta("property", "og:description", description),
      upsertHeadMeta("property", "og:url", `${SITE_ORIGIN}${path}`),
      upsertHeadMeta("name", "twitter:title", title),
      upsertHeadMeta("name", "twitter:description", description),
    ];
    const canonical = document.head.querySelector('link[rel="canonical"]');
    if (!canonical) {
      const created = document.createElement("link");
      created.setAttribute("rel", "canonical");
      created.setAttribute("href", `${SITE_ORIGIN}${path}`);
      document.head.appendChild(created);
      restore.push(() => created.remove());
    } else {
      restore.push(rememberAttr(canonical, "href", `${SITE_ORIGIN}${path}`));
    }
    if (robots) restore.push(upsertHeadMeta("name", "robots", robots));
    return () => {
      document.title = previousTitle;
      for (const undo of restore) undo();
    };
  }, [title, description, path, robots]);
}
