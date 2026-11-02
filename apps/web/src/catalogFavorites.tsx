import { useEffect, useState } from "react";
import type { Lang } from "./i18n/lang";
const KEY = "storyrus:favorite-books";
const EVENT = "storyrus:favorites-changed";
const COPY = {
  pt: { add: "Adicionar aos favoritos", remove: "Remover dos favoritos", filter: "Só favoritos", all: "Todos os livros", empty: "Toque no coração de um livro para salvar seus favoritos.", saved: "Favoritos salvos neste navegador." },
  en: { add: "Add to favorites", remove: "Remove from favorites", filter: "Favorites only", all: "All books", empty: "Tap a book’s heart to save your favorites.", saved: "Favorites saved in this browser." },
  es: { add: "Añadir a favoritos", remove: "Quitar de favoritos", filter: "Solo favoritos", all: "Todos los libros", empty: "Toca el corazón de un libro para guardar tus favoritos.", saved: "Favoritos guardados en este navegador." },
};
function readFavorites(): number[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(value) ? [...new Set(value.filter((id): id is number => Number.isInteger(id) && id >= 0))] : [];
  } catch { return []; }
}
export function useCatalogFavorites() {
  const [favorites, setFavorites] = useState(readFavorites);
  useEffect(() => {
    const sync = () => setFavorites(readFavorites());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener("storage", sync); };
  }, []);
  return favorites;
}
export function FavoriteBookButton({ index, title, lang }: { index: number; title: string; lang: Lang }) {
  const favorites = useCatalogFavorites();
  const selected = favorites.includes(index);
  const toggle = () => {
    const current = readFavorites();
    const next = current.includes(index) ? current.filter((id) => id !== index) : [...current, index];
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { return; }
    window.dispatchEvent(new Event(EVENT));
  };
  return <button type="button" className="catalog-favorite" aria-pressed={selected} aria-label={`${selected ? COPY[lang].remove : COPY[lang].add}: ${title}`} onClick={toggle}><span aria-hidden="true">{selected ? "♥" : "♡"}</span></button>;
}
export function CatalogFavoritesFilter({ lang, active, onChange }: { lang: Lang; active: boolean; onChange: (value: boolean) => void }) {
  return <div className="catalog-favorites-filter"><div role="group" aria-label={COPY[lang].filter}>
    <button type="button" className="kcat-btn" aria-pressed={!active} onClick={() => onChange(false)}>{COPY[lang].all}</button>
    <button type="button" className="kcat-btn" aria-pressed={active} onClick={() => onChange(true)}>♥ {COPY[lang].filter}</button>
  </div><p>{COPY[lang].saved}</p></div>;
}
export function CatalogFavoritesEmpty({ lang }: { lang: Lang }) {
  return <p className="ksub" role="status">{COPY[lang].empty}</p>;
}
