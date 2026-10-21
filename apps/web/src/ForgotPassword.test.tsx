import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ForgotPassword } from "./ForgotPassword";
import { ResetPassword } from "./ResetPassword";
import { getToken, setToken } from "./api";
import { state } from "./test/server";

afterEach(() => {
  setToken(null);
  state.reset();
});

describe("ForgotPassword", () => {
  it("envia e-mail e mostra confirmação genérica", async () => {
    const user = userEvent.setup();
    state.isGuest = false;
    state.email = "user@example.com";

    render(
      <MemoryRouter initialEntries={["/esqueci-senha?next=%2Fapp"]}>
        <Routes>
          <Route path="/esqueci-senha" element={<ForgotPassword />} />
          <Route path="/entrar" element={<div data-testid="login-dest">login</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByTestId("forgot-password-email"), "user@example.com");
    await user.click(screen.getByTestId("forgot-password-submit"));

    expect(await screen.findByTestId("forgot-password-sent")).toBeInTheDocument();
    expect(state.pendingResetToken).toBe("test-reset-token");
  });
});

describe("ResetPassword", () => {
  it("redefine senha e entra no estúdio", async () => {
    const user = userEvent.setup();
    state.isGuest = false;
    state.email = "user@example.com";
    state.pendingResetToken = "test-reset-token";

    render(
      <MemoryRouter
        initialEntries={[
          `/redefinir-senha?token=test-reset-token&next=${encodeURIComponent("/app")}`,
        ]}
      >
        <Routes>
          <Route path="/redefinir-senha" element={<ResetPassword />} />
          <Route path="/app" element={<div data-testid="studio-dest">studio</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByTestId("reset-password-password"), "nova12345");
    await user.type(screen.getByTestId("reset-password-confirm"), "nova12345");
    await user.click(screen.getByTestId("reset-password-submit"));

    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
    expect(state.pendingResetToken).toBeNull();
  });

  it("mostra erro sem token", () => {
    render(
      <MemoryRouter initialEntries={["/redefinir-senha"]}>
        <Routes>
          <Route path="/redefinir-senha" element={<ResetPassword />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("reset-password-error")).toHaveTextContent(/link inválido/i);
  });
});
