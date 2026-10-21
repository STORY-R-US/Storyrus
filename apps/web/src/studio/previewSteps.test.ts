import { describe, expect, it } from "vitest";
import type { Job } from "../types";
import { previewChainSteps, previewEtaMinutes, previewImageActivity } from "./previewSteps";

function job(type: Job["type"], status: Job["status"]): Job {
  return {
    id: `${type}-${status}`,
    project_id: "p1",
    type,
    status,
    provider: null,
    cost_credits: 1,
    attempts: 1,
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    result: { payload: { preview_chain: true } },
  };
}

describe("previewChainSteps", () => {
  it("começa na fila quando ainda não há jobs", () => {
    expect(previewChainSteps([]).map((step) => step.state)).toEqual(["queued", "wait", "wait"]);
  });

  it("não chama de agora um personagem que ainda está pendente", () => {
    expect(previewChainSteps([job("AVATAR", "PENDING")]).map((step) => step.state)).toEqual([
      "queued",
      "wait",
      "wait",
    ]);
  });

  it("marca a etapa em andamento e as anteriores como prontas", () => {
    const steps = previewChainSteps([
      job("AVATAR", "DONE"),
      job("STORY", "DONE"),
      job("EBOOK", "RUNNING"),
    ]);
    expect(steps.map((step) => [step.id, step.state])).toEqual([
      ["AVATAR", "done"],
      ["STORY", "done"],
      ["EBOOK", "now"],
    ]);
  });

  it("começa em cerca de 4 a 6 minutos e encolhe conforme as etapas fecham", () => {
    expect(previewEtaMinutes(previewChainSteps([]))).toEqual({ min: 4, max: 6 });
    const mid = previewChainSteps([job("AVATAR", "DONE"), job("STORY", "RUNNING")]);
    expect(previewEtaMinutes(mid)).toEqual({ min: 3, max: 4 });
    const images = previewChainSteps([job("EBOOK", "RUNNING")]);
    expect(previewEtaMinutes(images, { done: 2, total: 3 })).toEqual({ min: 1, max: 1 });
  });

  it("mostra capa, página, livro na mão e o fechamento conforme as imagens saem", () => {
    expect(previewImageActivity(undefined)).toBe("cover");
    expect(previewImageActivity(0)).toBe("cover");
    expect(previewImageActivity(1)).toBe("page");
    expect(previewImageActivity(2)).toBe("hand");
    expect(previewImageActivity(3)).toBe("book");
  });

  it("trata etapa anterior ausente como pronta se a seguinte já começou", () => {
    expect(previewChainSteps([job("EBOOK", "PENDING")]).map((step) => step.state)).toEqual([
      "done",
      "done",
      "queued",
    ]);
  });
});
