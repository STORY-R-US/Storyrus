import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { catalogModel } from "../catalogModel";
import { CatalogBookDesign, CatalogDesignSamples } from "./CatalogBookDesign";

describe("complete catalog model", () => {
  beforeAll(() => {
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value: function (this: HTMLDialogElement) { this.setAttribute("open", ""); },
    });
    Object.defineProperty(HTMLDialogElement.prototype, "close", {
      configurable: true,
      value: function (this: HTMLDialogElement) { this.removeAttribute("open"); },
    });
  });

  it("offers compatible complete designs and shows their actual trio", () => {
    const change = vi.fn();
    const { container, rerender } = render(<CatalogBookDesign value="auto" onChange={change} cartoon={false} disabled={false} lang="pt" />);
    expect(screen.queryByRole("option", { name: /cartoon/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Padrão visual do livro"), { target: { value: "family" } });
    expect(change).toHaveBeenCalledWith("family");
    rerender(<CatalogBookDesign value="family" onChange={change} cartoon={false} disabled={false} lang="pt" />);
    const sources = Array.from(container.querySelectorAll("img")).map(image => image.getAttribute("src"));
    expect(sources).toEqual(["/exemplos/covers/capa-amordebisavo-jpg-pt.webp", "/exemplos/pagina-amordebisavo.jpg", "/exemplos/foto-amordebisavo.jpg"]);
    expect(container.querySelector("details")).not.toHaveAttribute("open");
    rerender(<CatalogBookDesign value="auto" onChange={change} cartoon disabled={false} lang="pt" />);
    expect(screen.queryByRole("option", { name: "Amor de Bisavó" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: /cartoon/ })).toBeInTheDocument();
  });

  it.each(["pt", "en", "es"] as const)("shows the approved %s images in the studio and enlarged viewer", (lang) => {
    const model = catalogModel("catalog-realistic-69")!;
    const { container } = render(<CatalogDesignSamples model={{name: model.titles[lang], sources: model.sources}} lang={lang} />);
    expect(Array.from(container.querySelectorAll("figure img")).map(image => image.getAttribute("src"))).toEqual(
      ["cover", "page", "holding"].map(role => `/exemplos/catalog-20261124/69/${role}-${lang}.webp`),
    );
    fireEvent.click(container.querySelector("figure button")!);
    expect(container.querySelector("dialog img")).toHaveAttribute("src", `/exemplos/catalog-20261124/69/cover-${lang}.webp`);
  });
});
