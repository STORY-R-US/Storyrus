import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProjectJourney } from "./ProjectJourney";
import type { Project } from "../types";

const project: Project = { id: "test", status: "STORY_READY", style: "cartoon", story_text: null,
  ebook_url: null, video_url: null, created_at: "2026-10-30", book_profile: { version: 1,
    stage: "story_approved", title: "Livro", gender: "f", languages: ["pt-BR"], current_page: 0 } };

describe("Project journey approval gates", () => {
  it("mantém a prévia como etapa atual até sua aprovação explícita", () => {
    render(<ProjectJourney project={project} lang="pt" />);
    expect(screen.getByText("Prévia e história").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Pedido e criação").closest("li")).not.toHaveAttribute("aria-current");
    expect(screen.getByText("Etapa 1 de 3")).toBeInTheDocument();
  });
  it("avança para o pedido após a aprovação da prévia", () => {
    render(<ProjectJourney project={{ ...project, purchase_flow: { preview_approved_at: "2026-10-30" } }} lang="pt" />);
    expect(screen.getByText("Pedido e criação").closest("li")).toHaveAttribute("aria-current", "step");
  });
  it("não apresenta o livro de contingência como pronto para revisão final", () => {
    render(<ProjectJourney project={{ ...project, book_profile: { ...project.book_profile!, stage: "book_ready", current_page: 16, credits_fallback: true },
      purchase_flow: { full_book_ready_at: "2026-10-30" } }} lang="pt" />);
    expect(screen.getByText("Etapa 1 de 3")).toBeInTheDocument();
    expect(screen.getByText("Revisão e entrega").closest("li")).not.toHaveAttribute("aria-current");
  });
});
