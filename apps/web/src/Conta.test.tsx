import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Conta } from "./Conta";
import { Auth } from "./Auth";
import { api, getToken, setToken } from "./api";
import { state } from "./test/server";

function renderConta(initial = "/conta") {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/conta" element={<Conta />} />
        <Route path="/cadastro" element={<Auth mode="signup" />} />
        <Route path="/entrar" element={<Auth mode="login" />} />
        <Route path="/app" element={<div data-testid="studio-dest">studio</div>} />
        <Route path="/esqueci-senha" element={<div data-testid="forgot-dest">forgot</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function asRegistered(email = "ana@email.com") {
  state.isGuest = false;
  state.emailVerified = true;
  state.email = email;
  state.fullName = "Ana Souza";
  state.phone = "11999999999";
  state.postalCode = "01310-100";
  state.street = "Av Paulista";
  state.number = "1000";
  state.complement = "Sala 1";
  state.district = "Bela Vista";
  state.city = "São Paulo";
  state.stateUf = "SP";
  state.country = "BR";
  state.credits = 10;
  setToken("test-token");
}

afterEach(() => {
  vi.restoreAllMocks();
  setToken(null);
  state.reset();
  try {
    localStorage.removeItem("lang");
  } catch {
    /* ignore */
  }
});

describe("Conta — perfil editável", () => {
  it("mantém a sessão após falha temporária e recupera o perfil sem novo login", async () => {
    asRegistered();
    vi.spyOn(api, "me").mockRejectedValueOnce(new Error("502: Bad Gateway"));
    const user = userEvent.setup();
    renderConta();
    expect(await screen.findByTestId("connection-error")).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
    await user.click(screen.getByRole("button", { name: /tentar novamente/i }));
    expect(await screen.findByTestId("conta-form")).toBeInTheDocument();
  });

  it("redireciona para cadastro sem sessão", async () => {
    setToken(null);
    renderConta();
    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
  });

  it("carrega dados e salva alterações via updateMe", async () => {
    asRegistered();
    const update = vi.spyOn(api, "updateMe");
    const user = userEvent.setup();
    renderConta();

    expect(await screen.findByTestId("conta-form")).toBeInTheDocument();
    expect(screen.getByTestId("conta-email")).toHaveValue("ana@email.com");
    expect(screen.getByTestId("conta-full-name")).toHaveValue("Ana Souza");
    expect(screen.getByTestId("conta-phone")).toHaveValue("11999999999");
    await waitFor(() => {
      expect(screen.getByTestId("conta-city")).toHaveValue("São Paulo");
    });

    await user.clear(screen.getByTestId("conta-full-name"));
    await user.type(screen.getByTestId("conta-full-name"), "Ana Silva");
    await user.clear(screen.getByTestId("conta-phone"));
    await user.type(screen.getByTestId("conta-phone"), "11988887777");
    await user.click(screen.getByTestId("conta-submit"));

    await waitFor(() => {
      expect(update).toHaveBeenCalled();
    });
    expect(update.mock.calls[0][0]).toMatchObject({
      full_name: "Ana Silva",
      phone: "11988887777",
      city: "São Paulo",
      country: "BR",
    });
    expect(await screen.findByTestId("conta-saved")).toHaveTextContent(/atualizados/i);
    expect(screen.getByTestId("conta-full-name")).toHaveValue("Ana Silva");
  });

  it("bloqueia guest e manda para cadastro", async () => {
    state.isGuest = true;
    state.emailVerified = true;
    setToken("guest-token");
    renderConta();
    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
  });

  it("volta ao estúdio a partir do perfil", async () => {
    asRegistered();
    renderConta();
    expect(await screen.findByTestId("conta-studio")).toHaveAttribute("href", "/app");
    expect(screen.queryByTestId("conta-change-password")).not.toBeInTheDocument();
  });
});
