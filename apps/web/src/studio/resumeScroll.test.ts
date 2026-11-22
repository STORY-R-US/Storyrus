import { afterEach, describe, expect, it } from "vitest";
import { resumeTarget } from "./resumeScroll";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("resumeTarget", () => {
  it("fica no topo quando a ação pendente é a prévia", () => {
    document.body.innerHTML = '<div data-testid="studio-master-flow"><button class="kbtn kbtn-primary">Gostei</button></div>';
    expect(resumeTarget()).toBeNull();
  });

  it("vai para o pedido quando a família já chegou nele", () => {
    document.body.innerHTML =
      '<div data-testid="studio-master-story"><button class="kbtn kbtn-primary">Sim, aprovo</button></div><section id="pedido"></section>';
    expect(resumeTarget()?.id).toBe("pedido");
  });

  it("vai para a revisão da história antes de gerá-la", () => {
    document.body.innerHTML = '<section data-testid="studio-story-review"></section>';
    expect(resumeTarget()?.getAttribute("data-testid")).toBe("studio-story-review");
  });

  it("vai para a história quando falta aprová-la", () => {
    document.body.innerHTML =
      '<div data-testid="studio-master-story"><button class="kbtn kbtn-primary">Sim, aprovo</button></div>';
    expect(resumeTarget()?.getAttribute("data-testid")).toBe("studio-master-story");
  });

  it("não rola para a história já aprovada ou em andamento", () => {
    document.body.innerHTML =
      '<div data-testid="studio-master-story"><button class="kbtn kbtn-primary" disabled>Sim, aprovo</button></div>';
    expect(resumeTarget()).toBeNull();
  });
});
