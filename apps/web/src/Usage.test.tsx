import { describe, expect, it, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./Root";
import { Usage } from "./Usage";
import { Pedidos } from "./Pedidos";
import { Usuarios } from "./Usuarios";

describe("Pedidos", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("define o titulo da pagina", () => {
    render(<Pedidos />);
    expect(document.title).toBe("Pedidos — Story R Us");
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex, nofollow",
    );
  });

  it("abre o pedido detalhado depois da senha", async () => {
    const user = userEvent.setup();
    render(<Pedidos />);
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("heading", { name: /novo livro story r us realista/i })).toBeInTheDocument();
    const detail = screen.getByTestId("order-detail");
    expect(detail).toHaveTextContent("Matteo");
    expect(detail).toHaveTextContent("Português");
    expect(detail).toHaveTextContent("Matteo e o vale dos dinossauros");
    expect(detail).toHaveTextContent("Fotos anexadas");
    expect(detail).toHaveTextContent("Idade");
    expect(detail).toHaveTextContent("6");
    expect(detail).toHaveTextContent("M — 20 × 20 cm");
    expect(detail).toHaveTextContent("Capa dura");
    expect(detail).toHaveTextContent("Realista");
    expect(detail).toHaveTextContent("SR-TESTE001");
    expect(detail).toHaveTextContent("AA123BR");
    expect(detail.querySelector("img")).toHaveAttribute("src", "https://fotos.test/crianca.jpg");
    expect(detail.querySelector("a")).toHaveAttribute("href", "https://fotos.test/crianca.jpg");
  });

  it("abre Pedidos com a sessão do dono sem digitar senha", async () => {
    const { setToken } = await import("./api");
    const { state } = await import("./test/server");
    state.isOwner = true;
    setToken("owner-token");
    render(<Pedidos />);
    expect(await screen.findByRole("heading", { name: /novo livro story r us realista/i })).toBeInTheDocument();
    setToken(null);
  });

  it("com sessão, mostra abrindo e não pede senha enquanto carrega", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server, state } = await import("./test/server");
    const { setToken } = await import("./api");
    state.isOwner = true;
    setToken("owner-token");
    server.use(
      http.get("*/v1/usage", async () => {
        await new Promise((r) => setTimeout(r, 80));
        return HttpResponse.json({
          timezone: "America/Sao_Paulo",
          from_at: new Date().toISOString(),
          to_at: new Date().toISOString(),
          today_usd: 0,
          month_usd: 0,
          range_usd: 0,
          books_count: 0,
          avg_book_usd: null,
          by_type: [],
          by_provider: [],
          books: [],
          recent_jobs: [],
          events: [],
          events_count: 0,
          orders: [],
        });
      }),
    );
    render(<Pedidos />);
    expect(await screen.findByTestId("owner-access-opening")).toBeInTheDocument();
    expect(screen.queryByLabelText(/senha/i)).not.toBeInTheDocument();
    expect(await screen.findByTestId("pedidos-empty")).toBeInTheDocument();
    setToken(null);
  });

  it("renova a sessão vencida e abre Pedidos mesmo com a senha da conta salva", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server, state } = await import("./test/server");
    const { setToken } = await import("./api");
    state.isOwner = true;
    const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ sub: "u1", exp: Math.floor(Date.now() / 1000) - 120 }),
    );
    setToken(`${header}.${payload}.sig`);
    sessionStorage.setItem("storyrus.usage.password", "senha-da-conta");
    server.use(
      http.get("*/v1/usage", ({ request }) => {
        const auth = request.headers.get("Authorization") || "";
        if (auth !== "Bearer test-token-resumed") {
          return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
        }
        return HttpResponse.json({
          timezone: "America/Sao_Paulo",
          from_at: new Date().toISOString(),
          to_at: new Date().toISOString(),
          today_usd: 0,
          month_usd: 0,
          range_usd: 0,
          books_count: 1,
          avg_book_usd: null,
          by_type: [],
          by_provider: [],
          books: [],
          recent_jobs: [],
          events: [],
          events_count: 0,
          orders: [
            {
              id: "order-1",
              project_id: "p1",
              summary: "NOVO LIVRO STORY R US REALISTA\nNome: Matteo",
              created_at: new Date().toISOString(),
              child_age: 6,
              book_size: "M",
              cover_type: "hard",
              style: "realistic",
              photo_urls: [],
            },
          ],
        });
      }),
    );
    render(<Pedidos />);
    expect(
      await screen.findByRole("heading", { name: /novo livro story r us realista/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/senha inválida/i)).not.toBeInTheDocument();
    setToken(null);
  });

  it("em falha de rede com sessão, oferece tentar de novo sem travar na senha", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server, state } = await import("./test/server");
    const { setToken } = await import("./api");
    state.isOwner = true;
    setToken("owner-token");
    server.use(http.get("*/v1/usage", () => HttpResponse.error()));
    render(<Pedidos />);
    expect(await screen.findByTestId("owner-access-opening")).toBeInTheDocument();
    expect(await screen.findByTestId("owner-access-retry")).toBeInTheDocument();
    expect(screen.queryByLabelText(/senha/i)).not.toBeInTheDocument();
    setToken(null);
  });
});

