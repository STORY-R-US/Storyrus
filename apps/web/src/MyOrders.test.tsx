import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MyOrders } from "./MyOrders";
import { api, setToken } from "./api";
import { state } from "./test/server";
import type { Project } from "./types";

// The mock server keeps a smaller project shape; the list returns whatever is stored.
const put = (project: Project) =>
  state.projects.set(project.id, project as unknown as Parameters<typeof state.projects.set>[1]);

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Meus pedidos", () => {
  it("retira a autorização sem apagar o projeto nem bloquear a consulta", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = true;
    const project = { id: "p1", status: "CREATED", style: "cgi_3d",
      story_text: "Título: Lila\n", ebook_url: null, video_url: null,
      created_at: "2026-01-01T00:00:00Z" };
    state.projects.set("p1", project);
    const revoke = vi.spyOn(api, "revokeBookMedia").mockResolvedValue({
      ...project, processing_revoked_at: "2026-10-29T12:00:00Z",
    });
    const remove = vi.spyOn(api, "deleteProject");
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<MemoryRouter><MyOrders /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Lila" });
    await userEvent.click(screen.getByTestId("order-revoke"));
    expect(await screen.findByRole("button", { name: "Novas gerações bloqueadas" })).toBeDisabled();
    expect(revoke).toHaveBeenCalledWith("p1");
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Lila" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Continuar/ })).toHaveAttribute("href", "/app?projeto=p1");
  });

  it("não retira a autorização sem confirmação", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = true;
    state.projects.set("p1", { id: "p1", status: "CREATED", style: "cgi_3d",
      story_text: "Título: Lila\n", ebook_url: null, video_url: null, created_at: "2026-01-01T00:00:00Z" });
    const revoke = vi.spyOn(api, "revokeBookMedia");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<MemoryRouter><MyOrders /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Lila" });
    await userEvent.click(screen.getByTestId("order-revoke"));
    expect(revoke).not.toHaveBeenCalled();
  });

  it("mostra a capa, o próximo passo e separa os livros concluídos", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = true;
    const base = { status: "EBOOK_READY", style: "realistic", story_text: null, ebook_url: null,
      video_url: null, book_size: "M" as const, cover_type: "hard" as const };
    put({ ...base, id: "story", child_name: "Joao", created_at: "2026-11-16T12:00:00Z",
      cover_thumb_url: "https://cdn.test/capa.png",
      book_profile: { version: 1, stage: "story_ready", title: "Joao Sonha com as Estrelas", gender: "m",
        languages: ["pt-BR"], current_page: 0 } });
    put({ ...base, id: "quote", child_name: "Lorena", created_at: "2026-11-17T12:00:00Z",
      purchase_flow: { title: "Lorena e o Jardim", preview_approved_at: "2026-11-17" } });
    put({ ...base, id: "done", child_name: "Rodrigo", created_at: "2026-11-03T12:00:00Z",
      book_approved_at: "2026-11-10", purchase_flow: { title: "Rodrigo no Mar", full_book_ready_at: "2026-11-09" } });
    render(<MemoryRouter><MyOrders /></MemoryRouter>);
    const story = await screen.findByRole("heading", { name: "Joao Sonha com as Estrelas" });
    const storyCard = story.closest("article")!;
    expect(storyCard).toHaveTextContent("Sua vez: aprovar a história");
    expect(storyCard.querySelector("img")).toHaveAttribute("src", "https://cdn.test/capa.png");
    expect(screen.getByRole("link", { name: /Ler a história/ })).toHaveAttribute("href", "/app?projeto=story");
    expect(screen.getByText("Pedido em cotação", { exact: true })).toBeInTheDocument();
    const finished = screen.getByRole("heading", { name: /Concluídos/ }).closest("section")!;
    expect(finished).toHaveTextContent("Rodrigo no Mar");
    expect(finished).toHaveTextContent("Aprovado para impressão");
    const active = screen.getByRole("heading", { name: /Em andamento/ }).closest("section")!;
    expect(active).not.toHaveTextContent("Rodrigo no Mar");
    // The family's turn comes before a quotation that is waiting for payment.
    const titles = [...active.querySelectorAll("h3")].map((node) => node.textContent);
    expect(titles).toEqual(["Joao Sonha com as Estrelas", "Lorena e o Jardim"]);
  });

  it("apaga o projeto quando o responsável confirma", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = true;
    state.projects.set("p1", {
      id: "p1",
      status: "CREATED",
      style: "cgi_3d",
      story_text: "Título: Lila\n",
      ebook_url: null,
      video_url: null,
      created_at: "2026-01-01T00:00:00Z",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <MemoryRouter>
        <MyOrders />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Lila" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByTestId("order-delete"));
    expect(await screen.findByText(/ainda não tem pedidos/i)).toBeInTheDocument();
    expect(state.projects.has("p1")).toBe(false);
  });
});
