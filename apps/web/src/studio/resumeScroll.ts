/** Ao abrir um projeto salvo, leva a tela até a parte onde a família parou. */

const HAS_PENDING_ACTION = "button.kbtn-primary:not([disabled])";

/** A parte da tela com a ação pendente; null quando ela já está no topo. */
export function resumeTarget(root: ParentNode = document): HTMLElement | null {
  const order = root.querySelector<HTMLElement>("#pedido");
  if (order) return order;
  const storyReview = root.querySelector<HTMLElement>('[data-testid="studio-story-review"]');
  if (storyReview) return storyReview;
  const story = root.querySelector<HTMLElement>('[data-testid="studio-master-story"]');
  if (story?.querySelector(HAS_PENDING_ACTION)) return story;
  return null;
}

/**
 * Espera a tela terminar de montar e rola até a ação pendente.
 * Desiste se a pessoa mexer na tela antes. Devolve a função que cancela.
 */
export function resumeWherePaused(timeoutMs = 6000): () => void {
  if (typeof window === "undefined" || typeof Element.prototype.scrollIntoView !== "function") {
    return () => {};
  }
  let done = false;
  let stableSince = 0;
  let lastTop: number | null = null;
  const started = Date.now();
  let timer = 0;
  const events = ["wheel", "touchstart", "keydown", "mousedown"] as const;
  const stop = () => {
    if (done) return;
    done = true;
    window.clearInterval(timer);
    events.forEach((name) => window.removeEventListener(name, stop));
  };
  events.forEach((name) => window.addEventListener(name, stop, { passive: true }));
  timer = window.setInterval(() => {
    const target = resumeTarget();
    const expired = Date.now() - started > timeoutMs;
    if (!target) {
      if (expired) stop();
      return;
    }
    // As imagens acima ainda carregam e empurram a página: só rola quando a posição parar de mudar.
    const top = Math.round(target.getBoundingClientRect().top + window.scrollY);
    if (top !== lastTop) {
      lastTop = top;
      stableSince = Date.now();
      if (!expired) return;
    }
    if (Date.now() - stableSince < 400 && !expired) return;
    try {
      target.scrollIntoView({ block: "start" });
    } catch {
      /* jsdom */
    }
    stop();
  }, 200);
  return stop;
}