describe("Painel /usuarios", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("rota /usuarios nao cai na landing", async () => {
    render(
      <MemoryRouter initialEntries={["/usuarios"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /^usuários$/i })).toBeInTheDocument();
    expect(screen.queryByText(/escolha um livro/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(document.title).toBe("Usuários — Story R Us");
    });
  });

  it("pede senha e mostra contas depois do ok", async () => {
    const user = userEvent.setup();
    render(<Usuarios />);
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/senha/i), "errada");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText(/senha inválida/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText(/senha/i));
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText(/2 no total/i)).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
    expect(screen.getByText("bruno@example.com")).toBeInTheDocument();
    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    expect(screen.queryByText(/crédito/i)).not.toBeInTheDocument();
    expect(screen.getByRole("list", { name: /lista de usuários/i })).toBeInTheDocument();
    expect(screen.getByTestId("owner-user-placeholder")).toHaveTextContent(/clique numa conta na lista/i);
    expect(screen.queryByTestId("owner-user-detail")).not.toBeInTheDocument();
    const nav = screen.getByTestId("owner-nav");
    expect(nav).toHaveTextContent("Gastos");
    expect(nav).toHaveTextContent("Pedidos");
    expect(nav.querySelector('a[aria-current="page"]')).toHaveAttribute("href", "/usuarios");
  });

  it("abre os dados do usuario e permite editar", async () => {
    const user = userEvent.setup();
    render(<Usuarios />);
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText(/2 no total/i)).toBeInTheDocument();

    await user.click(screen.getByTestId("owner-user-open-u1"));
    expect(screen.queryByTestId("owner-user-placeholder")).not.toBeInTheDocument();
    expect(await screen.findByTestId("owner-user-street")).toHaveValue("Avenida Paulista");
    expect(screen.getByTestId("owner-user-city")).toHaveValue("Sao Paulo");
    expect(screen.queryByTestId("owner-user-credits")).not.toBeInTheDocument();

    await user.clear(screen.getByTestId("owner-user-full-name"));
    await user.type(screen.getByTestId("owner-user-full-name"), "Ana Silva");
    await user.click(screen.getByTestId("owner-user-save"));

    expect(await screen.findByTestId("owner-user-saved")).toHaveTextContent(/salvas/i);
    expect(screen.getByText("Ana Silva")).toBeInTheDocument();
    expect(screen.queryByText(/crédito/i)).not.toBeInTheDocument();
    expect(screen.getByText("bruno@example.com")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /lista de usuários/i })).toBeInTheDocument();
  });

  it("mantem a lista visivel se o detalhe da API ainda nao existir", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.get("*/v1/users/:id", () =>
        HttpResponse.json({ detail: "Not Found" }, { status: 404 }),
      ),
    );
    const user = userEvent.setup();
    render(<Usuarios />);
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText("ana@example.com")).toBeInTheDocument();

    await user.click(screen.getByTestId("owner-user-open-u1"));

    expect(screen.getByRole("list", { name: /lista de usuários/i })).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
    expect(screen.getByText("bruno@example.com")).toBeInTheDocument();
    expect(screen.getByTestId("owner-user-full-name")).toHaveValue("Ana Souza");
    expect(screen.queryByTestId("owner-user-credits")).not.toBeInTheDocument();
    expect(screen.queryByText(/falha ao abrir/i)).not.toBeInTheDocument();
  });

  it("filtra a lista e exclui um usuario depois da confirmacao", async () => {
    const user = userEvent.setup();
    render(<Usuarios />);
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText("ana@example.com")).toBeInTheDocument();

    await user.type(screen.getByTestId("owner-user-search"), "bruno");
    expect(screen.getByText("bruno@example.com")).toBeInTheDocument();
    expect(screen.queryByText("ana@example.com")).not.toBeInTheDocument();

    await user.clear(screen.getByTestId("owner-user-search"));
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();

    await user.click(screen.getByTestId("owner-user-open-u1"));
    await user.click(screen.getByTestId("owner-user-delete"));
    expect(screen.getByText(/não volta atrás/i)).toBeInTheDocument();
    await user.click(screen.getByTestId("owner-user-delete-confirm"));

    expect(await screen.findByText(/1 no total/i)).toBeInTheDocument();
    expect(screen.queryByText("ana@example.com")).not.toBeInTheDocument();
    expect(screen.getByText("bruno@example.com")).toBeInTheDocument();
    expect(screen.queryByTestId("owner-user-detail")).not.toBeInTheDocument();
    expect(screen.getByTestId("owner-user-placeholder")).toBeInTheDocument();
  });
});

