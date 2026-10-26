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
});
