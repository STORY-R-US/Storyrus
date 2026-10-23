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

const HOME_PHRASE = "Transformamos fotos em livros personalizados, histórias em memórias eternas.";

/** Título de SEO e de aba: a marca fica no começo. */
export function siteTitle(label: string): string {
  const stripped = label.replace(/\s*[—–-]\s*Story R Us\s*$/u, "").trim();
  if (/^Story R Us - /i.test(stripped)) return stripped;
  return `Story R Us - ${stripped}`;
}

export const NOT_FOUND_PAGE: HtmlPage = {
  path: "/404",
  title: siteTitle("Página Não Encontrada"),
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
    title: siteTitle(HOME_PHRASE),
    description: HOME_DESCRIPTION,
    sitemap: true,
  },
  {
    path: "/cartoon",
    title: siteTitle("Livros Cartoon"),
    description:
      "Livros ilustrados em desenho, com a foto do seu filho como herói. Veja os exemplos cartoon e crie o seu.",
    sitemap: true,
  },
  {
    path: "/catalogo",
    title: siteTitle("Nossos Livros"),
    description:
      "Catálogo de livros ilustrados personalizados. Escolha um tema e crie com a foto da criança.",
    sitemap: true,
  },
  {
    path: "/exemplos",
    title: siteTitle("Exemplos Da Plataforma"),
    description:
      "As fotos e vídeos de demonstração do site são materiais da Story R Us, separados do que você envia no estúdio.",
    sitemap: true,
  },
  {
    path: "/privacidade",
    title: siteTitle("Política De Privacidade"),
    description:
      "Quais dados a Story R Us trata, para quê, com quem compartilha e como pedir acesso ou exclusão.",
    sitemap: true,
  },
  {
    path: "/termos",
    title: siteTitle("Termos De Uso"),
    description:
      "Regras de uso da Story R Us para criar livros ilustrados personalizados e pedir a impressão.",
    sitemap: true,
  },
  {
    path: "/privacy",
    title: siteTitle("Privacy Policy"),
    description:
      "What Story R Us collects, why, who receives it, and how a parent can review or delete a project. Includes our COPPA notice.",
    canonicalPath: "/privacidade",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/terms",
    title: siteTitle("Terms Of Use"),
    description:
      "Rules for using Story R Us. Accounts are for adults 18 or older. Children under 13 may not create an account.",
    canonicalPath: "/termos",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/landing",
    title: siteTitle(HOME_PHRASE),
    description: HOME_DESCRIPTION,
    canonicalPath: "/",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/entrar",
    title: siteTitle("Entrar"),
    description: "Entre na sua conta para criar livros ilustrados personalizados.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/cadastro",
    title: siteTitle("Criar Conta"),
    description: "Crie sua conta Story R Us para transformar uma foto em um livro ilustrado.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/verificar-email",
    title: siteTitle("Confirmar E-mail"),
    description: "Confirme o e-mail da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/esqueci-senha",
    title: siteTitle("Esqueci A Senha"),
    description: "Peça um link para redefinir a senha da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/redefinir-senha",
    title: siteTitle("Redefinir Senha"),
    description: "Escolha uma nova senha para a sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/app",
    title: siteTitle("Estúdio"),
    description: "Estúdio para criar o livro ilustrado a partir da foto.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/conta",
    title: siteTitle("Meu Perfil"),
    description: "Atualize nome, telefone e endereço da sua conta Story R Us.",
    robots: "noindex, nofollow",
    sitemap: false,
  },
  {
    path: "/meus-pedidos",
    title: siteTitle("Meus Pedidos"),
    description: "Acompanhe a cotação, a produção e a entrega dos seus livros personalizados.",
    robots: "noindex, nofollow",
    sitemap: false,
    prerender: false,
  },
];

export function staticPageMeta(pathname: string): HtmlPage | null {
  const path = pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  return STATIC_PAGES.find((page) => page.path === path) ?? null;
}

export function categoryPageMeta(id: string, name: string): HtmlPage {
  return {
    path: `/catalogo/${id}`,
    title: siteTitle(name),
    description: categoryDescription(name),
    sitemap: true,
  };
}

export function bookPageMeta(book: CatalogBookSeo): HtmlPage {
  return {
    path: `/livro/${book.index}`,
    title: siteTitle(book.title),
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
  const branded = siteTitle(page.title);
  const title = escapeHtml(branded);
  const description = escapeHtml(page.description);
  const canonical = `${SITE_ORIGIN}${page.canonicalPath ?? page.path}`;
  let next = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${title}</title>`);
  next = upsertMetaTag(next, "name", "description", page.description);
  next = upsertMetaTag(next, "property", "og:title", branded);
  next = upsertMetaTag(next, "property", "og:description", page.description);
  next = upsertMetaTag(next, "property", "og:url", canonical);
  next = upsertMetaTag(next, "name", "twitter:title", branded);
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
    const branded = siteTitle(title);
    const previousTitle = document.title;
    document.title = branded;
    const restore: Array<() => void> = [
      upsertHeadMeta("name", "description", description),
      upsertHeadMeta("property", "og:title", branded),
      upsertHeadMeta("property", "og:description", description),
      upsertHeadMeta("property", "og:url", `${SITE_ORIGIN}${path}`),
      upsertHeadMeta("name", "twitter:title", branded),
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
