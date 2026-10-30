import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MyOrders } from "./MyOrders";
import { api, setToken } from "./api";
import { state } from "./test/server";

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
    render(<MemoryRouter><MyOrders /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Lila" });
    await userEvent.click(screen.getByTestId("order-revoke"));
    expect(await screen.findByRole("button", { name: "Novas gerações bloqueadas" })).toBeDisabled();
    expect(revoke).toHaveBeenCalledWith("p1");
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Lila" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Ver pedido/ })).toHaveAttribute("href", "/app?projeto=p1");
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
