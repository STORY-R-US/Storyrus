import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { App } from "./App";
import { Auth } from "./Auth";
import { getToken, readJwtPayload, setToken } from "./api";
import { state } from "./test/server";

afterEach(() => {
  vi.restoreAllMocks();
  setToken(null);
  state.reset();
});

function fakeJwt(exp: number): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: "u1", exp }));
  return `${header}.${payload}.sig`;
}

describe("readJwtPayload", () => {
  it("decodes exp from a JWT-shaped token", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = readJwtPayload(fakeJwt(exp));
    expect(payload?.exp).toBe(exp);
  });

  it("returns null for garbage", () => {
    expect(readJwtPayload("not-a-jwt")).toBeNull();
  });
});

describe("Studio account gate", () => {
  it("blocks guests and sends them to cadastro", async () => {
    state.isGuest = true;
    state.email = "guest-test@storyrus.app";
    setToken("test-token");

    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route path="/app" element={<App />} />
          <Route path="/cadastro" element={<Auth mode="signup" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
    expect(screen.queryByTestId("studio-upgrade-open")).not.toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("blocks unverified registered accounts", async () => {
    state.isGuest = false;
    state.emailVerified = false;
    state.email = "wait@example.com";
    setToken("test-token");

    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route path="/app" element={<App />} />
          <Route path="/cadastro" element={<Auth mode="signup" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("auth-page")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("shows logout for registered accounts", async () => {
    const user = userEvent.setup();
    state.isGuest = false;
    state.email = "parent@example.com";
    setToken("test-token");

    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route path="/app" element={<App />} />
          <Route path="/entrar" element={<Auth mode="login" />} />
        </Routes>
      </MemoryRouter>,
    );

    const logout = await screen.findByTestId("studio-logout");
    await user.click(logout);
    await waitFor(() => {
      expect(screen.getByTestId("auth-page")).toBeInTheDocument();
    });
  });
});
