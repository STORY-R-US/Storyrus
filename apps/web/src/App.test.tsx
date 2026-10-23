import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { App } from "./App";
import { Auth } from "./Auth";
import { api, getToken, setToken } from "./api";
import { state } from "./test/server";

function renderApp(initial = "/app") {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/app" element={<App />} />
        <Route path="/cadastro" element={<Auth mode="signup" />} />
        <Route path="/entrar" element={<Auth mode="login" />} />
      </Routes>
    </MemoryRouter>,
  );
}

function asRegistered(email = "ana@email.com") {
  state.isGuest = false;
  state.email = email;
  state.credits = 10;
  setToken("test-token");
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
  setToken(null);
  state.reset();
});

describe("Fluxo E2E (com conta)", () => {
  it("mantém a sessão após falha temporária e abre o estúdio ao tentar novamente", async () => {
    asRegistered();
    vi.spyOn(api, "me").mockRejectedValueOnce(new Error("504: Servidor indisponível"));
    const user = userEvent.setup();
    renderApp();
    expect(await screen.findByTestId("connection-error")).toHaveTextContent(/sessão foi mantida/i);
    expect(getToken()).toBe("test-token");
    expect(screen.queryByTestId("auth-page")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /tentar novamente/i }));
    expect(await screen.findByLabelText(/nome do protagonista/i)).toBeInTheDocument();
  });

  it("limpa uma sessão rejeitada pela API", async () => {
    asRegistered();
    vi.spyOn(api, "me").mockRejectedValueOnce(new Error("401: Sessão inválida"));
    renderApp();
    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("redireciona para cadastro sem sessão", async () => {
    setToken(null);
    renderApp("/app");
    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/criar conta/i);
  });

  it("criar livro mostra tela Projeto criado com prévia automática", async () => {
    asRegistered();
    const user = userEvent.setup();
    const { container } = renderApp();

    expect(await screen.findByLabelText(/nome do protagonista/i)).toBeInTheDocument();
    expect(screen.queryByTestId("studio-client")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/nome do protagonista/i), "Lila");
    await user.type(screen.getByLabelText(/^idade$/i), "5");
    await user.type(screen.getByLabelText(/título do livro/i), "Lila e as estrelas");
    await user.type(screen.getByLabelText(/insira o tema desejado/i), "Aventura no espaço");
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["x"], "foto.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);
    await user.click(screen.getByRole("button", { name: /^feminino$/i }));
    await user.click(screen.getByRole("checkbox", { name: /responsável legal/i }));
    await user.click(screen.getByRole("button", { name: /gerar o livro/i }));

    const sent = await screen.findByTestId("studio-order-sent");
    expect(sent).toHaveTextContent(/projeto criado/i);
    expect(screen.getByTestId("studio-preview-building")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.title).toBe("Story R Us - Projeto criado");
    });
    expect(screen.queryByTestId("studio-generate-preview")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /gerar história com ia/i })).not.toBeInTheDocument();
  }, 15000);

  it("abre exemplo pronto sem criar projeto", async () => {
    const create = vi.spyOn(api, "createProject");
    window.history.pushState({}, "", "/app?exemplo=dinosaurs");
    renderApp("/app?exemplo=dinosaurs");

    expect(await screen.findByText(/você está vendo um exemplo pronto/i)).toBeInTheDocument();
    expect(await screen.findByTestId("studio-order-sent")).toHaveTextContent(/prévia pronta/i);
    await waitFor(() => {
      expect(document.title).toBe("Story R Us - Prévia pronta");
    });
    expect(await screen.findByTestId("studio-story-result")).toBeInTheDocument();
    expect(screen.getByTestId("studio-review-changes")).toBeInTheDocument();
    expect(screen.getByTestId("studio-preview-trio")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/matteo e o vale dos dinossauros/i)).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });
});
