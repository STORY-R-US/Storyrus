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
    const labels = screen.getAllByRole("figure").map((el) => el.textContent);
    expect(labels[0]).toContain("Capa");
    expect(labels[1]).toContain("Livro aberto");
    expect(labels[2]).toContain("Leitura");
    await userEvent.click(screen.getByRole("button", { name: "Gostei, continuar com meu livro" }));
    await waitFor(() => expect(approve).toHaveBeenCalledWith("master"));
    expect(story).not.toHaveBeenCalled();
  });

  it("regenerates only the selected preview image and language", async () => {
    const regenerate = vi.spyOn(api, "startPreview").mockResolvedValue(accepted);
    vi.spyOn(api, "getProject").mockResolvedValue(project);
    vi.spyOn(api, "listJobs").mockResolvedValue([]);
    render(<MasterBookFlow project={project} assets={assets} jobs={[]} setProject={vi.fn()} setJobs={vi.fn()} />);
    await userEvent.click(screen.getAllByRole("button", { name: "Gerar novamente" })[1]);
    await userEvent.type(screen.getByLabelText("Ajuste desta imagem"), "Mais luz");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar ajuste" }));
    await waitFor(() => expect(regenerate).toHaveBeenCalledWith("master", {
      language: "pt-BR", image: "02_LIVRO_ABERTO", adjustment: "Mais luz",
    }));
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
    expect(screen.getByText("Este é o rosto?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sim, aprovo" }));
    await waitFor(() => expect(page).toHaveBeenCalledWith("master"));
    expect(approve.mock.invocationCallOrder[0]).toBeLessThan(page.mock.invocationCallOrder[0]);
  });
});
