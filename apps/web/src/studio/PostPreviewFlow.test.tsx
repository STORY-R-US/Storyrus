import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api";
import type { Project, PrintOrder } from "../types";
import { PostPreviewFlow } from "./PostPreviewFlow";
import type { StudioAssets } from "./assets";

const project: Project = {
  id: "p1",
  status: "EBOOK_READY",
  style: "realistic",
  story_text: "Título: Lila e as estrelas",
  ebook_url: "preview.pdf",
  video_url: null,
  created_at: "2026-10-15T12:00:00Z",
  purchase_flow: {
    title: "Lila e as estrelas",
    preview_ready_at: "2026-10-15",
  },
};
const assets: StudioAssets = {
  character_url: null,
  realistic_url: null,
  extra_characters: [],
  page_images: ["/page-1.png", "/page-2.png"],
  ebook_url: "/complete.pdf",
  video_url: null,
  narrated_video_url: null,
};
const order: PrintOrder = {
  id: "o1",
  project_id: "p1",
  code: "SR-1234",
  book_size: "M",
  cover_type: "soft",
  quantity: 1,
  status: "awaiting_payment",
  block_reason: null,
  book_price_cents: 17700,
  freight_options: [],
  freight_service_id: null,
  freight_service_name: null,
  freight_price_cents: null,
  freight_days: null,
  payment_status: "unpaid",
  amount_cents: null,
  tracking_code: null,
  label_error: null,
  checkout_available: false,
  checkout_url: null,
  recipient_name: "Ana",
  postal_code: "01310100",
  street: "Av Paulista",
  number: "1000",
  complement: "",
  district: "Bela Vista",
  city: "São Paulo",
  state: "SP",
};
function Harness({
  initial = project,
  dirty = false,
  canConfirm = false,
}: {
  initial?: Project;
  dirty?: boolean;
  canConfirm?: boolean;
}) {
  const [p, setProject] = useState(initial);
  return (
    <PostPreviewFlow
      project={p}
      assets={assets}
      jobs={[]}
      dirty={dirty}
      isDemo={false}
      canConfirmPayment={canConfirm}
      onProject={setProject}
      onJobs={() => {}}
      onAdjust={() => {}}
    />
  );
}
afterEach(() => vi.restoreAllMocks());

