import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PreviewTrio } from "./PreviewTrio";

describe("PreviewTrio", () => {
  it("mostra capa, página e na mão", () => {
    render(
      <PreviewTrio
        coverUrl="https://cdn.test/capa.png"
        pageUrl="https://cdn.test/pagina.png"
        inHandUrl="https://cdn.test/mao.png"
      />,
    );
    expect(screen.getByTestId("studio-preview-cover")).toBeInTheDocument();
    expect(screen.getByTestId("studio-preview-page")).toBeInTheDocument();
    expect(screen.getByTestId("studio-preview-in-hand")).toBeInTheDocument();
  });

  it("não mostra o bloco quando não há imagens", () => {
    const { container } = render(
      <PreviewTrio coverUrl={null} pageUrl={null} inHandUrl={null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
