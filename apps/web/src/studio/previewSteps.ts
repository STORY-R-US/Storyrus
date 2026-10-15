import type { Job } from "../types";

const CHAIN = ["AVATAR", "STORY", "EBOOK"] as const;

export type PreviewStepId = (typeof CHAIN)[number];
export type PreviewStepState = "wait" | "queued" | "now" | "done";

export type PreviewStep = {
  id: PreviewStepId;
  state: PreviewStepState;
};

function isChainJob(job: Job): boolean {
  return (
    (job.type === "AVATAR" || job.type === "STORY" || job.type === "EBOOK") &&
    Boolean(job.result?.payload?.preview_chain)
  );
}

/** Minutos típicos de cada etapa ainda aberta.
 * Personagem: uma imagem e o ajuste de rosto. História: o texto.
 * Imagens: capa, página e foto na mão, uma depois da outra.
 * Fila e nova tentativa alongam; o texto na tela diz "cerca de".
 */
const STEP_MINUTES: Record<PreviewStepId, [number, number]> = {
  AVATAR: [1, 2],
  STORY: [1, 1],
  EBOOK: [2, 3],
};

export function previewEtaMinutes(
  steps: PreviewStep[],
  imageProgress?: { done: number; total: number } | null,
): { min: number; max: number } {
  let min = 0;
  let max = 0;
  for (const step of steps) {
    if (step.state === "done") continue;
    let [lo, hi] = STEP_MINUTES[step.id];
    const progress = imageProgress;
    if (
      step.id === "EBOOK" &&
      step.state === "now" &&
      progress &&
      progress.total > 0 &&
      progress.done > 0 &&
      progress.done < progress.total
    ) {
      const left = progress.total - progress.done;
      lo = Math.max(1, left);
      hi = lo;
    }
    min += lo;
    max += hi;
  }
  if (min < 1) min = 1;
  if (max < min) max = min;
  return { min, max };
}

/** Qual figura a etapa Imagens está gerando. `done` é o progresso 0–3 do job. */
export function previewImageActivity(done?: number | null): "cover" | "page" | "hand" | "book" {
  if (done === 1) return "page";
  if (done === 2) return "hand";
  if (typeof done === "number" && done >= 3) return "book";
  return "cover";
}

/** Etapas da prévia, na ordem em que o Studio as monta. */
export function previewChainSteps(jobs: Job[]): PreviewStep[] {
  const chain = jobs.filter(isChainJob);
  const latest = (type: PreviewStepId) => [...chain].reverse().find((job) => job.type === type);
  const states: PreviewStepState[] = CHAIN.map((type) => {
    const job = latest(type);
    if (job?.status === "DONE") return "done";
    if (job?.status === "RUNNING") return "now";
    if (job?.status === "PENDING") return "queued";
    return "wait";
  });

  for (let i = 0; i < states.length; i += 1) {
    if (states[i] === "wait" && states.slice(i + 1).some((state) => state !== "wait")) {
      states[i] = "done";
    }
  }

  states[0] = states.every((state) => state === "wait") ? "queued" : states[0];

  return CHAIN.map((id, index) => ({ id, state: states[index] }));
}
