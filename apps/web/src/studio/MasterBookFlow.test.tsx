import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import type { JobAccepted, Project } from "../types";
import { MasterBookFlow } from "./MasterBookFlow";
import type { StudioAssets } from "./assets";

const project: Project = { id: "master", status: "EBOOK_READY", style: "cartoon", language: "pt-BR",
  story_text: null, ebook_url: null, video_url: null, created_at: "2026-10-15",
  book_profile: { version: 1, stage: "preview_ready", title: "Lia e as estrelas", gender: "f",
    languages: ["pt-BR"], current_page: 0 } };
const assets: StudioAssets = { character_url: null, realistic_url: null, extra_characters: [],
  page_images: [], ebook_url: null, video_url: null, narrated_video_url: null,
  previews: ["03_LEITURA", "01_CAPA", "02_LIVRO_ABERTO"].map((role) => ({ role, language: "pt-BR", url: `/image/${role}`, filename: `${role}.png` })) };
const accepted: JobAccepted = { job_id: "job", status: "PENDING", type: "EBOOK", estimated_cost_credits: 0 };

afterEach(() => vi.restoreAllMocks());

describe("Studio approval stages", () => {
  it("explica os dados da criança e salva o que o adulto escreve", async () => {
    const named = {
      ...project,
      child_name: "lila",
      child_age: 5,
      child_trait: "curiosidade",
      child_interest: "descobertas",
      book_profile: {
        ...project.book_profile!,
        costume: "roupa de aventura azul",
        trait: "curiosidade",
        interest: "descobertas",
      },
    };
    const save = vi.spyOn(api, "saveChildProfile").mockResolvedValue(named);
    vi.spyOn(api, "getProject").mockResolvedValue(named);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    vi.spyOn(api, "getAssets").mockResolvedValue(assets);
    render(<MasterBookFlow project={named} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} setAssets={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "A Criança Nesta História" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nome da criança")).toHaveValue("Lila");
    expect(screen.queryByLabelText(/roupa na história/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/jeito da criança/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/o que ela gosta/i)).not.toBeInTheDocument();
    expect(screen.queryByText("lila · 5")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar dados da criança" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("master", {
      childName: "Lila",
      childAge: 5,
      costume: "roupa de aventura azul",
      trait: "curiosidade",
      interest: "descobertas",
    }));
  });

  it("aplica a pausa global a projetos comuns e impede reativar IA pela tela", async () => {
    render(<MasterBookFlow project={{ ...project, test_mode: true, ai_generation_paused: true }}
      assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.getByTestId("studio-test-mode")).toHaveTextContent("sem chamadas à IA");
    expect(screen.queryByRole("button", { name: "Gerar versão real com IA" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sugerir 5 títulos com IA" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar prévia e continuar o teste" })).toBeEnabled();
  });
  it("identifica a prévia genérica e aguarda a aprovação manual no teste sem IA", async () => {
    const testProject = { ...project, book_profile: { ...project.book_profile!, test_mode: true } };
    const story = vi.spyOn(api, "startStep").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(testProject);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={testProject} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.getByTestId("studio-test-mode")).toHaveTextContent("sem chamadas à IA");
    expect(screen.queryByRole("button", { name: "Sugerir 5 títulos com IA" })).not.toBeInTheDocument();
    expect(story).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Aprovar prévia e continuar o teste" }));
    await waitFor(() => expect(story).toHaveBeenCalledWith("master", "story"));
  });
  it("interrompe o livro antigo de contingência antes de qualquer aprovação", async () => {
    const invalid = { ...project, book_profile: { ...project.book_profile!, stage: "book_ready", current_page: 16, credits_fallback: true },
      purchase_flow: { stage: "book_ready", full_book_ready_at: "2026-10-30" } };
    const retry = vi.spyOn(api, "retryRealPreview").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(invalid);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    const approve = vi.spyOn(api, "approveBook");
    render(<MasterBookFlow project={invalid} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.getByTestId("studio-preview-recovery")).toBeInTheDocument();
    expect(screen.queryByTestId("purchase-flow")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprovar livro" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Refazer prévia com IA" }));
    await waitFor(() => expect(retry).toHaveBeenCalledWith("master"));
    expect(approve).not.toHaveBeenCalled();
  });
  it("abre os ajustes depois da aprovação da história e envia o pedido de melhoria", async () => {
    const ready = { ...project, theme: "space", book_profile: { ...project.book_profile!, stage: "story_approved" } };
    const save = vi.spyOn(api, "savePreviewChanges").mockResolvedValue(accepted);
    const approve = vi.spyOn(api, "approvePreview");
    vi.spyOn(api, "getProject").mockResolvedValue(ready);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={ready} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Quero ajustar" }));
    expect(screen.getByRole("region", { name: "Ajustar Minha Prévia" })).toBeInTheDocument();
    const notes = screen.getByLabelText("O que você quer melhorar?");
    expect(notes).toHaveFocus();
    expect(screen.getByRole("button", { name: "Gostei, continuar com meu livro" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Aplicar ajuste" })).toBeDisabled();
    await userEvent.type(notes, "Mais estrelas na capa");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar ajuste" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("master", {
      title: "Lia e as estrelas", theme_description: "space", photo_notes: "Mais estrelas na capa", story_text: "",
    }));
    expect(approve).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("region", { name: "Ajustar Minha Prévia" })).not.toBeInTheDocument());
  });

  it("cancela os ajustes sem alterar o livro e libera a aprovação", async () => {
    const ready = { ...project, theme: "space", book_profile: { ...project.book_profile!, stage: "story_approved" } };
    const save = vi.spyOn(api, "savePreviewChanges");
    render(<MasterBookFlow project={ready} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Quero ajustar" }));
    await userEvent.type(screen.getByLabelText("O que você quer melhorar?"), "Mais luz");
    await userEvent.click(screen.getByRole("button", { name: "Cancelar ajustes" }));
    expect(screen.queryByRole("region", { name: "Ajustar Minha Prévia" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gostei, continuar com meu livro" })).toBeEnabled();
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Quero ajustar" }));
    expect(screen.getByLabelText("O que você quer melhorar?")).toHaveValue("");
  });

  it("gera cinco títulos por IA e só altera a capa após confirmar a escolha", async () => {
    const titles = ["Lia na Lua", "Lia e o cometa", "Lia astronauta", "As estrelas de Lia", "Lia e o universo"];
    const suggest = vi.spyOn(api, "suggestPreviewTitles").mockResolvedValue({ titles });
    const save = vi.spyOn(api, "updatePreviewTitle").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(project);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Como você gostaria de melhorar o título? (opcional)"), "Mais aventura");
    await userEvent.click(screen.getByRole("button", { name: "Sugerir 5 títulos com IA" }));
    await screen.findByRole("list", { name: "Sugestões geradas pela IA" });
    expect(suggest).toHaveBeenCalledWith("master", "Mais aventura");
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Lia na Lua Escolher" }));
    expect(screen.getByTestId("studio-preview-title")).toHaveValue("Lia na Lua");
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Atualizar título" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("master", "Lia na Lua"));
  });

  it("exibe falha da IA e permite tentar novamente sem trocar o título", async () => {
    vi.spyOn(api, "suggestPreviewTitles").mockRejectedValue(new Error("IA indisponível"));
    const save = vi.spyOn(api, "updatePreviewTitle");
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Sugerir 5 títulos com IA" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("IA indisponível");
    expect(screen.getByRole("button", { name: "Sugerir 5 títulos com IA" })).toBeEnabled();
    expect(screen.getByTestId("studio-preview-title")).toHaveValue("Lia e as estrelas");
    expect(save).not.toHaveBeenCalled();
  });
  it("envia a correção de uma página para a IA", async () => {
    const ready = {
      ...project,
      story_text: "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu.",
      book_profile: {
        ...project.book_profile!,
        stage: "story_ready",
        stories: { "pt-BR": "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu." },
      },
    };
    const story = vi.spyOn(api, "startStep").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(ready);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={ready} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Alterar" }));
    const note = screen.getByLabelText("O que devemos ajustar");
    expect(screen.queryByText(/não entra na página/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ajustar página" })).toBeDisabled();
    await userEvent.type(note, "Mais estrelas no céu");
    await userEvent.click(screen.getByRole("button", { name: "Ajustar página" }));
    await waitFor(() => expect(story).toHaveBeenCalledWith("master", "story", {
      page: 1, brief: "Mais estrelas no céu",
    }));
  });

  it("marca a página alterada e desfaz a alteração", async () => {
    const ready = {
      ...project,
      story_text: "Título: Lia e as estrelas\n\nPágina 1:\nLia acendeu estrelas.",
      book_profile: {
        ...project.book_profile!,
        stage: "story_ready",
        stories: { "pt-BR": "Título: Lia e as estrelas\n\nPágina 1:\nLia acendeu estrelas." },
        page_revisions: { "pt-BR": { "1": "Lia olhou o céu." } },
      },
    };
    const undo = vi.spyOn(api, "undoStoryPage").mockResolvedValue(ready);
    const cleared = {
      ...ready,
      book_profile: { ...ready.book_profile, page_revisions: {} },
    };
    vi.spyOn(api, "getProject").mockResolvedValue(cleared);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    function Harness() {
      const [current, setCurrent] = useState<Project>(ready);
      return (
        <MasterBookFlow
          project={current}
          assets={assets}
          jobs={[]}
          setProject={setCurrent}
          setJobs={vi.fn()}
        />
      );
    }
    render(<Harness />);
    expect(screen.getByText("Página alterada")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Desfazer alteração" }));
    await waitFor(() => expect(undo).toHaveBeenCalledWith("master", 1));
    await waitFor(() => expect(screen.queryByText("Página alterada")).not.toBeInTheDocument());
  });

  it("pede a aprovação da história antes da cotação", async () => {
    const ready = {
      ...project,
      story_text: "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu.",
      book_profile: {
        ...project.book_profile!,
        stage: "story_ready",
        stories: { "pt-BR": "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu." },
      },
    };
    const approve = vi.spyOn(api, "approveStory").mockResolvedValue(ready);
    const avatar = vi.spyOn(api, "startStep").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(ready);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={ready} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.getByTestId("studio-master-story")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Gostei, continuar com meu livro" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sim, aprovo" }));
    await waitFor(() => expect(approve).toHaveBeenCalledWith("master"));
    expect(avatar).not.toHaveBeenCalled();
  });

  it("abre a cotação depois que a história foi aprovada", async () => {
    const approved = {
      ...project,
      book_profile: { ...project.book_profile!, stage: "story_approved" },
    };
    const story = vi.spyOn(api, "startStep").mockResolvedValue(accepted);
    const approve = vi.spyOn(api, "approvePreview").mockResolvedValue(approved);
    vi.spyOn(api, "getProject").mockResolvedValue(approved);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={approved} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(story).not.toHaveBeenCalled();
    expect(screen.getByTestId("studio-story-review")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revisão" })).toBeInTheDocument();
    expect(screen.getByText("Lia e as estrelas")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ir para o pedido" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("studio-child-profile")).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Resumo do pedido" })).not.toBeInTheDocument();
    const labels = screen.getAllByRole("figure").map((el) => el.textContent);
    expect(labels[0]).toContain("Capa");
    expect(labels[1]).toContain("Livro Aberto");
    expect(labels[2]).toContain("Segurando o livro");
    await userEvent.click(screen.getByRole("button", { name: "Gostei, continuar com meu livro" }));
    await waitFor(() => expect(approve).toHaveBeenCalledWith("master"));
    expect(story).not.toHaveBeenCalled();
  });

  it("abre a sugestão de melhoria no lugar de baixar a imagem", async () => {
    const regenerate = vi.spyOn(api, "startPreview").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(project);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.queryByRole("link", { name: "Baixar imagem" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("O que melhorar nesta imagem?")).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Sugerir melhoria" })[0]);
    const note = screen.getByLabelText("O que melhorar nesta imagem?");
    expect(screen.getByRole("button", { name: "Enviar sugestão" })).toBeDisabled();
    await userEvent.type(note, "Mais estrelas na capa");
    await userEvent.click(screen.getByRole("button", { name: "Enviar sugestão" }));
    await waitFor(() => expect(regenerate).toHaveBeenCalledWith("master", {
      language: "pt-BR", image: "01_CAPA", adjustment: "Mais estrelas na capa",
    }));
  });

  it("coloca a opção escolhida no título e só salva ao confirmar", async () => {
    const save = vi.spyOn(api, "updatePreviewTitle").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(project);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getByText("Outras opções de título", { selector: "summary" }));
    expect(screen.getByRole("list", { name: "Outras opções de título" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "A história de Lia Usar este título" }));
    expect(screen.getByTestId("studio-preview-title")).toHaveValue("A história de Lia");
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Atualizar título" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("master", "A história de Lia"));
  });

  it("não mostra o ajuste solto da imagem na prévia pronta", () => {
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Gerar novamente" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Ajuste desta imagem")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aplicar ajuste" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Sugerir melhoria" })).toHaveLength(3);
  });

  it("atualiza o título da prévia e conserva a história", async () => {
    const ready = {
      ...project,
      story_text: "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu.",
      book_profile: {
        ...project.book_profile!,
        stage: "story_ready",
        stories: { "pt-BR": "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu." },
      },
    };
    const update = vi.spyOn(api, "updatePreviewTitle").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(ready);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    vi.spyOn(api, "getAssets").mockResolvedValue(assets);
    render(<MasterBookFlow project={ready} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} setAssets={vi.fn()} />);
    const title = screen.getByLabelText("Título do livro");
    expect(title).toHaveValue("Lia e as estrelas");
    expect(screen.getByText("Lia olhou o céu.")).toBeInTheDocument();
    await userEvent.clear(title);
    await userEvent.type(title, "Lia e o mar");
    await userEvent.click(screen.getByRole("button", { name: "Atualizar título" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith("master", "Lia e o mar"));
  });

  it("requires face approval before requesting the first page", async () => {
    const approve = vi.spyOn(api, "approveCharacter").mockResolvedValue(project);
    const page = vi.spyOn(api, "nextBookPage").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(project);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    const avatar = { ...project, book_profile: { ...project.book_profile!, stage: "avatar_ready" } };
    render(<MasterBookFlow project={avatar} assets={{ ...assets, character_url: "/avatar" }} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    expect(page).not.toHaveBeenCalled();
    expect(screen.getByText("Este É O Rosto?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sim, aprovo" }));
    await waitFor(() => expect(page).toHaveBeenCalledWith("master"));
    expect(approve.mock.invocationCallOrder[0]).toBeLessThan(page.mock.invocationCallOrder[0]);
  });

  it("pede o que melhorar em cada página e o consentimento fica na aprovação", async () => {
    const ready = {
      ...project,
      book_profile: { ...project.book_profile!, stage: "book_ready", current_page: 1 },
      purchase_flow: { stage: "book_ready", preview_approved_at: "2026-10-15", full_book_ready_at: "2026-10-15" },
    };
    const redo = vi.spyOn(api, "nextBookPage").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(ready);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    vi.spyOn(api, "getAssets").mockResolvedValue(assets);
    render(
      <MasterBookFlow
        project={ready}
        assets={{
          ...assets,
          page_versions: [{ role: "com_texto", language: "pt-BR", page: 1, url: "/p1.png", filename: "p1.png" }],
        }}
        jobs={[]}
        setProject={vi.fn()}
        setJobs={vi.fn()}
        setAssets={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Páginas Do Livro" })).toBeInTheDocument();
    expect(screen.getByText(/não dá para voltar atrás/i)).toBeInTheDocument();
    const note = screen.getByLabelText("O que melhorar nesta página");
    await userEvent.type(note, "Mais luz na janela");
    await userEvent.click(screen.getByRole("button", { name: "Melhorar esta página" }));
    await waitFor(() => expect(redo).toHaveBeenCalledWith("master", {
      page: 1,
      adjustment: "Mais luz na janela",
    }));
  });
});
