import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ForgotPassword } from "./ForgotPassword";
import { ResetPassword } from "./ResetPassword";

describe("ForgotPassword", () => {
  it("manda o link antigo para o login do Clerk", async () => {
    render(
      <MemoryRouter initialEntries={["/esqueci-senha?next=%2Fapp"]}>
        <Routes>
          <Route path="/esqueci-senha" element={<ForgotPassword />} />
          <Route path="/entrar" element={<div data-testid="login-dest">login</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("login-dest")).toBeInTheDocument();
  });
});

describe("ResetPassword", () => {
  it("manda o link antigo para o login do Clerk", async () => {
    render(
      <MemoryRouter initialEntries={["/redefinir-senha?token=test-reset-token&next=%2Fapp"]}>
        <Routes>
          <Route path="/redefinir-senha" element={<ResetPassword />} />
          <Route path="/entrar" element={<div data-testid="login-dest">login</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("login-dest")).toBeInTheDocument();
  });
});
