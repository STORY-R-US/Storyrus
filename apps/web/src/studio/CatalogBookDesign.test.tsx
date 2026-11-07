import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CatalogBookDesign } from "./CatalogBookDesign";

describe("complete catalog model", () => {
  it("offers compatible complete designs and shows their actual trio", () => {
    const change = vi.fn();
    const { container, rerender } = render(<CatalogBookDesign value="auto" onChange={change} cartoon={false} disabled={false} lang="pt" />);
    expect(screen.queryByRole("option", { name: /cartoon/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Padrão visual do livro"), { target: { value: "family" } });
    expect(change).toHaveBeenCalledWith("family");
    rerender(<CatalogBookDesign value="family" onChange={change} cartoon={false} disabled={false} lang="pt" />);
    const sources = Array.from(container.querySelectorAll("img")).map(image => image.getAttribute("src"));
    expect(sources).toEqual(["/exemplos/capa-amordebisavo.jpg", "/exemplos/pagina-amordebisavo.jpg", "/exemplos/foto-amordebisavo.jpg"]);
    expect(container.querySelector("details")).not.toHaveAttribute("open");
    rerender(<CatalogBookDesign value="auto" onChange={change} cartoon disabled={false} lang="pt" />);
    expect(screen.queryByRole("option", { name: "Amor de Bisavó" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: /cartoon/ })).toBeInTheDocument();
  });
});
