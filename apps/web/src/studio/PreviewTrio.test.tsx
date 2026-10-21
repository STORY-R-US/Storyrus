import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PreviewTrio } from "./PreviewTrio";

describe("PreviewTrio", () => {
  it("avisa quando as imagens da prévia são genéricas", () => {
    render(
      <PreviewTrio
        genericImages
        coverUrl="https://cdn.test/capa.png"
        pageUrl="https://cdn.test/pagina.png"
        inHandUrl="https://cdn.test/mao.png"
      />,
    );
    expect(screen.getByTestId("studio-generic-images")).toHaveTextContent(/sem créditos/i);
  });

  it("não mostra o aviso quando as imagens são da geração", () => {
    render(
      <PreviewTrio
        coverUrl="https://cdn.test/capa.png"
        pageUrl={null}
        inHandUrl={null}
      />,
    );
    expect(screen.queryByTestId("studio-generic-images")).not.toBeInTheDocument();
  });
});
