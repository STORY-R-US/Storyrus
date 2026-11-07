import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import type { Project } from "../types";
import { PreviewCopyRecovery } from "./PreviewCopyRecovery";

afterEach(() => vi.restoreAllMocks());
const project: Project = { id: "failed-book", language: "pt-BR", status: "FAILED", style: "realistic", story_text: null, ebook_url: null, video_url: null, created_at: "2026-11-07", book_profile: { version: 1, stage: "ficha", title: "Um título longo", gender: "m", languages: ["pt-BR"], current_page: 0, locales: { "pt-BR": { title: "Um título longo", left: "Primeiro verso", right: "Segundo verso" } } } };

describe("recover preview copy", () => {
  it("saves literal text without starting a paid generation", async () => {
    const saved = vi.spyOn(api, "savePreviewCopy").mockResolvedValue(project);
    const generation = vi.spyOn(api, "startPreview");
    const onSaved = vi.fn();
    render(<PreviewCopyRecovery project={project} lang="pt" onSaved={onSaved} />);
    fireEvent.click(screen.getByText("Revisar os textos antes de tentar novamente"));
    expect(saved).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Título da capa"), { target: { value: "João no parque" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar textos" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(project));
    expect(saved).toHaveBeenCalledWith("failed-book", { title: "João no parque", left: "Primeiro verso", right: "Segundo verso" });
    expect(generation).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Textos salvos");
  });
  it("keeps correction errors visible without retrying automatically", async () => {
    vi.spyOn(api, "savePreviewCopy").mockRejectedValue(new Error("Encurte o título"));
    const onSaved = vi.fn();
    render(<PreviewCopyRecovery project={project} lang="pt" onSaved={onSaved} />);
    fireEvent.click(screen.getByText("Revisar os textos antes de tentar novamente"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar textos" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Encurte o título");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