describe("continuação da prévia", () => {
  it("oferece salvar para depois e remove a ação após salvar, mantendo o pagamento", async () => {
    const approved = { ...project, purchase_flow: { ...project.purchase_flow, preview_approved_at: "2026-10-15" } };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, checkout_available: true });
    const save = vi.spyOn(api, "saveQuotation").mockResolvedValue({ ...approved,
      purchase_flow: { ...approved.purchase_flow, quoted_at: "2026-10-30" } });
    const checkout = vi.spyOn(api, "checkoutPrint");
    render(<Harness initial={approved} />);
    expect(await screen.findByRole("button", { name: "Continuar para pagamento" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar para depois" }));
    expect(await screen.findByText("Pedido salvo. Você pode pagar agora ou retomar em Meus pedidos.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar para depois" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar para pagamento" })).toBeInTheDocument();
    expect(save).toHaveBeenCalledWith("p1");
    expect(checkout).not.toHaveBeenCalled();
  });
  it("aprova a prévia e salva uma cotação sem oferecer cobrança indisponível", async () => {
    const approved = {
      ...project,
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
      },
    };
    const approve = vi.spyOn(api, "approvePreview").mockResolvedValue(approved);
    vi.spyOn(api, "printOrder").mockResolvedValue(order);
    vi.spyOn(api, "saveQuotation").mockResolvedValue({
      ...approved,
      purchase_flow: { ...approved.purchase_flow, quoted_at: "2026-10-15" },
    });
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(
      screen.getByRole("button", { name: /gostei, continuar/i }),
    );
    expect(approve).toHaveBeenCalledWith("p1");
    expect(await screen.findByText("Pedido em cotação")).toBeInTheDocument();
    expect(screen.getByText("Pela gráfica")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /calcular frete/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /continuar para pagamento/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/nenhum valor será cobrado/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /salvar cotação/i }));
    expect(await screen.findByText(/cotação salva/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /meus pedidos/i })).toHaveAttribute(
      "href",
      "/meus-pedidos",
    );
  });

  it("a conta da Story R Us confirma o pagamento e segue para o livro", async () => {
    const waiting = {
      ...project,
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        stage: "awaiting_payment",
      },
    };
    const started = {
      ...waiting,
      purchase_flow: { ...waiting.purchase_flow, stage: "generating_book" },
    };
    vi.spyOn(api, "printOrder").mockResolvedValue(order);
    const confirm = vi.spyOn(api, "confirmManualPayment").mockResolvedValue({
      ...order,
      payment_status: "paid",
      amount_cents: 17700,
    });
    vi.spyOn(api, "getProject").mockResolvedValue(started);
    const user = userEvent.setup();
    render(<Harness initial={waiting} canConfirm />);
    expect(
      screen.queryByRole("button", { name: /continuar para pagamento/i }),
    ).not.toBeInTheDocument();
    await user.click(
      await screen.findByRole("button", {
        name: /confirmar pagamento e continuar/i,
      }),
    );
    expect(confirm).toHaveBeenCalledWith("p1");
    expect(await screen.findByText(/estamos preparando seu livro completo/i)).toBeInTheDocument();
  });

  it("impede aprovar alterações que ainda não foram enviadas", () => {
    render(<Harness dirty />);
    expect(
      screen.getByRole("button", { name: /gostei, continuar/i }),
    ).toBeDisabled();
    expect(screen.getByText(/envie suas alterações/i)).toBeInTheDocument();
  });

  it("só autoriza a impressão depois da revisão explícita do livro completo", async () => {
    const complete = {
      ...project,
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        full_book_ready_at: "2026-10-15",
        stage: "book_ready",
      },
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({
      ...order,
      payment_status: "paid",
    });
    const approve = vi
      .spyOn(api, "approveBook")
      .mockResolvedValue({ ...complete, book_approved_at: "2026-10-15" });
    render(<Harness initial={complete} />);
    const user = userEvent.setup();
    expect(
      screen.getByRole("button", { name: /aprovar livro para impressão/i }),
    ).toBeDisabled();
    expect(screen.getAllByRole("img")).toHaveLength(2);
    expect(
      screen.getByRole("link", { name: /abrir livro completo/i }),
    ).toHaveAttribute("href", "/complete.pdf");
    await user.click(screen.getByRole("checkbox", { name: /revisei todas/i }));
    await user.click(
      screen.getByRole("button", { name: /aprovar livro para impressão/i }),
    );
    expect(approve).toHaveBeenCalledOnce();
    expect(
      await screen.findByRole("heading", {
        name: "Livro aprovado para impressão",
      }),
    ).toBeInTheDocument();
  });

  it("mostra miniaturas leves na revisão e abre a página inteira no clique", () => {
    const complete = {
      ...project,
      language: "pt-BR",
      book_profile: {
        version: 1,
        stage: "book_ready",
        title: "Lila e as estrelas",
        gender: "girl",
        languages: ["pt-BR"],
        current_page: 20,
      },
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        full_book_ready_at: "2026-10-15",
        stage: "book_ready",
      },
    } satisfies Project;
    const full: StudioAssets = {
      ...assets,
      page_versions: [
        { url: "/p2.png", thumb_url: "/p2_MINIATURA.jpg", language: "pt-BR", role: "com_texto", filename: "p2.png", page: 2 },
        { url: "/p1.png", thumb_url: "/p1_MINIATURA.jpg", language: "pt-BR", role: "com_texto", filename: "p1.png", page: 1 },
        { url: "/p3.png", thumb_url: null, language: "pt-BR", role: "com_texto", filename: "p3.png", page: 3 },
        { url: "/p1-sem.png", language: "pt-BR", role: "sem_texto", filename: "p1s.png", page: 1 },
      ],
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, payment_status: "paid" });
    const { container } = render(
      <PostPreviewFlow
        project={complete}
        assets={full}
        jobs={[]}
        isDemo={false}
        dirty={false}
        onProject={vi.fn()}
        onJobs={vi.fn()}
        onAdjust={vi.fn()}
      />,
    );
    const links = [...container.querySelectorAll(".purchase-pages a")];
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["/p1.png", "/p2.png", "/p3.png"]);
    expect(links.map((a) => a.querySelector("img")?.getAttribute("src"))).toEqual([
      "/p1_MINIATURA.jpg",
      "/p2_MINIATURA.jpg",
      "/p3.png",
    ]);
  });

  it("mostra no topo da revisão um atalho para a aprovação, que fica depois das páginas", async () => {
    const complete = {
      ...project,
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        full_book_ready_at: "2026-10-15",
        stage: "book_ready",
      },
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, payment_status: "paid" });
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    render(<Harness initial={complete} />);
    const user = userEvent.setup();
    expect(screen.getByText("Marque a caixa acima para liberar o botão.")).toBeInTheDocument();
    await user.click(screen.getByTestId("purchase-go-approve"));
    expect(scroll).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("checkbox", { name: /revisei todas/i }));
    expect(screen.queryByText("Marque a caixa acima para liberar o botão.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aprovar livro para impressão/i })).toBeEnabled();
  });

  it("mostra a capa, a dedicatória e seis páginas enquanto o livro é produzido", () => {
    const generating = {
      ...project,
      child_name: "Lia",
      dedication: "Para a Lia, com amor.",
      language: "pt-BR",
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        stage: "generating_book",
      },
    };
    const sample: StudioAssets = {
      ...assets,
      book_cover_url: "/capa-limpa.png",
      previews: [
        { url: "/capa-marca.png", language: "pt-BR", role: "01_CAPA", filename: "capa.png" },
      ],
      page_versions: Array.from({ length: 8 }, (_, index) => ({
        url: `/pagina-${index + 1}.png`,
        language: "pt-BR",
        role: index === 7 ? "sem_texto" : "com_texto",
        filename: `pagina-${index + 1}.png`,
        page: index + 1,
      })),
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, payment_status: "paid" });
    render(
      <PostPreviewFlow
        project={generating}
        assets={sample}
        jobs={[]}
        isDemo={false}
        dirty={false}
        onProject={vi.fn()}
        onJobs={vi.fn()}
        onAdjust={vi.fn()}
      />,
    );
    expect(screen.getByRole("img", { name: "Capa" })).toHaveAttribute("src", "/capa-limpa.png");
    expect(screen.getByRole("heading", { name: "Dedicatória" })).toBeInTheDocument();
    expect(screen.getByText("Para a Lia, com amor.")).toBeInTheDocument();
    expect(screen.getAllByRole("img", { name: /^Página / })).toHaveLength(6);
    expect(screen.queryByRole("img", { name: "Página 7" })).not.toBeInTheDocument();
  });

  it("soma o e-book e a capa animada ao impresso e oferece a compra só digital", async () => {
    const approved = {
      ...project,
      purchase_flow: { ...project.purchase_flow, preview_approved_at: "2026-10-15" },
    };
    const prices = {
      extra: { ebook: 2900, video: 3900, bundle: 5900 },
      digital: { ebook: 9700, video: 11700, bundle: 13700 },
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, prices, items_price_cents: 17700 });
    const choose = vi
      .spyOn(api, "setPrintPurchase")
      .mockResolvedValueOnce({
        ...order,
        prices,
        extra_ebook: true,
        items_price_cents: 20600,
      })
      .mockResolvedValueOnce({
        ...order,
        prices,
        fulfillment: "digital",
        extra_ebook: true,
        items_price_cents: 9700,
      });
    const user = userEvent.setup();
    render(<Harness initial={approved} />);
    await user.click(await screen.findByRole("checkbox", { name: /e-book \(pdf\)/i }));
    expect(choose).toHaveBeenCalledWith("p1", { fulfillment: "print", ebook: true, video: false });
    expect(await screen.findByText("E-Book (PDF)")).toBeInTheDocument();
    expect(screen.getByText("Levando os dois, sai por + R$ 59,00 em vez de + R$ 68,00.")).toBeInTheDocument();
    expect(screen.getByText("R$ 206,00")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /só digital/i }));
    expect(choose).toHaveBeenLastCalledWith("p1", { fulfillment: "digital", ebook: true, video: false });
    expect(await screen.findByText("Sem frete")).toBeInTheDocument();
    expect(screen.queryByText("Endereço de entrega")).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /e-book \(pdf\)/i })).toBeDisabled();
  });

  it("libera o PDF só para quem comprou o e-book", () => {
    const complete = {
      ...project,
      purchase_flow: {
        ...project.purchase_flow,
        preview_approved_at: "2026-10-15",
        full_book_ready_at: "2026-10-15",
        stage: "book_ready",
        purchase: { fulfillment: "print" as const, ebook: false, video: false },
      },
    };
    vi.spyOn(api, "printOrder").mockResolvedValue({ ...order, payment_status: "paid" });
    render(<Harness initial={complete} />);
    expect(screen.queryByRole("link", { name: /abrir livro completo/i })).not.toBeInTheDocument();
  });
});
