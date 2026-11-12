import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogBookCard, catalogEntry } from "./Landing";
import { catalogModel, catalogModelId } from "./catalogModel";

describe("specific catalog models", () => {
  it.each([0, 1, 6, 21])("passes the exact selected model through registration for book %i", (index) => {
    const book=catalogEntry('pt',index)!;
    render(<MemoryRouter><CatalogBookCard book={book} lang="pt" personalize="Personalizar" /></MemoryRouter>);
    const href=screen.getByTestId('landing-personalize').getAttribute('href')!;
    const outer=new URL(href,'https://storyrus.local');
    const target=new URL(outer.searchParams.get('next') || href,'https://storyrus.local');
    expect(target.searchParams.get('modelo')).toBe(catalogModelId(index));
    expect(target.searchParams.get('titulo')).toBe(book.t);
  });
  it('blocks a book without interior instead of silently switching to the default', () => {
    render(<MemoryRouter><CatalogBookCard book={catalogEntry('pt',35)!} lang="pt" personalize="Personalizar" /></MemoryRouter>);
    expect(screen.queryByTestId('landing-personalize')).not.toBeInTheDocument();
    expect(screen.getByTestId('catalog-model-unavailable')).toHaveTextContent(/miolo/);
  });
  it('keeps cartoon model separate and blocks its missing interior independently', () => {
    expect(catalogModel(catalogModelId(12))?.available).toBe(true);
    expect(catalogModel(catalogModelId(12,true))?.available).toBe(false);
    render(<MemoryRouter><CatalogBookCard book={catalogEntry('pt',6)!} lang="pt" personalize="Personalizar" modo="cartoon" /></MemoryRouter>);
    expect(decodeURIComponent(screen.getByTestId('landing-personalize').getAttribute('href')!)).toContain('modelo=catalog-cartoon-6');
  });
});