describe("Painel /gastos", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("rota /gastos nao cai na landing", async () => {
    render(
      <MemoryRouter initialEntries={["/gastos"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: /gastos da plataforma/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/escolha um livro/i)).not.toBeInTheDocument();
    expect(document.title).toBe("Gastos — Story R Us");
  });

  it("pede senha e mostra totais depois do ok", async () => {
    const user = userEvent.setup();
    render(<Usage />);
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/senha/i), "errada");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText(/senha inválida/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText(/senha/i));
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText(/hoje/i)).toBeInTheDocument();
    expect(screen.getByText(/ticket médio/i)).toBeInTheDocument();
    expect(screen.getAllByText(/matteo/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/página 3 — geração/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /extrato/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^pedidos$/i })).toBeInTheDocument();
    expect(screen.getByText(/NOVO LIVRO STORY R US REALISTA/)).toBeInTheDocument();
    expect(screen.getByText(/Fotos anexadas: 1 \(arquivo recebido\)/)).toBeInTheDocument();
    expect(screen.getByText(/Projeto p1/)).toBeInTheDocument();
  });

  it("mostra alerta de lockout quando a API devolve 429", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.get("*/v1/usage", () =>
        HttpResponse.json(
          { detail: "Muitas tentativas; tente mais tarde" },
          { status: 429 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<Usage />);
    await user.type(screen.getByLabelText(/senha/i), "qualquer");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByText(/muitas tentativas/i)).toBeInTheDocument();
  });

  it("mostra alertas de custo quando a API devolve anomalies", async () => {
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("./test/server");
    server.use(
      http.get("*/v1/usage", () =>
        HttpResponse.json({
          timezone: "America/Sao_Paulo",
          from_at: new Date().toISOString(),
          to_at: new Date().toISOString(),
          today_usd: 9.5,
          month_usd: 9.5,
          range_usd: 9.5,
          books_count: 0,
          avg_book_usd: null,
          by_type: [],
          by_provider: [],
          books: [],
          recent_jobs: [],
          events: [],
          events_count: 0,
          daily_spend_usd_ceiling: 10,
          anomalies: [
            {
              kind: "daily_usd_warn",
              severity: "warn",
              message: "Burn do dia em 95% do teto (9.5000 / 10.0000)",
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    render(<Usage />);
    await user.type(screen.getByLabelText(/senha/i), "segredo");
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    expect(await screen.findByRole("heading", { name: /alertas de custo/i })).toBeInTheDocument();
    expect(screen.getByText(/95% do teto/i)).toBeInTheDocument();
  });
});
