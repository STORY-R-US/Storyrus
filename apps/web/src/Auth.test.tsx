import { afterEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

async function fillSignup(
  user: ReturnType<typeof userEvent.setup>,
  email = "nova@example.com",
) {
  await user.type(screen.getByTestId("auth-full-name"), "Ana Souza");
  await user.type(screen.getByTestId("auth-email"), email);
  await user.type(screen.getByTestId("auth-phone"), "11999999999");
  await user.type(screen.getByTestId("auth-password"), "password123");
  await user.type(screen.getByTestId("auth-password-confirm"), "password123");
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
  it("cria conta e mostra tela de verificar e-mail (sem JWT)", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app?tema=space");

    await fillSignup(user);
    await user.click(screen.getByTestId("auth-submit"));

    expect(await screen.findByTestId("auth-check-email")).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(state.email).toBe("nova@example.com");
    expect(state.emailVerified).toBe(false);
    expect(screen.queryByTestId("studio-dest")).not.toBeInTheDocument();
  });

  it("aceita cadastro com endereço internacional (US)", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");

    await user.type(screen.getByTestId("auth-full-name"), "Jane Doe");
    await user.type(screen.getByTestId("auth-email"), "jane@example.com");
    await user.type(screen.getByTestId("auth-phone"), "+15551234567");
    await user.type(screen.getByTestId("auth-password"), "password123");
    await user.type(screen.getByTestId("auth-password-confirm"), "password123");
    await user.selectOptions(screen.getByTestId("auth-country"), "US");
    expect(screen.getByTestId("auth-postal-code")).toHaveAttribute("minLength", "5");
    expect(screen.queryByTestId("auth-district")).not.toBeInTheDocument();
    expect(screen.queryByTestId("auth-complement")).not.toBeInTheDocument();
    await user.type(screen.getByTestId("auth-postal-code"), "90210");
    await user.type(screen.getByTestId("auth-street"), "Rodeo Dr");
    await user.type(screen.getByTestId("auth-number"), "100");
    await user.type(screen.getByTestId("auth-city"), "Beverly Hills");
    await user.selectOptions(screen.getByTestId("auth-state"), "CA");
    await user.click(screen.getByTestId("auth-accept-terms"));
    await user.click(screen.getByTestId("auth-submit"));

    expect(await screen.findByTestId("auth-check-email")).toBeInTheDocument();
    expect(state.country).toBe("US");
    expect(state.postalCode).toBe("90210");
    expect(state.stateUf).toBe("CA");
  });

  it("preenche endereço automaticamente a partir do CEP", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");
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
    renderAuth("signup", "/app");
    await user.type(screen.getByTestId("auth-postal-code"), "00000000");
    expect(await screen.findByTestId("auth-cep-status")).toHaveTextContent(/não encontrado/i);
    expect(screen.getByTestId("auth-street")).toHaveValue("");
  });

  it("preenche cidade e estado automaticamente a partir do ZIP americano", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");
    await user.selectOptions(screen.getByTestId("auth-country"), "US");
    await user.type(screen.getByTestId("auth-postal-code"), "90210");
    expect(screen.getByTestId("auth-postal-code")).toHaveValue("90210");
    expect(await screen.findByTestId("auth-cep-status")).toHaveTextContent(/endereço preenchido|address filled/i);
    expect(screen.getByTestId("auth-city")).toHaveValue("Beverly Hills");
    expect(screen.getByTestId("auth-state")).toHaveValue("CA");
  });

  it("não busca CEP quando o país é México", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");
    await user.selectOptions(screen.getByTestId("auth-country"), "MX");
    await user.type(screen.getByTestId("auth-postal-code"), "01310100");
    expect(screen.queryByTestId("auth-cep-status")).not.toBeInTheDocument();
    expect(screen.getByTestId("auth-street")).toHaveValue("");
  });

  it("adapta labels para México (colonia / estado)", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");
    await user.selectOptions(screen.getByTestId("auth-country"), "MX");
    expect(screen.getByTestId("auth-district")).toBeInTheDocument();
    expect(screen.getByTestId("auth-postal-code")).toHaveAttribute("placeholder", "06600");
    expect(screen.getByTestId("auth-district").closest("label")).toHaveTextContent(/colonia/i);
  });

  it("troca idioma no cadastro e destaca Américas", async () => {
    const user = userEvent.setup();
    renderAuth("signup", "/app");
    expect(screen.getByTestId("auth-lang")).toBeInTheDocument();
    await user.click(screen.getByTestId("auth-lang-en"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/create account/i);
    expect(screen.getByTestId("auth-country")).toHaveValue("US");
    await user.click(screen.getByTestId("auth-lang-es"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/crear cuenta/i);
    expect(screen.getByTestId("auth-country")).toHaveValue("MX");
  });

  it("confirma e-mail e entra no estúdio", async () => {
    state.isGuest = false;
    state.emailVerified = false;
    state.pendingVerifyToken = "test-verify-token";
    state.email = "verify@example.com";

    render(
      <MemoryRouter
        initialEntries={[
          `/verificar-email?token=test-verify-token&next=${encodeURIComponent("/app?tema=space")}`,
        ]}
      >
        <Routes>
          <Route path="/verificar-email" element={<VerifyEmail />} />
          <Route path="/app" element={<div data-testid="studio-dest">studio</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
    expect(state.emailVerified).toBe(true);
  });

  it("mostra o e-mail do link e permite reenviar se o token falhar", async () => {
    const user = userEvent.setup();
    state.isGuest = false;
    state.emailVerified = false;
    state.pendingVerifyToken = "test-verify-token";
    state.email = "verify@example.com";

    render(
      <MemoryRouter
        initialEntries={[
          `/verificar-email?token=wrong-token-value!!&email=${encodeURIComponent("Verify@Example.com")}`,
        ]}
      >
        <Routes>
          <Route path="/verificar-email" element={<VerifyEmail />} />
          <Route path="/app" element={<div data-testid="studio-dest">studio</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("verify-email-error")).toBeInTheDocument();
    expect(screen.getByTestId("verify-email-address")).toHaveTextContent("Verify@Example.com");
    await user.click(screen.getByTestId("verify-email-resend"));
    expect(await screen.findByTestId("verify-email-resend-hint")).toBeInTheDocument();
  });

  it("faz login e redireciona", async () => {
    const user = userEvent.setup();
    state.emailVerified = true;
    renderAuth("login", "/app");

    await user.type(screen.getByTestId("auth-email"), "ja@example.com");
    await user.type(screen.getByTestId("auth-password"), "password123");
    await user.click(screen.getByTestId("auth-submit"));

    expect(await screen.findByTestId("studio-dest")).toBeInTheDocument();
    await waitFor(() => expect(getToken()).toBe("test-token"));
  });

  it("faz login sem next e volta para a home", async () => {
    const user = userEvent.setup();
    state.emailVerified = true;
    renderAuth("login");

    await user.type(screen.getByTestId("auth-email"), "ja@example.com");
    await user.type(screen.getByTestId("auth-password"), "password123");
    await user.click(screen.getByTestId("auth-submit"));

    expect(await screen.findByTestId("home-dest")).toBeInTheDocument();
    expect(screen.queryByTestId("studio-dest")).not.toBeInTheDocument();
  });

  it("mostra link Esqueci a senha no login", () => {
    renderAuth("login", "/app?tema=space");
    const link = screen.getByTestId("auth-forgot");
    expect(link).toHaveTextContent(/esqueci a senha/i);
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("/esqueci-senha"),
    );
    expect(link).toHaveAttribute("href", expect.stringContaining("next="));
  });

  it("mostra e oculta a senha pelo olho", async () => {
    const user = userEvent.setup();
    renderAuth("login");
    const input = screen.getByTestId("auth-password");
    expect(input).toHaveAttribute("type", "password");
    await user.type(input, "segredo12");
    await user.click(screen.getByTestId("auth-password-toggle"));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("segredo12");
    await user.click(screen.getByTestId("auth-password-toggle"));
    expect(input).toHaveAttribute("type", "password");
  });

  it("não mostra Esqueci a senha no cadastro", () => {
    renderAuth("signup", "/app");
    expect(screen.queryByTestId("auth-forgot")).not.toBeInTheDocument();
  });

  it("alterna entre login e cadastro preservando next", async () => {
    const user = userEvent.setup();
    renderAuth("login", "/app?tema=pets");
    await user.click(screen.getByTestId("auth-switch"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/criar conta/i);
    expect(screen.getByTestId("auth-switch")).toHaveAttribute(
      "href",
      expect.stringContaining("next="),
    );
  });

  it("mostra erro legível quando a API responde 502", async () => {
    const user = userEvent.setup();
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.post("*/v1/auth/signup", () => HttpResponse.text("bad gateway", { status: 502 })),
    );
    renderAuth("signup", "/app");
    await fillSignup(user, "x@example.com");
    await user.click(screen.getByTestId("auth-submit"));
    expect(await screen.findByTestId("auth-error")).toHaveTextContent(/indisponível/i);
  });

  it("sai de Aguarde… quando o signup estoura o timeout", async () => {
    const user = userEvent.setup();
    setAuthFetchTimeoutMsForTests(80);
    const { http, delay } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.post("*/v1/auth/signup", async () => {
        await delay("infinite");
        return new Response();
      }),
    );
    renderAuth("signup", "/app");
    await fillSignup(user, "x@example.com");
    await user.click(screen.getByTestId("auth-submit"));
    expect(screen.getByTestId("auth-submit")).toHaveTextContent(/aguarde/i);
    expect(await screen.findByTestId("auth-error", {}, { timeout: 3000 })).toHaveTextContent(
      /indisponível/i,
    );
    expect(screen.getByTestId("auth-submit")).not.toBeDisabled();
  });

  it("login com e-mail pendente mostra reenvio", async () => {
    const user = userEvent.setup();
    state.isGuest = false;
    state.emailVerified = false;
    state.email = "wait@example.com";
    renderAuth("login", "/app");
    await user.type(screen.getByTestId("auth-email"), "wait@example.com");
    await user.type(screen.getByTestId("auth-password"), "password123");
    await user.click(screen.getByTestId("auth-submit"));
    expect(await screen.findByTestId("auth-check-email")).toBeInTheDocument();
    await user.click(screen.getByTestId("auth-resend-verify"));
    expect(await screen.findByTestId("auth-resend-hint")).toBeInTheDocument();
  });
});
