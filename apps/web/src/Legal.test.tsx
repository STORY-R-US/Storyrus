import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Legal } from "./Legal";
import { AppRoutes } from "./Root";

const CONTACT = "info@storyrus.ai";

describe("Legal", () => {
  it("mostra política de privacidade com seções e contato", () => {
    render(
      <MemoryRouter>
        <Legal kind="privacy" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { level: 1, name: /política de privacidade|privacidade/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /o que coletamos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /para que usamos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /usuários internacionais/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /conta e sessão/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /seus direitos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /crianças/i })).toBeInTheDocument();
    expect(document.body.textContent).toContain(CONTACT);
    expect(screen.getByRole("link", { name: /^exemplos$/i })).toHaveAttribute("href", "/exemplos");
    expect(screen.queryByRole("heading", { name: /termos de uso/i })).not.toBeInTheDocument();
  });

  it("mostra termos de uso com seções e contato", () => {
    render(
      <MemoryRouter>
        <Legal kind="terms" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { level: 1, name: /termos de uso/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /o serviço/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /cadastro e conta/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /responsável legal/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /pagamento do livro impresso/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /impressão e envio/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /usuários internacionais/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /propriedade e uso/i })).toBeInTheDocument();
    expect(screen.getByText(CONTACT)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^política de privacidade$/i })).not.toBeInTheDocument();
  });

  it("oferece links de volta para a página inicial", () => {
    render(
      <MemoryRouter>
        <Legal kind="privacy" />
      </MemoryRouter>,
    );

    const homeLinks = screen.getAllByRole("link", { name: /início|voltar à página inicial|story r us/i });
    expect(homeLinks.length).toBeGreaterThanOrEqual(2);
    for (const link of homeLinks) {
      expect(link).toHaveAttribute("href", "/");
    }
  });
});

describe("Rotas legais (AppRoutes)", () => {
  it.each([
    ["/privacidade", /política de privacidade|privacidade/i],
    ["/privacy", /política de privacidade|privacidade/i],
    ["/termos", /termos de uso/i],
    ["/terms", /termos de uso/i],
  ] as const)("rota %s renderiza o documento correto", async (path, heading) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
  });
});
