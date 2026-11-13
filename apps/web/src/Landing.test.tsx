import { localizedExample } from "./localizedExamples";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Landing, occasionDue, catalogSections, catalogEntry } from "./Landing";
import { AppRoutes } from "./Root";
import { setToken } from "./api";
import { state } from "./test/server";

function renderLanding() {
  const result = render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>,
  );
  while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
  return result;
}

/** Personalizar aponta para /cadastro?next=… — decodifica o destino do estúdio. */
function studioTarget(href: string | null): string {
  if (!href) return "";
  try {
    const next = new URL(href, "https://storyrus.local").searchParams.get("next");
    if (next) return decodeURIComponent(next.replace(/\+/g, " "));
  } catch {
    /* ignore */
  }
  return decodeURIComponent(href.replace(/\+/g, " "));
}

beforeAll(() => {
  class IO {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal("IntersectionObserver", IO);

  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn().mockResolvedValue(undefined),
  });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", {
    configurable: true,
    value: vi.fn(),
  });
});

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.lang = "en";
});

afterEach(() => {
  vi.useRealTimers();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  setToken(null);
});

describe("Landing — idioma", () => {
  it("inicia em PT e troca copy/document.lang/localStorage ao clicar EN e ES", async () => {
    const user = userEvent.setup();
    renderLanding();

    expect(await screen.findByTestId("landing-hero-title")).toHaveTextContent(/transforme uma foto/i);
    expect(screen.getByRole("heading", { name: /perguntas frequentes/i })).toBeInTheDocument();

    await user.click(screen.getByTestId("landing-lang-en"));
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(/turn a photo/i);
    expect(screen.getByRole("heading", { name: /frequently asked questions/i })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem("lang")).toBe("en");
    expect(screen.getByTestId("landing-lang-en")).toHaveClass("on");
    expect(screen.getByTestId("landing-lang-pt")).not.toHaveClass("on");

    await user.click(screen.getByTestId("landing-lang-es"));
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(/convierte una foto/i);
    expect(screen.getByRole("heading", { name: /preguntas frecuentes/i })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("es");
    expect(localStorage.getItem("lang")).toBe("es");
    expect(screen.getByTestId("landing-lang-es")).toHaveClass("on");
  });

  it("restaura idioma salvo no localStorage", async () => {
    localStorage.setItem("lang", "en");
    renderLanding();

    expect(await screen.findByTestId("landing-hero-title")).toHaveTextContent(/turn a photo/i);
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByTestId("landing-lang-en")).toHaveClass("on");
  });
});

