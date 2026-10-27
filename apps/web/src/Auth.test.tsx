import { afterEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppRoutes } from "./Root";
import { Auth, accountGateHref, readAuthQueryToken, safeNextPath, studioEntryHref } from "./Auth";
import { VerifyEmail } from "./VerifyEmail";
import { getToken, setAuthFetchTimeoutMsForTests, setToken } from "./api";
import { state } from "./test/server";

afterEach(() => {
  setToken(null);
  setAuthFetchTimeoutMsForTests(15_000);
  state.reset();
  try {
    localStorage.removeItem("lang");
  } catch {
    /* ignore */
  }
});

function renderAuth(mode: "login" | "signup", next?: string) {
  const path = mode === "login" ? "/entrar" : "/cadastro";
  const entry = next == null ? path : `${path}?next=${encodeURIComponent(next)}`;
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/entrar" element={<Auth mode="login" />} />
        <Route path="/cadastro" element={<Auth mode="signup" />} />
        <Route path="/verificar-email" element={<VerifyEmail />} />
        <Route path="/app" element={<div data-testid="studio-dest">studio</div>} />
        <Route path="/" element={<div data-testid="home-dest">home</div>} />
        <Route path="/termos" element={<div>termos</div>} />
        <Route path="/privacidade" element={<div>privacidade</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function asIncompleteProfile() {
  setToken("test-token");
  state.isGuest = false;
  state.emailVerified = true;
  state.fullName = "";
  state.phone = "";
  state.street = "";
  state.city = "";
  state.termsAcceptedAt = null;
  state.adultConfirmedAt = null;
}

async function fillProfile(user: ReturnType<typeof userEvent.setup>) {
  expect(await screen.findByTestId("auth-full-name")).toBeInTheDocument();
  await user.type(screen.getByTestId("auth-full-name"), "Ana Souza");
  await user.type(screen.getByTestId("auth-phone"), "11999999999");
  await user.selectOptions(screen.getByTestId("auth-country"), "BR");
  await user.type(screen.getByTestId("auth-postal-code"), "01310100");
  await waitFor(() => {
    expect(screen.getByTestId("auth-street")).toHaveValue("Avenida Paulista");
    expect(screen.getByTestId("auth-district")).toHaveValue("Bela Vista");
    expect(screen.getByTestId("auth-city")).toHaveValue("São Paulo");
    expect(screen.getByTestId("auth-state")).toHaveValue("SP");
  });
  await user.type(screen.getByTestId("auth-number"), "1000");
  await user.type(screen.getByTestId("auth-complement"), "Sala 1");
  await user.click(screen.getByTestId("auth-confirm-adult"));
  await user.click(screen.getByTestId("auth-accept-terms"));
}

describe("safeNextPath / accountGateHref", () => {
  it("bloqueia open redirects", () => {
    expect(safeNextPath("https://evil.com")).toBe("/");
    expect(safeNextPath("//evil.com")).toBe("/");
    expect(safeNextPath(null)).toBe("/");
    expect(safeNextPath("/app?tema=pets")).toBe("/app?tema=pets");
    expect(accountGateHref("/app?tema=pets")).toBe(
      `/cadastro?next=${encodeURIComponent("/app?tema=pets")}`,
    );
  });

  it("studioEntryHref vai direto ao estúdio quando há sessão", () => {
    expect(studioEntryHref("/app?tema=pets")).toBe(
      `/cadastro?next=${encodeURIComponent("/app?tema=pets")}`,
    );
    setToken("test-token");
    expect(studioEntryHref("/app?tema=pets")).toBe("/app?tema=pets");
  });

  it("readAuthQueryToken junta token quebrado e decodifica", () => {
    expect(readAuthQueryToken("?token=abc.def.ghi")).toBe("abc.def.ghi");
    expect(readAuthQueryToken("?token=abc%0Adef")).toBe("abcdef");
    expect(readAuthQueryToken("?token=abc.def&email=a%40b.com")).toBe("abc.def");
    expect(readAuthQueryToken("?token=" + encodeURIComponent("abc.def.ghi"))).toBe("abc.def.ghi");
  });
});

describe("Auth", () => {
  it("mostra o cadastro do Clerk sem sessão", async () => {
    renderAuth("signup", "/app?tema=space");
    expect(await screen.findByTestId("clerk-sign-up")).toBeInTheDocument();
    expect(screen.getByTestId("auth-clerk-hint")).toHaveTextContent(/google ou o código/i);
    expect(screen.queryByTestId("auth-form")).not.toBeInTheDocument();
  });

  it("mostra o login do Clerk sem sessão", async () => {
    renderAuth("login", "/app");
    expect(await screen.findByTestId("clerk-sign-in")).toBeInTheDocument();
    expect(screen.getByTestId("auth-clerk-hint")).toHaveTextContent(/sessão fica salva/i);
  });

  it("mantém o login do Clerk no retorno do Google", async () => {
    render(
      <MemoryRouter initialEntries={["/entrar/sso-callback"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("clerk-sign-in")).toBeInTheDocument();
    expect(screen.queryByTestId("not-found-title")).not.toBeInTheDocument();
  });

  it("grava o endereço e segue quando o perfil está incompleto", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app?tema=space");
    await fillProfile(user);
    await user.click(screen.getByTestId("auth-submit"));
    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
    expect(state.fullName).toBe("Ana Souza");
    expect(state.termsAcceptedAt).toBeTruthy();
    expect(state.adultConfirmedAt).toBeTruthy();
  });

  it("não segue sem a declaração de 18 anos", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    await fillProfile(user);
    await user.click(screen.getByTestId("auth-confirm-adult"));
    await user.click(screen.getByTestId("auth-submit"));
    expect(await screen.findByTestId("auth-error")).toHaveTextContent(/18/);
    expect(screen.queryByTestId("studio-dest")).not.toBeInTheDocument();
  });

  it("aceita endereço internacional (US)", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();

    await user.type(screen.getByTestId("auth-full-name"), "Jane Doe");
    await user.type(screen.getByTestId("auth-phone"), "+15551234567");
    await user.selectOptions(screen.getByTestId("auth-country"), "US");
    expect(screen.getByTestId("auth-postal-code")).toHaveAttribute("minLength", "5");
    expect(screen.queryByTestId("auth-district")).not.toBeInTheDocument();
    expect(screen.queryByTestId("auth-complement")).not.toBeInTheDocument();
    await user.type(screen.getByTestId("auth-postal-code"), "90210");
    await user.type(screen.getByTestId("auth-street"), "Rodeo Dr");
    await user.type(screen.getByTestId("auth-number"), "100");
    await user.type(screen.getByTestId("auth-city"), "Beverly Hills");
    await user.selectOptions(screen.getByTestId("auth-state"), "CA");
    await user.click(screen.getByTestId("auth-confirm-adult"));
    await user.click(screen.getByTestId("auth-accept-terms"));
    await user.click(screen.getByTestId("auth-submit"));

    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
    expect(state.country).toBe("US");
    expect(state.postalCode).toBe("90210");
    expect(state.stateUf).toBe("CA");
  });

  it("preenche endereço automaticamente a partir do CEP", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    await user.type(screen.getByTestId("auth-postal-code"), "01310100");
    expect(screen.getByTestId("auth-postal-code")).toHaveValue("01310-100");
    expect(await screen.findByTestId("auth-cep-status")).toHaveTextContent(/endereço preenchido/i);
    expect(screen.getByTestId("auth-street")).toHaveValue("Avenida Paulista");
    expect(screen.getByTestId("auth-district")).toHaveValue("Bela Vista");
    expect(screen.getByTestId("auth-city")).toHaveValue("São Paulo");
    expect(screen.getByTestId("auth-state")).toHaveValue("SP");
  });

  it("avisa quando o CEP não existe", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    await user.type(screen.getByTestId("auth-postal-code"), "00000000");
    expect(await screen.findByTestId("auth-cep-status")).toHaveTextContent(/não encontrado/i);
    expect(screen.getByTestId("auth-street")).toHaveValue("");
  });

  it("preenche cidade e estado automaticamente a partir do ZIP americano", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    await user.selectOptions(screen.getByTestId("auth-country"), "US");
    await user.type(screen.getByTestId("auth-postal-code"), "90210");
    expect(screen.getByTestId("auth-postal-code")).toHaveValue("90210");
    expect(await screen.findByTestId("auth-cep-status")).toHaveTextContent(/endereço preenchido|address filled/i);
    expect(screen.getByTestId("auth-city")).toHaveValue("Beverly Hills");
    expect(screen.getByTestId("auth-state")).toHaveValue("CA");
  });

  it("não busca CEP quando o país é México", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    await user.selectOptions(screen.getByTestId("auth-country"), "MX");
    await user.type(screen.getByTestId("auth-postal-code"), "01310100");
    expect(screen.queryByTestId("auth-cep-status")).not.toBeInTheDocument();
    expect(screen.getByTestId("auth-street")).toHaveValue("");
  });

  it("adapta labels para México (colonia / estado)", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    await user.selectOptions(screen.getByTestId("auth-country"), "MX");
    expect(screen.getByTestId("auth-district")).toBeInTheDocument();
    expect(screen.getByTestId("auth-postal-code")).toHaveAttribute("placeholder", "06600");
    expect(screen.getByTestId("auth-district").closest("label")).toHaveTextContent(/colonia/i);
  });

  it("troca idioma no cadastro e destaca Américas", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    renderAuth("signup", "/app");
    expect(await screen.findByTestId("auth-form")).toBeInTheDocument();
    expect(screen.getByTestId("auth-lang")).toBeInTheDocument();
    await user.click(screen.getByTestId("auth-lang-en"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/create account/i);
    expect(screen.getByTestId("auth-country")).toHaveValue("US");
    await user.click(screen.getByTestId("auth-lang-es"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/crear cuenta/i);
    expect(screen.getByTestId("auth-country")).toHaveValue("MX");
  });

  it("perfil completo segue para o destino", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = true;
    renderAuth("login", "/app?tema=space");
    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
  });

  it("e-mail ainda não confirmado permanece na sessão", async () => {
    setToken("test-token");
    state.isGuest = false;
    state.emailVerified = false;
    renderAuth("login", "/app");
    expect(await screen.findByTestId("auth-check-email")).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
  });

  it("link antigo de verificação volta ao cadastro", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          `/verificar-email?token=test-verify-token&next=${encodeURIComponent("/app?tema=space")}`,
        ]}
      >
        <Routes>
          <Route path="/verificar-email" element={<VerifyEmail />} />
          <Route path="/cadastro" element={<div data-testid="signup-dest">signup</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("signup-dest")).toBeInTheDocument();
  });

  it("mostra erro legível quando o perfil responde 502", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.patch("*/v1/auth/me", () => HttpResponse.text("bad gateway", { status: 502 })),
    );
    renderAuth("signup", "/app");
    await fillProfile(user);
    await user.click(screen.getByTestId("auth-submit"));
    expect(await screen.findByTestId("auth-error")).toHaveTextContent(/indisponível/i);
  });

  it("sai de Aguarde… quando o perfil estoura o timeout", async () => {
    const user = userEvent.setup();
    asIncompleteProfile();
    setAuthFetchTimeoutMsForTests(80);
    const { http, delay } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.patch("*/v1/auth/me", async () => {
        await delay("infinite");
        return new Response();
      }),
    );
    renderAuth("signup", "/app");
    await fillProfile(user);
    await user.click(screen.getByTestId("auth-submit"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/aguarde/i);
    expect(await screen.findByTestId("auth-error", {}, { timeout: 3000 })).toHaveTextContent(
      /indisponível/i,
    );
    expect(screen.getByTestId("auth-submit")).not.toBeDisabled();
  });
});