describe("Landing — tema", () => {
  it("alterna data-theme e persiste em localStorage", async () => {
    const user = userEvent.setup();
    renderLanding();

    await screen.findByTestId("landing-hero-title");
    const themeButtons = () => screen.getAllByRole("button", { name: /alternar tema/i });
    expect(themeButtons()[0]).toHaveTextContent(/claro/i);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");

    await user.click(themeButtons()[0]);
    expect(themeButtons()[0]).toHaveTextContent(/escuro/i);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(localStorage.getItem("theme")).toBe("light");

    await user.click(themeButtons()[0]);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("restaura tema claro do localStorage", async () => {
    localStorage.setItem("theme", "light");
    renderLanding();

    await screen.findByTestId("landing-hero-title");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});

describe("Landing — promessa", () => {
  it("destaca presente no título e usa a nova copy em PT", async () => {
    renderLanding();

    await screen.findByTestId("landing-hero-title");
    const heading = screen.getByRole("heading", { name: /um presente personalizado para eternizar momentos inesquecíveis/i });
    expect(within(heading).getByText(/^presente$/i)).toHaveClass("promise-mark");
    expect(
      screen.getByText(/da foto à prévia final, cada detalhe é criado com carinho, dando vida a um presente único para toda a vida\./i),
    ).toBeInTheDocument();
  });
});

describe("Landing — avaliações", () => {
  it("mostra a foto segurando o livro com só o nome da criança", async () => {
    renderLanding();

    const reviews = (await screen.findByRole("heading", { name: /o que as famílias dizem/i })).closest("section") as HTMLElement;
    const fotos = [
      "foto-martin-goleiro.jpg",
      "foto-nicolas-maefilho.jpg",
      "foto-emilia-bailarina.jpg",
      "foto-amordemae.jpg",
      "foto-antonio-bicicleta.jpg",
      "foto-mariajesus-hockey.jpg",
      "foto-amordebisavo.jpg",
      "foto-facundo-motocross.jpg",
      "foto-natalmemetata.jpg",
      "foto-ester.png",
      "foto-raquel-papai.png",
      "foto-rebeca.png",
      "foto-maya-cachorra-pt.jpg",
      "foto-mako-amigofiel.jpg",
      "foto-noe.png",
    ];
    fotos.forEach((file, i) => {
      expect(within(reviews).getByTestId(`landing-review-cover-${i}`)).toHaveAttribute("src", expect.stringContaining(file));
    });
    expect(within(reviews).getByTestId("landing-review-name-0")).toHaveTextContent(/^Martin$/);
    expect(within(reviews).getByTestId("landing-review-name-1")).toHaveTextContent(/^Nicolas$/);
    expect(within(reviews).getByTestId("landing-review-name-2")).toHaveTextContent(/^Emilia$/);
    expect(within(reviews).getByTestId("landing-review-name-10")).toHaveTextContent(/^Raquel$/);
    expect(within(reviews).getByTestId("landing-review-name-14")).toHaveTextContent(/^Noé$/);
    expect(within(reviews).queryByTestId("landing-review-cover-15")).not.toBeInTheDocument();
    expect(within(reviews).queryByTestId("landing-review-cover-16")).not.toBeInTheDocument();
    expect(within(reviews).queryByText(/^Abigail$/)).not.toBeInTheDocument();
    expect(within(reviews).queryByText(/^Miriam$/)).not.toBeInTheDocument();
    expect(within(reviews).queryByText(/^Nano$/)).not.toBeInTheDocument();
    expect(within(reviews).queryByText(/o Grande Goleiro do Chile/i)).not.toBeInTheDocument();
    const quotes = within(reviews).getAllByRole("blockquote");
    expect(quotes).toHaveLength(10);
    expect(within(reviews).getByText("Camila R.")).toBeInTheDocument();
    expect(within(reviews).getByText(/a vovó se viu no livro com a neta/i)).toBeInTheDocument();
    expect(within(reviews).getByText("Larissa M.")).toBeInTheDocument();
  });

  it("traduz os depoimentos novos ao trocar para EN e ES", async () => {
    const user = userEvent.setup();
    renderLanding();

    const reviews = (await screen.findByRole("heading", { name: /o que as famílias dizem/i })).closest("section") as HTMLElement;
    await user.click(screen.getByTestId("landing-lang-en"));
    expect(within(reviews).getByText(/grandma saw herself in the book/i)).toBeInTheDocument();
    expect(within(reviews).getByText("Helena V.")).toBeInTheDocument();
    expect(within(reviews).queryByText(/a vovó se viu no livro/i)).not.toBeInTheDocument();
    expect(within(reviews).getByTestId("landing-review-name-0")).toHaveTextContent(/^Martin$/);
    expect(within(reviews).getByTestId("landing-review-cover-0")).toHaveAttribute("src", expect.stringContaining("localized/foto-martin-goleiro-en.webp"));
    expect([...reviews.querySelectorAll("img")].some((img) => (img.getAttribute("src") ?? "").includes("foto-martin-goleiro"))).toBe(true);
    expect([...reviews.querySelectorAll("img")].some((img) => (img.getAttribute("src") ?? "").includes("foto-mamaepapaimatteo-en.jpg"))).toBe(false);

    await user.click(screen.getByTestId("landing-lang-es"));
    expect(within(reviews).getByText(/la abuela se vio en el libro/i)).toBeInTheDocument();
    expect(within(reviews).getByText(/hicimos el libro de los primos/i)).toBeInTheDocument();
  });
});

describe("Landing — catálogo", () => {
  it("usa as capas aprovadas com o formato padronizado", async () => {
    renderLanding();

    const catalog = (await screen.findByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const imgs = within(catalog).getAllByRole("img");
    const srcs = imgs.map((img) => img.getAttribute("src") ?? "");
    expect(srcs.some((src) => src.includes(localizedExample("capa-nicolas-maefilho.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-amordemae.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-mamaepapaimatteo.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-sofia-alfabeto.png", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-bruno-animais.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-gael-es.png", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-matteo-rancho-es.png", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-ester.png", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-martin-goleiro.jpg", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-natalmemetata.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-amordetia.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-davi-pastor.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-meupai-heroi.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-enzo-primo.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-lucas-max.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-esther-higiene.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-pedro-amem-se.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes("cartoon-capa-pedro-amem-se"))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-nicolas-maefilho.jpg", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-matteo-aniversario.png", "pt")))).toBe(false);
    expect(srcs.some((src) => src.includes(localizedExample("capa-matteo-nas-nuvens.png", "pt")))).toBe(true);
    expect(imgs).toHaveLength(53);
    expect(srcs.some((src) => src.includes("capa-maos-motores"))).toBe(false);
    expect(srcs.some((src) => src.includes("capa-nanoaventuras"))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-feliz-natal-familia.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-enzo-dinossauro.png", "pt")))).toBe(true);
    expect(srcs.some((src) => src.includes(localizedExample("capa-pai-e-filha.png", "pt")))).toBe(true);
  });

  it("mostra os livros realistas com a mesma capa, o valor e sem o resumo", async () => {
    renderLanding();

    const catalog = (await screen.findByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const cards = within(catalog).getAllByTestId("landing-catalog-card");
    expect(within(catalog).queryByText(/mãos que consertam motores/i)).not.toBeInTheDocument();
    expect(within(cards[0]).queryByText(/capa mole ou capa dura/i)).not.toBeInTheDocument();
    expect(within(cards[0]).getByText("Livro 16 Páginas")).toBeInTheDocument();
    expect(cards[0].querySelector(".cat-notes-sizes")).toContainElement(within(cards[0]).getByText("Livro 16 Páginas"));
    expect(cards[0].querySelector(".cat-badges")).not.toBeInTheDocument();
    const noteLabels = [...cards[0].querySelectorAll(".cat-notes button")].map((button) => button.textContent);
    expect(noteLabels).toEqual(["P", "M", "HARD", "SOFT"]);
    expect(cards[0].textContent).toContain("20 × 20 cm");
    expect(cards[0].textContent).toContain("15 × 15 cm");
    expect(cards[0].textContent).toContain("R$ 177,00");
    expect(cards[0].textContent).toContain("R$ 157,00");
    expect(within(cards[0]).getAllByRole("button", { name: "HARD" })).toHaveLength(1);
    expect(within(cards[0]).getByText(/resistente e durável/i)).toBeInTheDocument();
    expect(within(cards[0]).getAllByRole("button", { name: "SOFT" })).toHaveLength(1);
    expect(within(cards[0]).getByText(/leve e flexível/i)).toBeInTheDocument();
    expect(within(catalog).getAllByRole("button", { name: "HARD" })).toHaveLength(53);
    expect(cards).toHaveLength(53);
    expect(cards.some((card) => card.textContent?.includes("Livro Teste"))).toBe(false);
    expect(within(catalog).getByText(/nano e suas aventuras/i)).toBeInTheDocument();
    expect(within(catalog).getByText(/feliz natal, família/i)).toBeInTheDocument();
    expect(within(catalog).getByText(/segredos do dinossauro, enzo/i)).toBeInTheDocument();
    cards.forEach((card) => {
      expect(card).toHaveAttribute("data-format", "catalog");
      expect(within(card).queryByText(/esporte e coragem/i)).not.toBeInTheDocument();
      expect(within(card).queryByText(/amizade e cuidado/i)).not.toBeInTheDocument();
    });
    expect(within(cards[0]).getByText("Pequeno Construtor, Grande Empreendedor")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Meu Herói Favorito, O Bombeiro")).toBeInTheDocument();
    expect(within(cards[2]).getByText("Meu Herói Favorito, O Policial")).toBeInTheDocument();
    expect(within(cards[3]).getByText("Meu Pai, Meu Herói")).toBeInTheDocument();
    expect(within(cards[4]).getByText("Amor De Avô, Meu Porto Seguro")).toBeInTheDocument();
    expect(within(cards[5]).getByText("Enzo, Meu Primo Predileto")).toBeInTheDocument();
    expect(within(cards[6]).getByText("Davi, O Menino Pastor")).toBeInTheDocument();
    expect(within(cards[7]).getByText("Amem-se Sinceramente Uns Aos Outros")).toBeInTheDocument();
    expect(within(cards[8]).getByText(/Tomé Duvidou/i)).toBeInTheDocument();
    expect(within(cards[9]).getByText(/Martin, O Grande Goleiro/i)).toBeInTheDocument();
    expect(within(cards[10]).getByText(/Maria Jesus E A Disciplina No Hockey/i)).toBeInTheDocument();
    expect(within(cards[11]).getByText("Brilho Que Fascina, Alma De Bailarina")).toBeInTheDocument();
    expect(within(catalog).getByText("Meu Pai, Meu Herói")).toBeInTheDocument();
    expect(within(catalog).getByText("Davi, O Menino Pastor")).toBeInTheDocument();
    expect(within(catalog).getByText("Enzo, Meu Primo Predileto")).toBeInTheDocument();
    expect(within(catalog).getByText(/Martin, O Grande Goleiro/i)).toBeInTheDocument();
    expect(within(catalog).queryByText(/Aniversário Especial De Ester/i)).not.toBeInTheDocument();
    expect(within(catalog).getByText("Amor De Tia")).toBeInTheDocument();
    expect(within(catalog).getByText("Lucas E Seu Amigo Max")).toBeInTheDocument();
    expect(within(catalog).getByText("Pequeno Construtor, Grande Empreendedor")).toBeInTheDocument();
    expect(within(catalog).getByText("Meu Herói Favorito, O Bombeiro")).toBeInTheDocument();
    expect(within(catalog).getByText("Meu Herói Favorito, O Policial")).toBeInTheDocument();
    expect(within(catalog).getByText("Meu Herói Favorito, A Aranha")).toBeInTheDocument();
    expect(within(catalog).getByText("Tia Especial, Não Existe Igual")).toBeInTheDocument();
    expect(within(catalog).getByText("Amor De Avô, Meu Porto Seguro")).toBeInTheDocument();
    expect(within(catalog).getByRole("img", { name: /amor de avô, meu porto seguro/i })).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-amor-de-avo.png", "pt")));
    expect(within(catalog).getByText("Bruno Em Uma Aventura Animal")).toBeInTheDocument();
    expect(within(catalog).getByText("Aprendendo Economia Com O Gael")).toBeInTheDocument();
    expect(within(catalog).getByText("Maria Jesus E A Disciplina No Hockey Na Grama")).toBeInTheDocument();
    expect(within(catalog).getByText("Feliz Páscoa")).toBeInTheDocument();
    expect(within(catalog).queryByText("Nossa Família")).not.toBeInTheDocument();
    expect(within(catalog).queryByText("Minha Grande Aventura")).not.toBeInTheDocument();
    expect(within(catalog).getByText("Esther E Os Superpoderes Da Higiene")).toBeInTheDocument();
    expect(cards[0].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-construtor.png", "pt")));
    expect(cards[1].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-heroi-bombeiro.png", "pt")));
    expect(cards[2].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-heroi-policia.png", "pt")));
    expect(within(cards[0]).getByRole("button", { name: "HARD", pressed: true })).toBeInTheDocument();
    expect(within(cards[0]).getByRole("button", { name: "SOFT", pressed: false })).toBeInTheDocument();
    expect(within(cards[0]).getByRole("button", { name: "M", pressed: true })).toBeInTheDocument();
    expect(within(cards[0]).getByRole("button", { name: "P", pressed: false })).toBeInTheDocument();
    expect(cards[0].querySelector(".cat-book")).toHaveAttribute("data-size", "M");
    expect(within(cards[4]).getByRole("button", { name: "HARD", pressed: true })).toBeInTheDocument();
  });

  it("troca descrição e valor ao escolher capa e tamanho", async () => {
    const user = userEvent.setup();
    renderLanding();

    const catalog = (await screen.findByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const card = within(catalog).getAllByTestId("landing-catalog-card")[0];

    await user.click(within(card).getByRole("button", { name: "HARD" }));
    expect(within(card).getByRole("button", { name: "HARD", pressed: true })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "SOFT", pressed: false })).toBeInTheDocument();
    expect(card.textContent).toContain("20 × 20 cm");
    expect(card.textContent).toContain("15 × 15 cm");

    await user.click(within(card).getByRole("button", { name: "SOFT" }));
    expect(within(card).getByRole("button", { name: "SOFT", pressed: true })).toBeInTheDocument();
    expect(studioTarget(within(card).getByTestId("landing-personalize").getAttribute("href"))).toContain("capa=soft");

    expect(within(card).getByText("R$ 177,00.")).toHaveClass("is-price");
    expect(within(card).getByText("R$ 157,00.")).not.toHaveClass("is-price");

    await user.click(within(card).getByRole("button", { name: "P" }));
    expect(within(card).getByRole("button", { name: "P", pressed: true })).toBeInTheDocument();
    expect(card.querySelector(".cat-book")).toHaveAttribute("data-size", "P");
    expect(studioTarget(within(card).getByTestId("landing-personalize").getAttribute("href"))).toContain("tamanho=P");
    expect(within(card).getByRole("button", { name: "M", pressed: false })).toBeInTheDocument();
    expect(card.textContent).toContain("20 × 20 cm");
    expect(card.textContent).toContain("15 × 15 cm");
    expect(within(card).getByText("R$ 157,00.")).toHaveClass("is-price");
    expect(within(card).getByText("R$ 177,00.")).not.toHaveClass("is-price");
    await user.click(within(card).getByRole("button", { name: "M" }));
    expect(card.querySelector(".cat-book")).toHaveAttribute("data-size", "M");
  });

  it("troca a capa localizada de Amor de Mãe ao mudar o idioma", async () => {
    const user = userEvent.setup();
    renderLanding();

    const catalog = (await screen.findByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const ptSrcs = within(catalog).getAllByRole("img").map((img) => img.getAttribute("src") ?? "");
    expect(ptSrcs.some((src) => src.includes(localizedExample("capa-amordemae.png", "pt")))).toBe(true);
    expect(ptSrcs.some((src) => src.includes(localizedExample("capa-amordemae-en.png", "pt")))).toBe(false);

    await user.click(screen.getByTestId("landing-lang-en"));
    const enCatalog = (await screen.findByRole("heading", { name: /our books/i })).closest("section") as HTMLElement;
    const enSrcs = within(enCatalog).getAllByRole("img").map((img) => img.getAttribute("src") ?? "");
    expect(enSrcs.some((src) => src.includes(localizedExample("capa-amordemae.png", "en")))).toBe(true);
    expect(enSrcs.some((src) => src.includes(localizedExample("capa-ester-en.png", "pt")))).toBe(false);
    expect(enSrcs.some((src) => src.includes("capa-martin-goleiro"))).toBe(true);
    expect(enSrcs.some((src) => src.includes("capa-amor-vovo-motor"))).toBe(true);
    expect(enCatalog.textContent).toContain("Martin, The Great Goalkeeper");
    expect(enCatalog.textContent).toContain("Grandpa's Love, My Safe Harbor");
    expect(enCatalog.textContent).toContain("$33.91");
    expect(enCatalog.textContent).toContain("$30.08");
    expect(enCatalog.textContent?.replace(/R\$ 0,50/g, "")).not.toContain("R$");

    await user.click(screen.getByTestId("landing-lang-es"));
    const esCatalog = (await screen.findByRole("heading", { name: /nuestros libros/i })).closest("section") as HTMLElement;
    const esSrcs = within(esCatalog).getAllByRole("img").map((img) => img.getAttribute("src") ?? "");
    expect(esSrcs.some((src) => src.includes(localizedExample("capa-amordemae.png", "es")))).toBe(true);
    expect(esSrcs.some((src) => src.includes(localizedExample("capa-ester-es.png", "pt")))).toBe(false);
    expect(esSrcs.some((src) => src.includes("capa-martin-goleiro"))).toBe(true);
    expect(esSrcs.some((src) => src.includes("capa-amor-de-avo"))).toBe(true);
    expect(esCatalog.textContent).toContain("El Amor Del Abuelo, Mi Puerto Seguro");
    expect(esCatalog.textContent).toContain("Feliz Cumpleaños, Matteo");
    expect(within(esCatalog).getAllByRole("button", { name: "HARD" }).length).toBeGreaterThan(0);
    expect(within(esCatalog).getAllByText(/resistente y duradera/i).length).toBeGreaterThan(0);
    expect(esCatalog.textContent).toContain("20 × 20 cm");
    expect(esCatalog.textContent).toContain("30,10 €");
    expect(esCatalog.textContent).toContain("26,70 €");
    expect(esCatalog.textContent?.replace(/R\$ 0,50/g, "")).not.toContain("R$");
  });

  it("mostra somente a capa sem navegação no card do catálogo", async () => {
    const user = userEvent.setup();
    renderLanding();

    const catalog = (await screen.findByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const card = within(catalog).getByText("Meu Pai, Meu Herói").closest("[data-testid='landing-catalog-card']") as HTMLElement;
    const cover = within(card).getByRole("img");
    expect(cover).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "pt")));
    expect(within(catalog).queryByRole("button", { name: /imagem anterior|próxima imagem/i })).not.toBeInTheDocument();
    expect(within(catalog).queryByRole("tablist")).not.toBeInTheDocument();
    await user.hover(cover);
    expect(within(card).getAllByRole("img")).toHaveLength(1);
    expect(cover).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "pt")));
    within(card).getAllByRole("link", { name: "Meu Pai, Meu Herói" }).forEach((link) => {
      expect(link).toHaveAttribute("href", "/livro/21");
    });
  });

  it("aponta os livros realistas para os temas existentes", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    const personalize = screen.getAllByTestId("landing-personalize");
    expect(personalize).toHaveLength(52);
    expect(screen.getAllByTestId("catalog-model-unavailable")).toHaveLength(1);
    const first = studioTarget(personalize[0].getAttribute("href"));
    expect(first).toContain("tema=adventure");
    expect(first).toContain("campos=nome");
    expect(first).toContain("tamanho=M");
    expect(first).toContain("capa=hard");
    expect(first).toContain("modo=realista");
    expect(first).toContain("titulo=");
    expect(first).not.toContain("heroi=");
    expect(first).toContain("Construir e criar");
    expect(studioTarget(personalize[1].getAttribute("href"))).toContain("tema=superhero");
    expect(studioTarget(personalize[3].getAttribute("href"))).toContain("tema=fathers_day");
    const martin = personalize.find((link) => studioTarget(link.getAttribute("href")).includes("Martin, O Grande Goleiro"));
    expect(martin).toBeTruthy();
    expect(studioTarget(martin ? martin.getAttribute("href") : null)).toContain("tema=sport");
    const pai = personalize.find((link) => studioTarget(link.getAttribute("href")).includes("Meu Pai, Meu Herói"));
    expect(pai).toBeTruthy();
    expect(studioTarget(pai ? pai.getAttribute("href") : null)).toContain("tema=fathers_day");
  });
});

describe("Landing — FAQ", () => {
  it("abre e fecha item; só um fica expandido por vez", async () => {
    const user = userEvent.setup();
    renderLanding();

    const faqSection = (await screen.findByRole("heading", { name: /perguntas frequentes/i })).closest(
      "section",
    ) as HTMLElement;
    const questions = within(faqSection).getAllByRole("button");
    expect(questions.length).toBeGreaterThanOrEqual(2);

    expect(questions[0]).toHaveAttribute("aria-expanded", "false");
    await user.click(questions[0]);
    expect(questions[0]).toHaveAttribute("aria-expanded", "true");
    expect(questions[1]).toHaveAttribute("aria-expanded", "false");

    await user.click(questions[1]);
    expect(questions[0]).toHaveAttribute("aria-expanded", "false");
    expect(questions[1]).toHaveAttribute("aria-expanded", "true");

    await user.click(questions[1]);
    expect(questions[1]).toHaveAttribute("aria-expanded", "false");
  });
});

describe("Landing — menu mobile e abas do hero", () => {
  it("abre as categorias pelo menu desktop", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");
    const nav = document.querySelector(".kcats") as HTMLElement;
    expect(within(nav).getByRole("link", { name: /^temáticas$/i })).toHaveAttribute("href", "/catalogo#aventuras");
    expect(within(nav).getByRole("link", { name: /^educativo$/i })).toHaveAttribute("href", "/catalogo#educativo");
  });

  it("abre/fecha o menu e Escape fecha", async () => {
    const user = userEvent.setup();
    renderLanding();

    const menuBtn = await screen.findByTestId("landing-menu");
    const siteMenu = screen.getByTestId("landing-site-menu");
    expect(menuBtn).toHaveAttribute("aria-expanded", "false");
    expect(siteMenu).not.toHaveClass("open");

    await user.click(menuBtn);
    expect(menuBtn).toHaveAttribute("aria-expanded", "true");
    expect(siteMenu).toHaveClass("open");

    await user.keyboard("{Escape}");
    expect(menuBtn).toHaveAttribute("aria-expanded", "false");
    expect(siteMenu).not.toHaveClass("open");
  });

  it("organiza o menu mobile com categorias e acessos rapidos", async () => {
    const user = userEvent.setup();
    renderLanding();

    const menuBtn = await screen.findByTestId("landing-menu");
    const siteMenu = screen.getByTestId("landing-site-menu");

    await user.click(menuBtn);

    expect(siteMenu.querySelector(".kmobile-label")).toHaveTextContent(/^livros$/i);
    expect(within(siteMenu).getByText(/acessos r[aá]pidos/i)).toBeInTheDocument();

    const mobileCatButtons = within(siteMenu).getAllByRole("button");
    expect(mobileCatButtons.length).toBeGreaterThan(0);
    expect(mobileCatButtons[0]).toHaveAttribute("aria-expanded", "false");

    await user.click(mobileCatButtons[0]);
    expect(mobileCatButtons[0]).toHaveAttribute("aria-expanded", "true");
    expect(within(siteMenu).getByRole("link", { name: /ver todos/i })).toHaveAttribute("href", "/catalogo");
  });

  it("mostra no menu mobile as capas em destaque do menu desktop", async () => {
    const user = userEvent.setup();
    renderLanding();

    const siteMenu = screen.getByTestId("landing-site-menu");
    await user.click(await screen.findByTestId("landing-menu"));
    await user.click(within(siteMenu).getByRole("button", { name: /^temáticas$/i }));

    const feats = within(siteMenu).getByTestId("landing-mobile-feats-aventuras");
    const featLinks = within(feats).getAllByRole("link");
    expect(featLinks.length).toBeGreaterThan(0);
    featLinks.forEach((link) => {
      expect(link.getAttribute("href")).toMatch(/^\/livro\/\d+/);
    });

    await user.click(within(siteMenu).getByRole("button", { name: /^dinossauros$/i }));
    const noe = within(siteMenu).getByRole("link", { name: /noé/i });
    expect(noe).toHaveAttribute("href", "/livro/18");
    expect(noe.querySelector("img")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-noe.png", "pt")));

    await user.click(within(siteMenu).getByRole("button", { name: /^você e eu$/i }));
    await user.click(within(siteMenu).getByRole("button", { name: /^vovô e eu$/i }));
    const avo = within(siteMenu).getByRole("link", { name: /amor de avô/i });
    expect(avo).toHaveAttribute("href", "/livro/30");
    expect(avo.querySelector("img")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-amor-de-avo.png", "pt")));
  });

  it("abre o hero em Meu Pai e duplica a faixa", async () => {
    const user = userEvent.setup();
    renderLanding();

    const cover = await screen.findByTestId("landing-hero-slide-0");
    expect(cover).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "pt")));
    expect(screen.getByTestId("landing-hero-slide-1")).toHaveAttribute("src", expect.stringContaining("pagina-meupai-heroi.png"));
    expect(screen.getByTestId("landing-hero-slide-2")).toHaveAttribute("src", expect.stringContaining("foto-meupai-heroi.png"));
    expect(screen.getByTestId("landing-hero-slide-3")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-amordebisavo.jpg", "pt")));
    expect(screen.getByTestId("landing-hero-slide-4")).toHaveAttribute("src", expect.stringContaining("pagina-amordebisavo.jpg"));
    expect(screen.getByTestId("landing-hero-slide-5")).toHaveAttribute("src", expect.stringContaining("foto-amordebisavo.jpg"));
    expect(screen.getAllByRole("button", { name: "Nano E Suas Aventuras" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Pai e Filha: Uma Dupla que Brilha" }).length).toBeGreaterThan(0);

    const track = cover.closest(".hero-carousel-track") as HTMLElement;
    expect(track.querySelector(".hero-slide, .hero-slide-frame")).toBeNull();
    const shot = (n: number) => screen.getByTestId(`landing-hero-slide-${n}`).parentElement;
    const series0 = shot(0)?.parentElement?.parentElement as HTMLElement;
    const series1 = shot(3)?.parentElement?.parentElement as HTMLElement;
    expect(series0).toBeTruthy();
    expect(series1).toBeTruthy();
    expect(shot(0)?.nextElementSibling).toBe(shot(1));
    expect(shot(1)?.nextElementSibling).toBe(shot(2));
    expect(series0).toHaveClass("hero-series");
    expect(series1).toHaveClass("hero-series");

    const carousel = cover.closest(".hero-carousel") as HTMLElement;
    const natalCovers = [...carousel.querySelectorAll("img")].filter((img) => {
      const src = img.getAttribute("src") ?? "";
      return src.includes(localizedExample("capa-natalmemetata.png", "pt")) && !src.includes("capa-natalmemetata-e");
    });
    expect(natalCovers).toHaveLength(2);
    const heroSrcs = [...carousel.querySelectorAll("img")].map((img) => img.getAttribute("src") ?? "");
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-matteo-trator.jpg", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-nonna-90-anos.png", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-maria-fundo-do-mar.png", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-nanoaventuras.png", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-feliz-natal-familia.png", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-enzo-dinossauro.png", "pt")))).toBe(true);
    expect(heroSrcs.some((src) => src.includes(localizedExample("capa-pai-e-filha.png", "pt")))).toBe(true);
    expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "pt")));
    expect(screen.getByTestId("landing-hero-flip-dot-0")).toHaveAttribute("aria-selected", "true");
    await user.click(screen.getByRole("button", { name: /próxima página/i }));
    await waitFor(() => {
      expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining("pagina-meupai-heroi.png"));
    }, { timeout: 2200 });
    expect(screen.getByTestId("landing-hero-flip-dot-1")).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByTestId("landing-hero-flip-dot-2"));
    await waitFor(() => {
      expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining("foto-meupai-heroi.png"));
    }, { timeout: 2200 });

    await user.click(screen.getByRole("button", { name: /próxima página/i }));
    await waitFor(() => {
      expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-amordebisavo.jpg", "pt")));
    }, { timeout: 2200 });
    expect(screen.getByTestId("landing-hero-flip-dot-0")).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByTestId("landing-hero-pick-1"));
    expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining("pagina-meupai-heroi.png"));

    await user.click(screen.getByTestId("landing-lang-es"));
    const heroImgs = [...carousel.querySelectorAll("img")].map((img) => img.getAttribute("src") ?? "");
    expect(heroImgs).toHaveLength(108); // same 18 book trios, with the carousel loop copy
    expect(heroImgs.some((src) => src.includes(localizedExample("capa-meupai-heroi.png", "es")))).toBe(true);
    expect(heroImgs.some((src) => src.includes(localizedExample("capa-lucas-max.png", "es")))).toBe(true);
    expect(heroImgs.some((src) => src.includes(localizedExample("capa-esther-higiene.png", "es")))).toBe(true);
    expect(screen.getByTestId("landing-hero-slide-0")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "es")));

    expect(carousel).toHaveAttribute("aria-label", expect.stringMatching(/carrusel de libros/i));
    expect(screen.queryByText(/^carrusel de libros$/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("landing-hero-slide-1")).toHaveAttribute("src", expect.stringContaining("pagina-meupai-heroi-es"));
    expect(screen.getByTestId("landing-hero-slide-2")).toHaveAttribute("src", expect.stringContaining("foto-meupai-heroi-es"));
    expect(screen.getByTestId("landing-hero-flip")).toHaveAttribute("src", expect.stringContaining(localizedExample("capa-meupai-heroi.png", "es")));
    const videos = document.getElementById("videos") as HTMLElement;
    expect(within(videos).getByRole("heading", { name: /mi papá, mi héroe/i })).toBeInTheDocument();
    const passo = document.getElementById("passo") as HTMLElement;
    expect([...passo.querySelectorAll("img")].some((img) => img.getAttribute("src")?.endsWith(localizedExample("pagina-mamaepapaimatteo.jpg", "es")))).toBe(true);
  }, 15000);

  it("coloca o texto Uma foto abaixo do titulo Transforme", async () => {
    renderLanding();

    const heading = await screen.findByRole("heading", { level: 1 });
    const intro = heading.closest(".khero-intro") as HTMLElement;
    expect(intro).toBeTruthy();
    expect(intro.firstElementChild).toBe(heading);
    expect(intro).toHaveTextContent(/uma foto\. uma história\. uma memória eterna/i);
    expect(heading.nextElementSibling).toHaveTextContent(/uma foto/i);
  });
});

describe("Landing — CTAs e links", () => {
  it("CTAs principais apontam para cadastro e login", async () => {
    renderLanding();

    await screen.findByTestId("landing-hero-title");
    expect(screen.queryByTestId("landing-hero-cta")).not.toBeInTheDocument();
    expect(screen.getByTestId("landing-header-auth")).toBeInTheDocument();
    expect(screen.getByTestId("landing-header-cta")).toHaveAttribute("href", "/cadastro");
    expect(screen.getByTestId("landing-header-cta")).toHaveClass("kbtn", "kbtn-primary");
    expect(screen.getByTestId("landing-header-login")).toHaveAttribute("href", "/entrar");
    expect(screen.getByTestId("landing-header-login")).toHaveClass("kbtn", "kbtn-login");
    expect(screen.getByTestId("landing-mobile-cta")).toHaveAttribute("href", "/cadastro");
    expect(screen.getByTestId("landing-mobile-login")).toHaveAttribute("href", "/entrar");
    expect(screen.getByTestId("landing-mobile-auth")).toBeInTheDocument();
  });

  it("footer liga privacidade e termos", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    expect(screen.getByRole("link", { name: /^privacidade$/i })).toHaveAttribute("href", "/privacidade");
    expect(screen.getByRole("link", { name: /^termos$/i })).toHaveAttribute("href", "/termos");
  });

  it("botão Personalizar leva tema no query", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    const personalize = screen.getAllByTestId("landing-personalize");
    expect(personalize.length).toBeGreaterThan(0);
    for (const link of personalize) {
      const href = link.getAttribute("href") ?? "";
      expect(href.startsWith("/cadastro?next=")).toBe(true);
      expect(decodeURIComponent(href)).toContain("/app?tema=");
    }
  });

  it("com sessão, Personalizar e CTAs abrem o estúdio", async () => {
    state.isGuest = false;
    state.emailVerified = true;
    state.email = "ana@email.com";
    state.fullName = "Ana Souza";
    setToken("test-token");
    const user = userEvent.setup();
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    expect(screen.queryByTestId("landing-hero-cta")).not.toBeInTheDocument();
    expect(screen.getByTestId("landing-header-user")).toHaveTextContent("Ana");
    expect(screen.getByTestId("landing-header-cta")).toHaveAttribute("href", "/app");
    expect(screen.getByTestId("landing-header-cta")).toHaveTextContent(/criar meu livro/i);
    expect(screen.queryByTestId("landing-header-login")).not.toBeInTheDocument();
    expect(screen.queryByTestId("landing-header-account-menu")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("landing-header-user"));
    expect(await screen.findByTestId("landing-header-account-menu")).toBeInTheDocument();
    expect(screen.getByTestId("landing-header-account")).toHaveAttribute("href", "/conta");
    expect(screen.getByTestId("landing-header-orders")).toHaveAttribute("href", "/pedidos");
    expect(screen.getByTestId("landing-header-orders")).toHaveTextContent(/meus pedidos/i);
    expect(screen.getByTestId("landing-header-logout")).toBeInTheDocument();
    expect(screen.queryByTestId("landing-header-users")).not.toBeInTheDocument();
    const personalize = screen.getAllByTestId("landing-personalize");
    expect(personalize[0].getAttribute("href") ?? "").toMatch(/^\/app\?/);
  });

  it("com sessão admin, menu do usuário mostra Meus pedidos e Usuários", async () => {
    state.isGuest = false;
    state.emailVerified = true;
    state.isOwner = true;
    state.email = "dono@storyrus.ai";
    state.fullName = "André Admin";
    setToken("test-token");
    const user = userEvent.setup();
    renderLanding();

    expect(await screen.findByTestId("landing-header-user")).toHaveTextContent("André");
    expect(screen.getByTestId("landing-header-cta")).toHaveAttribute("href", "/app");
    await user.click(screen.getByTestId("landing-header-user"));
    expect(await screen.findByTestId("landing-header-orders")).toHaveAttribute("href", "/pedidos");
    expect(screen.getByTestId("landing-header-orders")).toHaveTextContent(/meus pedidos/i);
    expect(screen.getByTestId("landing-header-users")).toHaveAttribute("href", "/usuarios");
  });

  it("com sessão, Sair limpa o header e volta a mostrar Entrar", async () => {
    state.isGuest = false;
    state.emailVerified = true;
    state.email = "ana@email.com";
    state.fullName = "Ana Souza";
    setToken("test-token");
    const user = userEvent.setup();
    renderLanding();

    expect(await screen.findByTestId("landing-header-user")).toHaveTextContent("Ana");
    await user.click(screen.getByTestId("landing-header-user"));
    await user.click(await screen.findByTestId("landing-header-logout"));
    expect(await screen.findByTestId("landing-header-login")).toHaveAttribute("href", "/entrar");
    expect(screen.queryByTestId("landing-header-account")).not.toBeInTheDocument();
    expect(screen.getByTestId("landing-header-cta")).toHaveAttribute("href", "/cadastro");
  });

  it("mostra Meu Pai na seção de vídeos", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    const videos = document.getElementById("videos") as HTMLElement;
    expect(videos).toBeTruthy();
    const card = within(videos).getByRole("heading", { name: /^meu pai, meu herói$/i }).closest("figure");
    expect(card).toBeTruthy();
    expect(within(card as HTMLElement).getByText(/cada página ganha movimento/i)).toBeInTheDocument();
    const poster = (card as HTMLElement).querySelector("video");
    expect(poster).toHaveAttribute("poster", expect.stringContaining("capa-meupai-heroi"));
    expect(within(videos).queryByRole("heading", { name: /lia/i })).not.toBeInTheDocument();
    expect(within(videos).getAllByRole("heading", { level: 3 })).toHaveLength(3);
  });

  it("ordena as seções e aponta o Instagram para storyr.us", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");

    const order = ["como", "passo", "catalogo", "promessa", "videos", "reviews", "faq"];
    const nodes = order.map((id) => document.getElementById(id));
    expect(nodes.every(Boolean)).toBe(true);
    for (let i = 0; i < nodes.length - 1; i++) {
      expect(nodes[i]!.compareDocumentPosition(nodes[i + 1]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }

    expect(screen.getByRole("link", { name: /@storyr\.us/i })).toHaveAttribute("href", "https://www.instagram.com/storyr.us/");
    expect(within(document.querySelector(".kcats") as HTMLElement).getByRole("link", { name: /^livros cartoon$/i })).toHaveAttribute("href", "/cartoon");
    expect(screen.getAllByText(/fotos nítidas relacionadas à história/i)).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: /^a criança$/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/dicas para a foto perfeita/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Preencha os Dados" })).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: /^dados do livro$/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /acompanhe a criação/i })).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: /envie a foto e defina os detalhes/i })).not.toBeInTheDocument();
    const como = document.getElementById("como") as HTMLElement;
    const firstHow = como.querySelector(".howex-card") as HTMLElement;
    expect(firstHow.querySelector(".howex-lead")?.textContent).toBe("Preencha os Dados");
    expect(firstHow.querySelector("figcaption")?.textContent).toMatch(/fotos nítidas relacionadas à história/i);
    for (const file of ["como-envia.jpg", "como-cria.jpg", "como-recebe.jpg"]) {
      expect(como.querySelector(`img[alt][src*="${file}"]`)).toBeTruthy();
    }
    const passo = document.getElementById("passo") as HTMLElement;
    expect(within(passo).getByRole("heading", { name: "Passo a Passo" })).toBeInTheDocument();
    expect(within(passo).getByRole("heading", { name: "Envie a Foto do Protagonista" })).toBeInTheDocument();
    expect(within(passo).getByRole("heading", { name: "Envie Fotos dos Outros Personagens" })).toBeInTheDocument();
    expect(within(passo).getByRole("heading", { name: "Revise e Aprove" })).toBeInTheDocument();
    expect(passo.querySelector(".howex-card figcaption")?.textContent).toMatch(/herói da história/i);
    for (const file of ["passo-protagonista-v2.webp", "passo-familia-v2.webp", "pagina-mamaepapaimatteo.jpg"]) {
      expect(passo.querySelector(`img[alt][src*="${file}"]`)).toBeTruthy();
    }
  });

  it("mostra todos os livros do tema e liga cada capa à ficha correta", async () => {
    renderLanding();
    await screen.findByTestId("landing-hero-title");
    const panel = document.querySelector("#cat-panel") as HTMLElement;
    const feats = screen.getByTestId("landing-cat-feats");
    const hover = (name: RegExp) => fireEvent.mouseEnter(within(panel).getByRole("link", { name }));
    const bookLinks = () => [...feats.querySelectorAll(".kcat-feat")].map((link) => link.getAttribute("href"));

    const dinosaurs = within(panel).getByRole("link", { name: /^dinossauros$/i });
    expect(dinosaurs).toHaveAttribute("href", "/catalogo#aventuras-dinosaurs");
    hover(/^dinossauros$/i);
    expect(bookLinks().sort()).toEqual(["/livro/18", "/livro/60"]);
    expect(within(feats).getByRole("link", { name: /ver todos/i })).toHaveAttribute("href", "/catalogo#aventuras-dinosaurs");
    hover(/^aventura$/i);
    expect(bookLinks()).toContain("/livro/57");
    hover(/^esportes$/i);
    expect(bookLinks()).toEqual(expect.arrayContaining(["/livro/0", "/livro/1", "/livro/36", "/livro/53"]));
    hover(/^princesas$/i);
    expect(bookLinks()).toContain("/livro/62");
    hover(/^vovó e eu$/i);
    expect(bookLinks()).toContain("/livro/56");
    hover(/^irmãos e primos$/i);
    expect(bookLinks()).toEqual(["/livro/22"]);
    hover(/^tios e tias$/i);
    expect(bookLinks()).toHaveLength(4);
    hover(/^família$/i);
    expect(bookLinks().length).toBeGreaterThan(4);
    expect(bookLinks()).toContain("/livro/61");
    expect(within(panel).getByRole("link", { name: /^casamento$/i })).toHaveAttribute("href", "/catalogo#voce-e-eu-casamento");
    expect(within(panel).getByRole("link", { name: /hora de dormir/i })).toHaveAttribute("href", "/catalogo#educativo-rotina_dormir");
    hover(/hora de dormir/i);
    expect(bookLinks()).toContain("/livro/65");
  });

  for (const variant of ["photo", "cartoon"] as const) {
    it(`mantém todos os livros acessíveis no menu ${variant} nos três idiomas`, () => {
      render(<MemoryRouter><Landing variant={variant} /></MemoryRouter>);
      for (const lang of ["pt", "en", "es"] as const) {
        fireEvent.click(screen.getByTestId(`landing-lang-${lang}`));
        const links = [...document.querySelectorAll("#cat-panel .kcat-subs a")];
        const books = new Set<string>();
        for (const link of links) {
          fireEvent.mouseEnter(link);
          const shown = [...screen.getByTestId("landing-cat-feats").querySelectorAll(".kcat-feat")];
          expect(shown.length, `${lang}: ${link.textContent}`).toBeGreaterThan(0);
          shown.forEach((book) => books.add(book.getAttribute("href")!));
        }
        expect(books.size).toBe(variant === "photo" ? 58 : 37);
        if (variant === "photo") expect(books.has("/livro/31")).toBe(true);
        else expect([...books].every((href) => href.endsWith("?modo=cartoon"))).toBe(true);
      }
    });
  }

  it("mostra só a data que ainda cai neste ano", () => {
    const oct2 = new Date(2026, 9, 2);
    expect(occasionDue({ month: 10, day: 4 }, oct2)).toBe(true);
    expect(occasionDue({ month: 10, day: 12 }, oct2)).toBe(true);
    expect(occasionDue({ month: 10, day: 1 }, oct2)).toBe(false);
    expect(occasionDue({ month: 12, day: 25 }, oct2)).toBe(true);
    expect(occasionDue({ month: 5, day: 10 }, oct2)).toBe(false);
    expect(occasionDue({ month: 7, day: 26 }, oct2)).toBe(false);
    expect(occasionDue({ month: 8, day: 9 }, oct2)).toBe(false);
    expect(occasionDue({ month: 3, day: 8 }, oct2)).toBe(false);
    expect(occasionDue({ month: 12, day: 25 }, new Date(2026, 10, 25))).toBe(true);
    expect(occasionDue({ month: 1, day: 1 }, new Date(2026, 10, 1))).toBe(false);
    expect(occasionDue("easter", oct2)).toBe(false);
    expect(occasionDue("easter", new Date(2027, 1, 6))).toBe(true);
  });

  it("rota /cartoon repete a landing e troca as fotos por desenho", async () => {
    render(
      <MemoryRouter initialEntries={["/cartoon"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("landing-hero-title")).toBeInTheDocument();
    const cartoonNav = document.querySelector(".kcats") as HTMLElement;
    expect(within(cartoonNav).getByRole("link", { name: /^realista$/i })).toHaveAttribute("href", "/");
    expect(within(cartoonNav).queryByRole("link", { name: /^livros cartoon$/i })).not.toBeInTheDocument();
    expect(within(document.querySelector(".kmobile") as HTMLElement).getByRole("link", { name: /^realista$/i })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("heading", { name: /^educativo$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^sentimentos$/i })).not.toBeInTheDocument();
    const cartoonGroups = [...document.querySelectorAll("#cat-panel .kcat-group-name")].map((el) => el.textContent ?? "");
    expect(cartoonGroups).toEqual(["Temáticas", "Você e Eu", "Ocasiões Especiais", "Educativo"]);
    const cartoonPanel = document.querySelector("#cat-panel") as HTMLElement;
    const cartoonVovo = within(cartoonPanel).getByRole("link", { name: /^vovô e eu$/i });
    expect(cartoonVovo).toHaveAttribute("href", "/catalogo?modo=cartoon#voce-e-eu-grandfather_love");
    fireEvent.mouseEnter(cartoonVovo);
    const cartoonAvo = within(screen.getByTestId("landing-cat-feats")).getByRole("link", { name: /amor de avô/i });
    expect(cartoonAvo).toHaveAttribute("href", "/livro/30?modo=cartoon");
    expect(cartoonAvo.querySelector("img")).toHaveAttribute("src", expect.stringContaining(localizedExample("cartoon-capa-avo.png", "pt")));
    const cartoonEducativo = document.querySelectorAll("#cat-panel .kcat-group")[3] as HTMLElement;
    expect(within(cartoonEducativo).getByRole("link", { name: /^sentimentos$/i })).toHaveAttribute("href", "/catalogo?modo=cartoon#educativo-literacia_emocional");
    expect(within(cartoonEducativo).getByRole("link", { name: /hora de dormir/i })).toHaveAttribute("href", "/catalogo?modo=cartoon#educativo-rotina_dormir");
    expect(within(cartoonPanel).getByRole("link", { name: /^dinossauros$/i })).toHaveAttribute("href", "/catalogo?modo=cartoon#aventuras-dinosaurs");
    expect(screen.queryByRole("heading", { name: /dicas para a foto perfeita/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/você envia a foto/i)).not.toBeInTheDocument();
    const cartoonComo = document.getElementById("como") as HTMLElement;
    expect(within(cartoonComo).getByRole("heading", { name: "Preencha os Dados" })).toBeInTheDocument();
    expect(within(cartoonComo).queryByRole("heading", { name: /envie a foto e defina os detalhes/i })).not.toBeInTheDocument();
    expect(cartoonComo.querySelector(".howex-card figcaption")?.textContent).toMatch(/fotos nítidas relacionadas à história/i);
    for (const file of ["cartoon-como-dados.jpg", "cartoon-pagina-bisavo.jpg", "cartoon-capa-bisavo.jpg"]) {
      expect(cartoonComo.querySelector(`img[src*="${localizedExample(file, "pt")}"]`)).toBeTruthy();
    }
    const cartoonPasso = document.getElementById("passo") as HTMLElement;
    expect(within(cartoonPasso).getByRole("heading", { name: "Passo a Passo" })).toBeInTheDocument();
    expect(cartoonPasso.querySelector(".howex-card figcaption")?.textContent).toMatch(/herói da história/i);
    for (const file of ["passo-protagonista-v2.webp", "passo-familia-v2.webp", "cartoon-pagina-matteo.jpg"]) {
      expect(cartoonPasso.querySelector(`img[src*="${file}"]`)).toBeTruthy();
    }

    const catalog = (screen.getByRole("heading", { name: /nossos livros/i })).closest("section") as HTMLElement;
    const cards = within(catalog).getAllByTestId("landing-catalog-card");
    while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
    expect(screen.getAllByTestId("landing-catalog-card")).toHaveLength(37);
    expect(within(catalog).getByRole("img", { name: /amem-se sinceramente uns aos outros/i })).toHaveAttribute("src", expect.stringContaining(localizedExample("cartoon-capa-pedro-amem-se.png", "pt")));
    expect(within(catalog).getByText("Meu Pai, Meu Herói")).toBeInTheDocument();
    expect(within(catalog).getByText("Mako, Meu Amigo Fiel")).toBeInTheDocument();
    expect(within(catalog).getByText("Amor De Tia")).toBeInTheDocument();
    expect(within(catalog).getByText("Lucas E Seu Amigo Max")).toBeInTheDocument();
    expect(within(catalog).getByText("Amor De Avô, Meu Porto Seguro")).toBeInTheDocument();
    expect(within(catalog).getByText("Esther E Os Superpoderes Da Higiene")).toBeInTheDocument();
    expect(within(catalog).getByText("Nano E Suas Aventuras")).toBeInTheDocument();
    expect(within(catalog).getByText(/meme e o tata/i)).toBeInTheDocument();
    expect(within(cards[0]).getByText("Pequeno Construtor, Grande Empreendedor")).toBeInTheDocument();
    expect(within(catalog).getByText("Minha Grande Aventura")).toBeInTheDocument();
    expect(within(catalog).queryByText("Feliz Páscoa")).not.toBeInTheDocument();
    expect(within(catalog).queryByText("Nossa Família")).not.toBeInTheDocument();
    expect(cards[0].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("covers/cartoon-capa-construtor-v1-pt.webp", "pt")));
    expect(within(cards[1]).getByText("Meu Herói Favorito, O Bombeiro")).toBeInTheDocument();
    expect(cards[1].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("covers/cartoon-capa-heroi-bombeiro-v1-pt.webp", "pt")));
    expect(within(cards[2]).getByText("Meu Herói Favorito, O Policial")).toBeInTheDocument();
    expect(cards[2].querySelector(".cat-book img")).toHaveAttribute("src", expect.stringContaining(localizedExample("covers/cartoon-capa-heroi-policia-v1-pt.webp", "pt")));
    expect(within(catalog).getByText("Enzo, Meu Primo Predileto")).toBeInTheDocument();
    expect(within(catalog).getByText("Nicolas, Meu Primeiro Amor")).toBeInTheDocument();
    expect(within(catalog).getByRole("img", { name: /nicolas, meu primeiro amor/i })).toHaveAttribute("src", expect.stringContaining(localizedExample("cartoon-capa-nicolas.jpg", "pt")));
    expect(within(catalog).queryByText(/floresta encantada/i)).not.toBeInTheDocument();

    expect(screen.getByTestId("landing-hero-slide-0")).toHaveAttribute("src", expect.stringContaining(localizedExample("cartoon-capa-bisavo.jpg", "pt")));
    expect(screen.queryByRole("button", { name: "Meu Pai, Meu Herói" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nano" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Meme e Tata" })).not.toBeInTheDocument();
    const cartoonReviews = [
      "cartoon-foto-nicolas.jpg",
      "cartoon-foto-davi.jpg",
      "cartoon-foto-maya.jpg",
      "cartoon-foto-enzo.jpg",
      "cartoon-foto-amordemae.jpg",
      "cartoon-foto-natal.jpg",
      "cartoon-foto-matteo.jpg",
      "cartoon-foto-bisavo.jpg",
    ];
    cartoonReviews.forEach((file, i) => {
      expect(screen.getByTestId(`landing-review-cover-${i}`)).toHaveAttribute("src", expect.stringContaining(file));
    });
    expect(screen.queryByTestId("landing-review-cover-8")).not.toBeInTheDocument();
    expect(within(document.getElementById("como") as HTMLElement).getAllByRole("heading", { name: "Preencha os Dados" })).toHaveLength(1);
    expect(within(document.getElementById("passo") as HTMLElement).getByRole("heading", { name: "Envie a Foto do Protagonista" })).toBeInTheDocument();
  });
});

describe("Catálogo e página do livro", () => {
  it("abre o catálogo completo agrupado e a página do livro", async () => {
    render(
      <MemoryRouter initialEntries={["/catalogo"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /nossos livros/i }, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /imagem anterior|próxima imagem/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByTestId("site-back-nav")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /como funciona/i })).toHaveAttribute("href", "/#como");
    expect(screen.getByRole("link", { name: /^vídeos$/i })).toHaveAttribute("href", "/#videos");
    expect(screen.getByRole("link", { name: /avaliações/i })).toHaveAttribute("href", "/#reviews");
    expect(screen.getByRole("link", { name: /livros cartoon/i })).toHaveAttribute("href", "/cartoon");
    expect(screen.getByRole("link", { name: /^livros$/i })).toHaveAttribute("href", "/catalogo");
    expect(screen.getByRole("link", { name: /entrar/i })).toHaveAttribute("href", "/entrar");
    expect(screen.getByRole("link", { name: /criar conta/i })).toHaveAttribute("href", "/cadastro");
    expect(screen.getAllByTestId("landing-catalog-card")).toHaveLength(12);
    fireEvent.change(screen.getByTestId("catalog-category"), { target: { value: "educativo" } });
    expect(screen.getByRole("heading", { name: /^educativo$/i })).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("catalog-search"), { target: { value: "Davi" } });
    expect(screen.getAllByTestId("landing-catalog-card")).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: /davi, o menino pastor/i })[0]).toHaveAttribute("href", "/livro/20");
    fireEvent.change(screen.getByTestId("catalog-search"), { target: { value: "" } });
    fireEvent.change(screen.getByTestId("catalog-category"), { target: { value: "" } });
    while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
    const links = [...document.querySelectorAll(".cat-book-link")].map((a) => a.getAttribute("href"));
    expect(new Set(links).size).toBe(links.length);
    expect(links).not.toContain("/livro/58");
    expect(links).toContain("/livro/53");
  });

  it("abre a categoria ocasiões especiais com os livros das datas", async () => {
    render(
      <MemoryRouter initialEntries={["/catalogo/ocasioes"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /ocasiões especiais/i }, { timeout: 15000 })).toBeInTheDocument();
    while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
    expect(screen.queryByRole("button", { name: /imagem anterior|próxima imagem/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /natal com a meme e o tata/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: /nicolas, meu primeiro amor/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: /raquel e papai/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: /amor de bisavó/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: /^feliz aniversário, matteo$/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /feliz aniversário, matteo!/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /feliz aniversário, grace/i })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /feliz 90 anos, nonna/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: /o aniversário especial de ester/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /nano e suas aventuras/i })).not.toBeInTheDocument();
  });

  it("mostra a descrição completa na página do livro", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/livro/20"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /davi, o menino pastor/i }, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /resumo da história/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /detalhes do livro/i })).toBeInTheDocument();
    expect(screen.getByTestId("book-story")).toHaveTextContent(/harpa e as ovelhas/i);
    expect(screen.getByText(/livro 16 páginas/i)).toBeInTheDocument();
    expect(studioTarget(screen.getByTestId("landing-personalize").getAttribute("href"))).toContain("tema=biblico");
    expect(screen.getByTestId("site-back-nav")).toBeInTheDocument();
    expect(screen.getByTestId("site-back-home")).toHaveAttribute("href", "/");
    expect(screen.getByTestId("site-back-prev")).toBeInTheDocument();
    const series = screen.getByTestId("book-series");
    expect(series).toBeInTheDocument();
    expect(screen.getByTestId("book-series-cover")).toBeInTheDocument();
    expect(within(series).getAllByRole("img")).toHaveLength(1);
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("capa-davi-pastor"));
    expect(within(series).getByText(/^capa$/i)).toBeInTheDocument();

    const next = within(series).getByRole("button", { name: /próxima imagem/i });
    const prev = within(series).getByRole("button", { name: /imagem anterior/i });
    expect(within(series).getAllByRole("tab")).toHaveLength(3);
    await user.click(next);
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("pagina-davi-pastor"));
    expect(within(series).getByText(/^página$/i)).toBeInTheDocument();
    await user.click(next);
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("foto-davi-pastor"));
    expect(within(series).getByText(/^foto$/i)).toBeInTheDocument();
    await user.unhover(series);
    expect(within(series).getByRole("tab", { name: /^foto$/i })).toHaveAttribute("aria-selected", "true");
    await user.click(next);
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("capa-davi-pastor"));
    await user.click(prev);
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("foto-davi-pastor"));
    await user.click(within(series).getByRole("tab", { name: /^capa$/i }));
    expect(within(series).getByRole("img")).toHaveAttribute("src", expect.stringContaining("capa-davi-pastor"));
  });

  it("abre o catálogo completo da categoria", async () => {
    render(
      <MemoryRouter initialEntries={["/catalogo/aventuras"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /^temáticas$/i }, { timeout: 15000 })).toBeInTheDocument();
    while (screen.queryByTestId("catalog-more")) fireEvent.click(screen.getByTestId("catalog-more"));
    expect(screen.getByRole("heading", { name: /nano e suas aventuras/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /segredos do dinossauro, enzo/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /emilia e os primeiros passos da bailarina/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /meu pai, meu herói/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId("site-back-nav")).not.toBeInTheDocument();
  });

  it("abre o catálogo completo com hash da categoria", async () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    render(
      <MemoryRouter initialEntries={["/catalogo#educativo"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /nossos livros/i }, { timeout: 15000 })).toBeInTheDocument();
    expect(document.getElementById("educativo")).toBeTruthy();
    expect(screen.queryByTestId("site-back-nav")).not.toBeInTheDocument();
    scrollTo.mockRestore();
  });

  it("responde 404 para um livro inexistente", async () => {
    render(
      <MemoryRouter initialEntries={["/livro/99"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("not-found-title")).toBeInTheDocument();
  });
});


describe("Classificação editorial do catálogo", () => {
  for (const lang of ["pt", "en", "es"] as const) {
    it(`mantém livros acessíveis e relações em ${lang}`, () => {
      const sections = catalogSections(lang);
      const shelf = (section: string, sub: string) => sections.find((s) => s.id === section)?.subs.find((s) => s.id === sub)?.books.map((b) => b.catalogI) ?? [];
      expect(shelf("aventuras", "sport")).toEqual(expect.arrayContaining([1, 53]));
      expect(shelf("aventuras", "princess")).not.toContain(53);
      expect(shelf("aventuras", "princess")).toContain(62);
      expect(shelf("educativo", "cores")).toContain(63);
      expect(shelf("educativo", "compartilhar_revezar")).toContain(64);
      expect(shelf("educativo", "rotina_dormir")).toContain(65);
      expect(shelf("educativo", "literacia_emocional")).toContain(66);
      expect(shelf("voce-e-eu", "casamento")).toContain(67);
      expect(shelf("voce-e-eu", "tio_tia")).toEqual(expect.arrayContaining([19, 29, 39, 40].filter((index) => catalogEntry(lang, index))));
      expect(shelf("voce-e-eu", "family_love")).toContain(9);
      expect(shelf("voce-e-eu", "pets")).toEqual(expect.arrayContaining([10, 28]));
      expect(shelf("aventuras", "superhero")).not.toContain(28);
      expect(shelf("aventuras", "dinosaurs")).toContain(60);
      expect(shelf("voce-e-eu", "fathers_day")).toContain(61);
      expect(shelf("ocasioes", "christmas")).toEqual(expect.arrayContaining([9, 59]));
      expect(shelf("ocasioes", "birthday")).toEqual(expect.arrayContaining([41, 51, 55]));
      expect(shelf("ocasioes", "birthday")).not.toContain(50);
      expect(shelf("ocasioes", "birthday")).not.toContain(13);
      if (catalogEntry(lang, 3)) expect(shelf("educativo", "alfabetizacao_inicial")).toContain(3);
      const all = new Set(sections.flatMap((s) => s.books.map((b) => b.catalogI)));
      for (let index = 0; index <= 67; index++) {
        if (catalogEntry(lang, index) && index !== 33) expect(all.has(index), `livro ${index}`).toBe(true);
      }
      for (const section of sections) {
        expect(new Set(section.books.map((b) => b.catalogI)).size).toBe(section.books.length);
      }
    });
  }
});
