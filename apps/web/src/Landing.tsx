import { Fragment, useEffect, useRef, useState, type CSSProperties, type KeyboardEvent as RKeyboardEvent, type MouseEvent as RMouseEvent, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { studioEntryHref } from "./Auth";
import { api, getToken } from "./api";
import { readStoredLang, useResolvedLang, type Lang as SiteLang } from "./i18n/lang";
import { SiteBackNav } from "./SiteBackNav";
import logo from "./assets/logo.png";
import "./landing.css";
import "./landing-flip-fold.css";

type LandingSession =
  | { status: "out" }
  | { status: "loading" }
  | { status: "in"; name: string; email: string; isOwner: boolean };

function sessionDisplayName(fullName: string | null | undefined, email: string): string {
  const first = (fullName || "").trim().split(/\s+/)[0];
  if (first) return first;
  const local = email.split("@")[0]?.trim();
  return local || email;
}

export type Lang = SiteLang;

/* ---------------- ícones (SVG, sem emojis) ---------------- */
type IconProps = { className?: string };
const S = 2.2;
const Svg = (p: { className?: string; children: ReactNode; fill?: string }) => (
  <svg className={p.className} viewBox="0 0 24 24" fill={p.fill ?? "none"} stroke={p.fill ? "none" : "currentColor"}
    strokeWidth={S} strokeLinecap="round" strokeLinejoin="round" aria-hidden>{p.children}</svg>
);
const IcBook =({ className }: IconProps) => (<Svg className={className}><path d="M12 6c-2-1.4-4.5-1.6-7-1v12c2.5-.6 5-.4 7 1 2-1.4 4.5-1.6 7-1V5c-2.5-.6-5-.4-7 1z" /><path d="M12 6v13" /></Svg>);
const IcStar = ({ className }: IconProps) => (<svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 2.6l2.7 5.7 6.3.8-4.6 4.3 1.2 6.2L12 16.9 6.4 19.6l1.2-6.2L3 9.1l6.3-.8L12 2.6z" /></svg>);
const IcGift = ({ className }: IconProps) => (<Svg className={className}><rect x="3.5" y="10" width="17" height="10.5" rx="1.6" /><path d="M3 10h18M12 10v10.5" /><path d="M12 10S9 5.5 7 6.5 8.5 10 12 10zM12 10s3-4.5 5-3.5S15.5 10 12 10z" /></Svg>);
const IcHeart = ({ className }: IconProps) => (<Svg className={className}><path d="M12 20s-7-4.4-9-8.5C1.6 8.3 3.3 5.5 6.3 5.5c1.9 0 3 1.1 3.7 2.2.7-1.1 1.8-2.2 3.7-2.2 3 0 4.7 2.8 3.3 6C19 15.6 12 20 12 20z" /></Svg>);
const IcSparkle = ({ className }: IconProps) => (<svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 3l1.6 5L19 9.6l-5 1.6L12 17l-1.6-5.8L5 9.6 10.4 8 12 3z" /></svg>);
const IcArrow = ({ className }: IconProps) => (<svg className={className} viewBox="0 0 40 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M4 12h28M24 4l9 8-9 8" /></svg>);
const IcSun = ({ className }: IconProps) => (<Svg className={className}><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.4M12 19.1v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7" /></Svg>);
const IcMoon = ({ className }: IconProps) => (<Svg className={className}><path d="M20 15A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 11z" /></Svg>);
const IcChevron = ({ className }: IconProps) => (<Svg className={className}><path d="M6 9l6 6 6-6" /></Svg>);
const IcShield = ({ className }: IconProps) => (<Svg className={className}><path d="M12 3l7 2.5V11c0 4.4-3 7.7-7 9-4-1.3-7-4.6-7-9V5.5L12 3z" /><path d="M9.2 12l2 2 3.6-3.8" /></Svg>);
const IcEye = ({ className }: IconProps) => (<Svg className={className}><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="2.6" /></Svg>);
const IcTruck = ({ className }: IconProps) => (<Svg className={className}><path d="M3 6.5h11v9H3zM14 9.5h4l3 3v3h-7z" /><circle cx="7" cy="18" r="1.6" /><circle cx="17.5" cy="18" r="1.6" /></Svg>);
const IcPlay = ({ className }: IconProps) => (<Svg className={className}><rect x="3" y="5.5" width="18" height="13" rx="2.5" /><path d="M10 9.5l4.5 2.5-4.5 2.5z" fill="currentColor" stroke="none" /></Svg>);
const IcMail = ({ className }: IconProps) => (
  <Svg className={className}><rect x="3" y="5.5" width="18" height="13" rx="2" /><path d="M3.5 7.5 12 13l8.5-5.5" /></Svg>
);
const IcInstagram = ({ className }: IconProps) => (
  <Svg className={className}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
    <circle cx="12" cy="12" r="4" />
    <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
  </Svg>
);
const FOOT_ICONS = [IcSparkle, IcBook, IcPlay, IcStar];
const CONTACT_EMAIL = "info@storyrus.ai";
const CONTACT_INSTA = "storyr.us";
const PROMISE_ICONS = [IcShield, IcGift, IcEye, IcTruck];
type CoverFont = "fredoka" | "baloo" | "lilita";
type HeroAsset = Record<Lang, string>;
const heroAsset = (pt: string, en = pt, es = en): HeroAsset => ({ pt, en, es });
/** Hero strip: capa, página aberta, criança lendo. */
const HERO_STRIP: { name: string; cover: HeroAsset; page: HeroAsset; photo: HeroAsset }[] = [
  {
    name: "Meu Pai, Meu Herói",
    cover: heroAsset("capa-meupai-heroi.png"),
    page: heroAsset("pagina-meupai-heroi.png"),
    photo: heroAsset("foto-meupai-heroi.png"),
  },
  {
    name: "Nano",
    cover: heroAsset("capa-nanoaventuras.jpg", "capa-nanoaventuras-en.jpg", "capa-nanoaventuras-es.jpg"),
    page: heroAsset("pagina-nanoaventuras.jpg", "pagina-nanoaventuras-en.jpg", "pagina-nanoaventuras-es.jpg"),
    photo: heroAsset("foto-nanoaventuras.jpg", "foto-nanoaventuras-en.jpg", "foto-nanoaventuras-es.jpg"),
  },
  {
    name: "Amor de Bisavó",
    cover: heroAsset("capa-amordebisavo.jpg", "capa-amordebisavo-en.jpg", "capa-amordebisavo-es.jpg"),
    page: heroAsset("pagina-amordebisavo.jpg", "pagina-amordebisavo-en.jpg", "pagina-amordebisavo-es.jpg"),
    photo: heroAsset("foto-amordebisavo.jpg", "foto-amordebisavo-en.jpg", "foto-amordebisavo-es.jpg"),
  },
  {
    name: "Amor de Mãe",
    cover: heroAsset("capa-amordemae.jpg"),
    page: heroAsset("pagina-amordemae.jpg"),
    photo: heroAsset("foto-amordemae.jpg"),
  },
  {
    name: "Mako",
    cover: heroAsset("capa-mako-amigofiel.jpg", "capa-mako-amigofiel-en.jpg", "capa-mako-amigofiel-es.jpg"),
    page: heroAsset("pagina-mako-amigofiel.jpg", "pagina-mako-amigofiel-en.jpg", "pagina-mako-amigofiel-es.jpg"),
    photo: heroAsset("foto-mako-amigofiel.jpg", "foto-mako-amigofiel-en.jpg", "foto-mako-amigofiel-es.jpg"),
  },
  {
    name: "Facundo",
    cover: heroAsset("capa-facundo-motocross.jpg"),
    page: heroAsset("pagina-facundo-motocross.jpg"),
    photo: heroAsset("foto-facundo-motocross.jpg"),
  },
  {
    name: "Amor de Tia",
    cover: heroAsset("capa-amordetia.png"),
    page: heroAsset("pagina-amordetia.png"),
    photo: heroAsset("foto-amordetia.png"),
  },
  {
    name: "Davi, o Menino Pastor",
    cover: heroAsset("capa-davi-pastor.png"),
    page: heroAsset("pagina-davi-pastor.png"),
    photo: heroAsset("foto-davi-pastor.png"),
  },
  {
    name: "Enzo, Meu Primo Predileto",
    cover: heroAsset("capa-enzo-primo.png"),
    page: heroAsset("pagina-enzo-primo.png"),
    photo: heroAsset("foto-enzo-primo.png"),
  },
  {
    name: "Lucas e seu amigo Max",
    cover: heroAsset("capa-lucas-max.png"),
    page: heroAsset("pagina-lucas-max.png"),
    photo: heroAsset("foto-lucas-max.png"),
  },
  {
    name: "Esther e os Superpoderes da Higiene",
    cover: heroAsset("capa-esther-higiene.png"),
    page: heroAsset("pagina-esther-higiene.png"),
    photo: heroAsset("foto-esther-higiene.png"),
  },
  {
    name: "Meme e Tata",
    cover: heroAsset("capa-natalmemetata.jpg", "capa-natalmemetata-en.jpg", "capa-natalmemetata-es.jpg"),
    page: heroAsset("pagina-natalmemetata.jpg", "pagina-natalmemetata-en.jpg", "pagina-natalmemetata-es.jpg"),
    photo: heroAsset("foto-natalmemetata.jpg", "foto-natalmemetata-en.jpg", "foto-natalmemetata-es.jpg"),
  },
];
/** Livros da /cartoon que têm capa, página ou foto em desenho. Os demais ficam só na principal. */
const CARTOON_HERO: Record<string, { cover?: string; page?: string; photo?: string }> = {
  "Amor de Bisavó": { cover: "cartoon-capa-bisavo.jpg", page: "cartoon-pagina-bisavo.jpg", photo: "cartoon-foto-bisavo.jpg" },
  "Amor de Mãe": { cover: "cartoon-capa-amordemae.jpg", page: "cartoon-pagina-amordemae.jpg", photo: "cartoon-foto-amordemae.jpg" },
  "Davi, o Menino Pastor": { cover: "cartoon-capa-davi.jpg", page: "cartoon-pagina-davi.jpg", photo: "cartoon-foto-davi.jpg" },
  "Enzo, Meu Primo Predileto": { cover: "cartoon-capa-enzo.jpg", page: "cartoon-pagina-enzo.jpg", photo: "cartoon-foto-enzo.jpg" },
};
const CARTOON_COVER: Record<number, string | Record<Lang, string>> = {
  5: "cartoon-capa-nicolas.jpg",
  6: "cartoon-capa-amordemae.jpg",
  7: "cartoon-capa-matteo.jpg",
  8: "cartoon-capa-bisavo.jpg",
  11: "cartoon-capa-maya.jpg",
  12: "cartoon-capa-mako.png",
  19: "cartoon-capa-amordetia.png",
  20: "cartoon-capa-davi.png",
  22: "cartoon-capa-enzo.jpg",
  23: "cartoon-capa-lucas.png",
  30: { pt: "cartoon-capa-avo.png", en: "cartoon-capa-avo-en.png", es: "cartoon-capa-avo-en.png" },
  33: { pt: "cartoon-capa-aventura.png", en: "cartoon-capa-aventura-en.png", es: "cartoon-capa-aventura-es.png" },
};
/** Faixa do /cartoon: cenas diferentes lado a lado, não só família lendo no sofá. */
const CARTOON_REVIEW_PHOTOS = [
  { tab: "cartoon-foto-nicolas.jpg", name: "Nicolas" },
  { tab: "cartoon-foto-davi.jpg", name: "Davi" },
  { tab: "cartoon-foto-maya.jpg", name: "Maya" },
  { tab: "cartoon-foto-enzo.jpg", name: "Enzo" },
  { tab: "cartoon-foto-amordemae.jpg", name: "Amor de Mãe" },
  { tab: "cartoon-foto-natal.jpg", name: "Meme e Tata" },
  { tab: "cartoon-foto-matteo.jpg", name: "Matteo" },
  { tab: "cartoon-foto-bisavo.jpg", name: "Amor de Bisavó" },
] as const;

/* ------- exemplos reais em apps/web/public/exemplos/ ------- */
const HOW_IMGS = ["cartoon-como-dados.jpg", "cartoon-pagina-bisavo.jpg", "cartoon-capa-bisavo.jpg"];
const HOW_SCENE_IMGS = ["como-envia.jpg", "como-cria.jpg", "como-recebe.jpg"];
const PASSO_IMGS = ["dica-boa.png", "personagem-avatar.jpg", "cena-dino-floresta.jpg"];
/** Reviews strip: one lifestyle photo per book (PT/default), never EN/ES duplicates of the same scene. */
const REVIEW_PHOTOS = [
  { tab: "foto-martin-goleiro.jpg", name: "Martin" },
  { tab: "foto-nicolas-maefilho.jpg", name: "Nicolas" },
  { tab: "foto-emilia-bailarina.jpg", name: "Emilia" },
  { tab: "foto-amordemae.jpg", name: "Amor de Mãe" },
  { tab: "foto-antonio-bicicleta.jpg", name: "Antonio" },
  { tab: "foto-mamaepapaimatteo-en.jpg", name: "Matteo" },
  { tab: "foto-mariajesus-hockey.jpg", name: "Maria Jesus" },
  { tab: "foto-amordebisavo.jpg", name: "Amor de Bisavó" },
  { tab: "foto-facundo-motocross.jpg", name: "Facundo" },
  { tab: "foto-natalmemetata.jpg", name: "Meme e Tata" },
  { tab: "foto-ester.png", name: "Ester" },
  { tab: "foto-raquel-papai.png", name: "Raquel" },
  { tab: "foto-rebeca.png", name: "Rebeca" },
  { tab: "foto-maya-cachorra-pt.jpg", name: "Maya" },
  { tab: "foto-abigail.png", name: "Abigail" },
  { tab: "foto-nanoaventuras.jpg", name: "Nano" },
  { tab: "foto-miriam.png", name: "Miriam" },
  { tab: "foto-mako-amigofiel.jpg", name: "Mako" },
  { tab: "foto-noe.png", name: "Noé" },
] as const;
type CatalogImg = string | Record<Lang, string>;
function catalogImgSrc(img: CatalogImg, lang: Lang): string {
  return typeof img === "string" ? img : img[lang];
}
function catalogCoverFile(i: number, lang: Lang, variant: "photo" | "cartoon"): string {
  const cartoon = CARTOON_COVER[i];
  if (variant === "cartoon" && cartoon) return catalogImgSrc(cartoon, lang);
  return catalogImgSrc(CATALOG_IMGS[i], lang);
}
/** Capa que só existe em desenho: fica na /cartoon, fora das listas realistas. */
function isCartoonOnlyCover(i: number): boolean {
  const img = CATALOG_IMGS[i];
  if (!img) return false;
  const names = typeof img === "string" ? [img] : Object.values(img);
  return names.some((name) => name.startsWith("cartoon-"));
}
const CATALOG_IMGS: CatalogImg[] = [
  "capa-martin-goleiro.jpg",
  "capa-emilia-bailarina.jpg",
  "capa-antonio-bicicleta.jpg",
  "capa-sofia-alfabeto.png",
  "capa-cristobal-esporte.png",
  "capa-nicolas-maefilho.png",
  { pt: "capa-amordemae.png", en: "capa-amordemae-en.png", es: "capa-amordemae-es.png" },
  { pt: "capa-mamaepapaimatteo.png", en: "capa-mamaepapaimatteo-en.png", es: "capa-mamaepapaimatteo-es.png" },
  { pt: "capa-amordebisavo.png", en: "capa-amordebisavo-en.png", es: "capa-amordebisavo-es.png" },
  { pt: "capa-natalmemetata.jpg", en: "capa-natalmemetata-en.jpg", es: "capa-natalmemetata-es.jpg" },
  { pt: "capa-nanoaventuras.png", en: "capa-nanoaventuras-en.png", es: "capa-nanoaventuras-es.png" },
  { pt: "capa-maya-cachorra-pt.jpg", en: "capa-maya-cachorra-en.jpg", es: "capa-maya-cachorra-es.jpg" },
  { pt: "capa-mako-amigofiel.jpg", en: "capa-mako-amigofiel-en.jpg", es: "capa-mako-amigofiel-es.jpg" },
  { pt: "capa-ester.png", en: "capa-ester-en.png", es: "capa-ester-es.png" },
  { pt: "capa-raquel-papai.png", en: "capa-raquel-papai-en.png", es: "capa-raquel-papai-es.png" },
  { pt: "capa-rebeca.png", en: "capa-rebeca-en.png", es: "capa-rebeca-es.png" },
  { pt: "capa-abigail.png", en: "capa-abigail-en.png", es: "capa-abigail-es.png" },
  { pt: "capa-miriam.png", en: "capa-miriam-en.png", es: "capa-miriam-es.png" },
  { pt: "capa-noe.png", en: "capa-noe-en.png", es: "capa-noe-es.png" },
  { pt: "capa-amordetia.png", en: "capa-amordetia.png", es: "capa-amordetia.png" },
  { pt: "capa-davi-pastor.png", en: "capa-davi-pastor.png", es: "capa-davi-pastor.png" },
  { pt: "capa-meupai-heroi.png", en: "capa-meupai-heroi.png", es: "capa-meupai-heroi.png" },
  { pt: "capa-enzo-primo.png", en: "capa-enzo-primo.png", es: "capa-enzo-primo.png" },
  { pt: "capa-lucas-max.png", en: "capa-lucas-max.png", es: "capa-lucas-max.png" },
  { pt: "capa-esther-higiene.png", en: "capa-esther-higiene.png", es: "capa-esther-higiene.png" },
  "capa-construtor.png",
  { pt: "capa-heroi-bombeiro.png", en: "capa-heroi-bombeiro-en.png", es: "capa-heroi-bombeiro-es.png" },
  { pt: "capa-heroi-policia.png", en: "capa-heroi-policia-en.png", es: "capa-heroi-policia-es.png" },
  { pt: "capa-heroi-aranha.png", en: "capa-heroi-aranha-en.png", es: "capa-heroi-aranha-es.png" },
  { pt: "capa-tia-especial.png", en: "capa-tia-especial-en.png", es: "capa-tia-especial-es.png" },
  { pt: "capa-amor-de-avo.png", en: "capa-amor-de-avo-en.png", es: "capa-amor-de-avo-en.png" },
  { pt: "capa-pascoa.png", en: "capa-pascoa-en.png", es: "capa-pascoa-es.png" },
  "capa-nossa-familia.png",
  { pt: "cartoon-capa-aventura.png", en: "cartoon-capa-aventura-en.png", es: "cartoon-capa-aventura-es.png" },
  { pt: "capa-bruno-animais.png", en: "capa-bruno-animais-en.png", es: "capa-bruno-animais-es.png" },
  "capa-gael-economia.jpg",
  "capa-mariajesus-hockey.jpg",
];
type CatalogSeriesShot = { cover: CatalogImg; page?: CatalogImg; photo?: CatalogImg };
/** Série capa / página / foto por índice do catálogo (quando existir em /exemplos). */
const CATALOG_SERIES: Record<number, CatalogSeriesShot> = {
  0: { cover: "capa-martin-goleiro.jpg", page: "pagina-martin-goleiro.jpg", photo: "foto-martin-goleiro.jpg" },
  1: { cover: "capa-emilia-bailarina.jpg", page: "pagina-emilia-bailarina.jpg", photo: "foto-emilia-bailarina.jpg" },
  2: { cover: "capa-antonio-bicicleta.jpg", page: "pagina-antonio-bicicleta.jpg", photo: "foto-antonio-bicicleta.jpg" },
  3: { cover: "capa-sofia-alfabeto.png", page: "pagina-sofia-alfabeto.jpg", photo: "foto-sofia.png" },
  4: { cover: "capa-cristobal-esporte.png", page: "pagina-cristobal-esporte.jpg" },
  5: { cover: "capa-nicolas-maefilho.png", page: "pagina-nicolas-maefilho.jpg", photo: "foto-nicolas-maefilho.jpg" },
  6: {
    cover: { pt: "capa-amordemae.png", en: "capa-amordemae-en.png", es: "capa-amordemae-es.png" },
    page: { pt: "pagina-amordemae.jpg", en: "pagina-amordemae-en.jpg", es: "pagina-amordemae-es.jpg" },
    photo: { pt: "foto-amordemae.jpg", en: "foto-amordemae-en.jpg", es: "foto-amordemae-es.jpg" },
  },
  7: {
    cover: { pt: "capa-mamaepapaimatteo.png", en: "capa-mamaepapaimatteo-en.png", es: "capa-mamaepapaimatteo-es.png" },
    page: { pt: "pagina-mamaepapaimatteo.jpg", en: "pagina-mamaepapaimatteo-en.jpg", es: "pagina-mamaepapaimatteo-es.jpg" },
    photo: { pt: "foto-mamaepapaimatteo-en.jpg", en: "foto-mamaepapaimatteo-en.jpg", es: "foto-mamaepapaimatteo-es.jpg" },
  },
  8: {
    cover: { pt: "capa-amordebisavo.png", en: "capa-amordebisavo-en.png", es: "capa-amordebisavo-es.png" },
    page: { pt: "pagina-amordebisavo.jpg", en: "pagina-amordebisavo-en.jpg", es: "pagina-amordebisavo-es.jpg" },
    photo: { pt: "foto-amordebisavo.jpg", en: "foto-amordebisavo-en.jpg", es: "foto-amordebisavo-es.jpg" },
  },
  9: {
    cover: { pt: "capa-natalmemetata.jpg", en: "capa-natalmemetata-en.jpg", es: "capa-natalmemetata-es.jpg" },
    page: { pt: "pagina-natalmemetata.jpg", en: "pagina-natalmemetata-en.jpg", es: "pagina-natalmemetata-es.jpg" },
    photo: { pt: "foto-natalmemetata.jpg", en: "foto-natalmemetata-en.jpg", es: "foto-natalmemetata-es.jpg" },
  },
  10: {
    cover: { pt: "capa-nanoaventuras.png", en: "capa-nanoaventuras-en.png", es: "capa-nanoaventuras-es.png" },
    page: { pt: "pagina-nanoaventuras.jpg", en: "pagina-nanoaventuras-en.jpg", es: "pagina-nanoaventuras-es.jpg" },
    photo: { pt: "foto-nanoaventuras.jpg", en: "foto-nanoaventuras-en.jpg", es: "foto-nanoaventuras-es.jpg" },
  },
  11: {
    cover: { pt: "capa-maya-cachorra-pt.jpg", en: "capa-maya-cachorra-en.jpg", es: "capa-maya-cachorra-es.jpg" },
    page: { pt: "pagina-maya-cachorra-pt.jpg", en: "pagina-maya-cachorra-en.jpg", es: "pagina-maya-cachorra-es.jpg" },
    photo: { pt: "foto-maya-cachorra-pt.jpg", en: "foto-maya-cachorra-en.jpg", es: "foto-maya-cachorra-es.jpg" },
  },
  12: {
    cover: { pt: "capa-mako-amigofiel.jpg", en: "capa-mako-amigofiel-en.jpg", es: "capa-mako-amigofiel-es.jpg" },
    page: { pt: "pagina-mako-amigofiel.jpg", en: "pagina-mako-amigofiel-en.jpg", es: "pagina-mako-amigofiel-es.jpg" },
    photo: { pt: "foto-mako-amigofiel.jpg", en: "foto-mako-amigofiel-en.jpg", es: "foto-mako-amigofiel-es.jpg" },
  },
  13: { cover: { pt: "capa-ester.png", en: "capa-ester-en.png", es: "capa-ester-es.png" }, photo: "foto-ester.png" },
  14: { cover: { pt: "capa-raquel-papai.png", en: "capa-raquel-papai-en.png", es: "capa-raquel-papai-es.png" }, photo: "foto-raquel-papai.png" },
  15: { cover: { pt: "capa-rebeca.png", en: "capa-rebeca-en.png", es: "capa-rebeca-es.png" }, photo: "foto-rebeca.png" },
  16: { cover: { pt: "capa-abigail.png", en: "capa-abigail-en.png", es: "capa-abigail-es.png" }, photo: "foto-abigail.png" },
  17: { cover: { pt: "capa-miriam.png", en: "capa-miriam-en.png", es: "capa-miriam-es.png" }, photo: "foto-miriam.png" },
  18: { cover: { pt: "capa-noe.png", en: "capa-noe-en.png", es: "capa-noe-es.png" }, photo: "foto-noe.png" },
  19: { cover: "capa-amordetia.png", page: "pagina-amordetia.png", photo: "foto-amordetia.png" },
  20: { cover: "capa-davi-pastor.png", page: "pagina-davi-pastor.png", photo: "foto-davi-pastor.png" },
  21: { cover: "capa-meupai-heroi.png", page: "pagina-meupai-heroi.png", photo: "foto-meupai-heroi.png" },
  22: { cover: "capa-enzo-primo.png", page: "pagina-enzo-primo.png", photo: "foto-enzo-primo.png" },
  23: { cover: "capa-lucas-max.png", page: "pagina-lucas-max.png", photo: "foto-lucas-max.png" },
  24: { cover: "capa-esther-higiene.png", page: "pagina-esther-higiene.png", photo: "foto-esther-higiene.png" },
  30: { cover: { pt: "capa-amor-de-avo.png", en: "capa-amor-de-avo-en.png", es: "capa-amor-de-avo-en.png" } },
  34: {
    cover: { pt: "capa-bruno-animais.png", en: "capa-bruno-animais-en.png", es: "capa-bruno-animais-es.png" },
    page: "pagina-bruno-animais.jpg",
  },
  36: { cover: "capa-mariajesus-hockey.jpg", page: "pagina-mariajesus-hockey.jpg" },
};
type CatalogSeriesKind = "cover" | "page" | "photo";
function catalogSeriesShots(i: number, lang: Lang): { key: CatalogSeriesKind; src: string }[] {
  const series = CATALOG_SERIES[i];
  if (!series) {
    const cover = catalogCoverFile(i, lang, "photo");
    return cover ? [{ key: "cover", src: cover }] : [];
  }
  const shots: { key: CatalogSeriesKind; src: string }[] = [
    { key: "cover", src: catalogImgSrc(series.cover, lang) },
  ];
  if (series.page) shots.push({ key: "page", src: catalogImgSrc(series.page, lang) });
  if (series.photo) shots.push({ key: "photo", src: catalogImgSrc(series.photo, lang) });
  return shots;
}
const CATALOG_THEMES = [
  "sport",
  "princess",
  "adventure",
  "alfabetizacao_inicial",
  "sport",
  "mothers_day",
  "mothers_day",
  "family_love",
  "grandparents_love",
  "christmas",
  "adventure",
  "pets",
  "pets",
  "birthday",
  "fathers_day",
  "superhero",
  "space",
  "underwater",
  "dinosaurs",
  "family_love",
  "biblico",
  "fathers_day",
  "family_love",
  "pets",
  "higiene_desfralde",
  "adventure",
  "superhero",
  "superhero",
  "pets",
  "family_love",
  "grandfather_love",
  "easter",
  "family_love",
  "adventure",
  "animais_sons",
  "economia",
  "sport",
];
/** Janela da vitrine. Era 15; desceu 1 quando o Bruno saiu do meio da lista. */
const CATALOG_LIMIT = 14;
/** Índices fora do catálogo realista: capas em desenho e o aniversário da Ester. */
const CATALOG_CARTOON_INDEXES = new Set([1, 2, 3, 4, 13, 33]);
/** Livros novos em português, depois do limite dos 15 primeiros. */
const CATALOG_NEW_INDEXES = new Set([19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 34, 35, 36]);
/** Primeiros da vitrine: livros novos, depois Meu Pai, Davi, Enzo e o Martin. */
const CATALOG_LEAD = [25, 26, 27, 28, 29, 30, 21, 20, 22, 31, 0, 33];
type CatalogCoverChoice = "soft" | "hard";
type CatalogSizeChoice = "M" | "P";
function catalogCoverChoice(cover?: string): CatalogCoverChoice {
  return cover === "Hard" ? "hard" : "soft";
}
function catalogSizeChoice(size?: string): CatalogSizeChoice {
  return size === "P" ? "P" : "M";
}
const VIDEO_IMGS = ["capa-meupai-heroi.png", "flor-2.jpg", "dino-2.jpg"];
const VIDEO_SRCS: (string | null)[] = [
  "video-meupai-heroi-kling.mp4",
  "video-flor.mp4",
  "video-dino.mp4",
];
const FEELING_THEMES = new Set(["literacia_emocional", "rotina_dormir", "compartilhar_revezar", "consciencia_corporal"]);
const CATALOG_SECTION_THEMES: Record<string, readonly string[]> = {
  aventuras: ["adventure", "princess", "sport", "dinosaurs", "underwater", "space", "superhero"],
  "voce-e-eu": ["mothers_day", "fathers_day", "grandparents_love", "grandfather_love", "family_love", "recem_nascidos", "casamento", "pets"],
  ocasioes: ["christmas", "birthday", "mothers_day", "fathers_day", "grandparents_love", "easter"],
  educativo: ["animais_sons", "higiene_desfralde", "biblico", "economia"],
};
const NAV_CAT_META = [
  {
    id: "aventuras",
    color: "#7aa2ff",
    subs: [
      { href: "/app?tema=adventure" },
      { href: "/app?tema=dinosaurs" },
      { href: "/app?tema=underwater" },
      { href: "/app?tema=space" },
      { href: "/app?tema=princess" },
      { href: "/app?tema=superhero" },
      { href: "/app?tema=sport" },
    ],
    feats: [
      { href: "/app?tema=princess", catalogI: 1 },
      { href: "/app?tema=adventure", catalogI: 25 },
      { href: "/app?tema=sport", catalogI: 4 },
      { href: "/app?tema=adventure", catalogI: 10 },
    ],
  },
  {
    id: "voce-e-eu",
    color: "#b48ad4",
    subs: [
      { href: "/app?tema=mothers_day" },
      { href: "/app?tema=fathers_day" },
      { href: "/app?tema=grandparents_love" },
      { href: "/app?tema=grandfather_love" },
      { href: "/app?tema=family_love" },
      { href: "/app" },
      { href: "/app?tema=recem_nascidos" },
      { href: "/app?tema=casamento" },
      { href: "/app?tema=pets" },
    ],
    feats: [
      { href: "/app?tema=mothers_day", catalogI: 5 },
      { href: "/app?tema=grandparents_love", catalogI: 8 },
      { href: "/app?tema=family_love", catalogI: 7 },
      { href: "/app?tema=mothers_day", catalogI: 6 },
    ],
  },
  {
    id: "ocasioes",
    color: "#f0b429",
    subs: [
      { href: "/app?tema=dia_da_mulher", when: { month: 3, day: 8 } },
      { href: "/app?tema=dia_da_sogra", when: { month: 3, day: 26 } },
      { href: "/app?tema=easter", when: "easter" },
      { href: "/app?tema=mothers_day", when: { month: 5, day: 10 } },
      { href: "/app?tema=dia_da_familia", when: { month: 5, day: 15 } },
      { href: "/app?tema=dia_do_irmao", when: { month: 5, day: 30 } },
      { href: "/app?tema=dia_dos_namorados", when: { month: 6, day: 12 } },
      { href: "/app?tema=dia_do_amigo", when: { month: 7, day: 20 } },
      { href: "/app?tema=grandparents_love", when: { month: 7, day: 26 } },
      { href: "/app?tema=tio_tia", when: { month: 7, day: 26 } },
      { href: "/app?tema=fathers_day", when: { month: 8, day: 9 } },
      { href: "/app?tema=dia_dos_filhos", when: { month: 8, day: 11 } },
      { href: "/app?tema=independencia", when: { month: 9, day: 7 } },
      { href: "/app?tema=dia_do_idoso", when: { month: 10, day: 1 } },
      { href: "/app?tema=pets", when: { month: 10, day: 4 } },
      { href: "/app?tema=childrens_day", when: { month: 10, day: 12 } },
      { href: "/app?tema=christmas", when: { month: 12, day: 25 } },
      { href: "/app?tema=birthday" },
    ],
    feats: [
      { href: "/app?tema=christmas", catalogI: 9 },
      { href: "/app?tema=mothers_day", catalogI: 5 },
      { href: "/app?tema=grandparents_love", catalogI: 8 },
      { href: "/app?tema=fathers_day", catalogI: 21 },
    ],
  },
  {
    id: "educativo",
    color: "#5ec4a8",
    subs: [
      { href: "/app?tema=biblico" },
      { href: "/app?tema=cores" },
      { href: "/app?tema=higiene_desfralde" },
      { href: "/app?tema=animais_sons" },
      { href: "/app?tema=literacia_emocional" },
      { href: "/app?tema=rotina_dormir" },
      { href: "/app?tema=compartilhar_revezar" },
      { href: "/app?tema=consciencia_corporal" },
      { href: "/app?tema=economia" },
    ],
    feats: [
      { href: "/app?tema=animais_sons", catalogI: 23 },
      { href: "/app?tema=higiene_desfralde", catalogI: 24 },
      { href: "/app?tema=biblico", catalogI: 20 },
    ],
  },
] as const;
/** Livros reais de cada tema do menu. O painel troca esta lista ao passar o mouse no subtema. */
const MENU_BOOKS: Record<string, readonly number[]> = {
  adventure: [33, 2, 10, 25],
  dinosaurs: [18],
  underwater: [17],
  space: [16],
  princess: [1],
  superhero: [15, 26, 27],
  sport: [0, 4, 36],
  mothers_day: [5, 6],
  fathers_day: [21, 14],
  grandparents_love: [8],
  grandfather_love: [30],
  dia_do_idoso: [8, 30],
  family_love: [7, 29],
  pets: [11, 12, 23, 28],
  dia_da_mulher: [6, 5, 8, 19],
  dia_da_familia: [7, 19, 21],
  tio_tia: [19, 29],
  christmas: [9],
  easter: [31],
  animais_sons: [34],
  economia: [35],
  higiene_desfralde: [24],
  biblico: [20],
};
function catalogSectionId(theme: string | null | undefined): string {
  if (!theme) return "aventuras";
  for (const [id, themes] of Object.entries(CATALOG_SECTION_THEMES)) {
    if ((themes as readonly string[]).includes(theme)) return id;
  }
  return "aventuras";
}
function themeFromHref(href: string): string | null {
  // Links podem ser /app?tema=… ou /cadastro?next=%2Fapp%3Ftema%3D…
  let target = href;
  try {
    const next = new URL(href, "https://storyrus.local").searchParams.get("next");
    if (next && next.startsWith("/")) target = next;
  } catch {
    /* ignore */
  }
  const match = target.match(/[?&]tema=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
type OccasionWhen = { month: number; day: number } | "easter";
function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
function easterSunday(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}
export function nextOccasionDate(when: OccasionWhen, today: Date): Date {
  const start = startOfDay(today);
  if (when === "easter") {
    const thisYear = easterSunday(start.getFullYear());
    return thisYear >= start ? thisYear : easterSunday(start.getFullYear() + 1);
  }
  const next = new Date(start.getFullYear(), when.month - 1, when.day);
  return next >= start ? next : new Date(start.getFullYear() + 1, when.month - 1, when.day);
}
/** A data entra no menu só se a próxima ocorrência ainda é neste ano. */
export function occasionDue(when: OccasionWhen, today: Date): boolean {
  const start = startOfDay(today);
  return nextOccasionDate(when, start).getFullYear() === start.getFullYear();
}
function SubLabel({ label }: { label: string }) {
  const [name, date] = label.split(" · ");
  if (!date) return label;
  return (
    <>
      <span className="kcat-sub-name">{name}</span>
      <span className="kcat-sub-date">{date}</span>
    </>
  );
}
/** Nome da criança no exemplo, para o estúdio trocar pelo nome que a família digitar. */
const HERO_BY_CATALOG: Record<number, string> = {
  0: "Martin",
  1: "Emilia",
  2: "Antonio",
  3: "Sofia",
  4: "Cristobal",
  5: "Nicolas",
  7: "Matteo",
  10: "Nano",
  11: "Maya",
  12: "Mako",
  23: "Lucas",
  13: "Ester",
  14: "Raquel",
  15: "Rebeca",
  16: "Abigail",
  17: "Miriam",
  18: "Noé",
  20: "Davi",
};
function personalizeHref(opts: {
  theme: string;
  title: string;
  historia?: string;
  heroi?: string;
  size: "M" | "P";
  cover: "soft" | "hard";
  modo: "realista" | "cartoon";
  catalogI?: number;
}) {
  const q = new URLSearchParams();
  q.set("tema", opts.theme);
  q.set("campos", "nome");
  q.set("titulo", opts.title);
  if (opts.historia) q.set("historia", opts.historia);
  if (opts.heroi) q.set("heroi", opts.heroi);
  q.set("tamanho", opts.size);
  q.set("capa", opts.cover);
  q.set("modo", opts.modo);
  return studioEntryHref(`/app?${q.toString()}`);
}
const exUrl = (f: string) => (f.startsWith("http://") || f.startsWith("https://") ? f : `${import.meta.env.BASE_URL}exemplos/${f}`);

/** Vídeo de exemplo: carrega e toca só quando entra na tela. */
function AutoMutedVideo({ src, poster }: { src: string; poster: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [activeSrc, setActiveSrc] = useState<string | undefined>(undefined);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.muted = true;
    el.defaultMuted = true;
    const tryPlay = () => {
      el.muted = true;
      void el.play().catch(() => { /* autoplay bloqueado até interação */ });
    };
    const io = new IntersectionObserver(
      (entries) => {
        for (const en of entries) {
          if (en.isIntersecting) {
            setActiveSrc(src);
            tryPlay();
          } else {
            el.pause();
          }
        }
      },
      { threshold: 0.25 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [src]);
  useEffect(() => {
    const el = ref.current;
    if (!el || !activeSrc) return;
    el.muted = true;
    void el.play().catch(() => { /* autoplay bloqueado até interação */ });
  }, [activeSrc]);
  return (
    <video
      ref={ref}
      poster={poster}
      controls
      muted
      playsInline
      preload="metadata"
      loop
    >
      {activeSrc ? <source src={activeSrc} type="video/mp4" /> : null}
    </video>
  );
}

function Faq({ items }: { items: readonly { q: string; a: string }[] }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="faq">
      {items.map((it, i) => {
        const qid = `faq-q-${i}`;
        const aid = `faq-a-${i}`;
        return (
        <div className={`faq-item${open === i ? " open" : ""}`} key={it.q}>
          <button
            type="button"
            className="faq-q"
            id={qid}
            onClick={() => setOpen(open === i ? null : i)}
            aria-expanded={open === i}
            aria-controls={aid}
          >
            <span>{it.q}</span><IcChevron className="faq-chev" />
          </button>
          <div className="faq-a" id={aid} role="region" aria-labelledby={qid} aria-hidden={open !== i}>
            <div className="faq-a-inner">
              <p>{it.a}</p>
            </div>
          </div>
        </div>
        );
      })}
    </div>
  );
}

const I18N = {
  pt: {
    nav: ["Como Funciona", "Livros", "Vídeos", "FAQ"],
    reviews_link: "Avaliações",
    videos_link: "Vídeos",
    my_books: "Meus Livros",
    see_all_books: "Ver Todos Os Livros",
    view_all: "Ver Todos",
    cat_empty: "Ainda não temos um exemplo neste tema.",
    cats_label: "Livros",
    realistic_link: "Realista",
    cartoon_link: "Livros Cartoon",
    quick_links: "Acessos Rápidos",
    font_label: "Fonte Do Título",
    explore: "Explorar Agora",
    eyebrow: "Eternize Momentos. Presenteie Familiares Com Uma História Inesquecível.",
    h_pre: "Transforme uma foto em uma ", w1: "história inesquecível", c1: ", onde seu filho é o ", w2: "protagonista", h_suf: " !",
    lead: "Você envia a foto e nós transformamos seu filho em um personagem ilustrado, criando uma aventura personalizada especialmente para ele — um livro para presentear a família e guardar para sempre.",
    cta_login: "Entrar",
    cta_play: "Criar Conta",
    account: "Minha Conta",
    logout: "Sair",
    orders: "Meus Pedidos",
    users: "Usuários",
    hero_cta: "Criar Meu Livro",
    cta_story: "Criar Minha História",
    hero_sign: "Uma foto. Uma história. Uma memória eterna.",
    book_carousel: "Carrossel De Livros",
    cats: [
      {
        name: "Temáticas",
        subs: ["Aventura", "Dinossauros", "Fundo do Mar", "Espaço", "Princesas", "Super-heróis", "Esportes"],
        feats: ["Princesas", "Aventura", "Cristobal E Seu Esporte Favorito", "Nano E Suas Aventuras"],
      },
      {
        name: "Você e Eu",
        subs: ["Mamãe e Eu", "Papai e Eu", "Vovó e Eu", "Vovô e Eu", "Nossa Família", "Irmãos e Primos", "Recém-nascidos", "Casamento", "Pets"],
        feats: ["Mamãe e Eu", "Vovó e Eu", "Nossa Família", "O Amor de Mãe"],
      },
      {
        name: "Ocasiões Especiais",
        subs: [
          "Dia Internacional da Mulher · 8 de março",
          "Dia da Sogra · 26 de março",
          "Páscoa",
          "Dia das Mães · 10 de maio",
          "Dia Internacional da Família · 15 de maio",
          "Dia do Irmão · 30 de maio",
          "Dia dos Namorados · 12 de junho",
          "Dia do Amigo · 20 de julho",
          "Dia dos Avós · 26 de julho",
          "Dia do Tio e da Tia · 26 de julho",
          "Dia dos Pais · 9 de agosto",
          "Dia dos Filhos · 11 de agosto",
          "Independência do Brasil · 7 de setembro",
          "Dia Internacional do Idoso · 1 de outubro",
          "Dia dos Animais · 4 de outubro",
          "Dia das Crianças · 12 de outubro",
          "Natal · 25 de dezembro",
          "Aniversário",
        ],
        feats: ["Natal", "Dia das Mães", "Dia dos Avós", "Dia dos Pais"],
      },
      {
        name: "Educativo",
        subs: ["Bíblico", "Cores", "Higiene", "Animais", "Sentimentos", "Hora de Dormir", "Compartilhar", "Corpo", "Economia"],
        feats: ["Animais", "Higiene", "Davi, O Menino Pastor"],
      },
    ],
    cat_below: "Eternize Momentos. Presenteie Familiares Com Uma História Inesquecível.",
    cat_below_lead: "Transforme uma foto em um livro personalizado, onde seu filho é o protagonista.",
    trust: "Encantando Famílias Do Início Ao Fim",
    ba_before: "ANTES", ba_after: "DEPOIS", ba_caption: "Você envia a foto. A gente cria o encanto.",
    ba_preview: "PRÉ-VISUALIZAÇÃO",
    ba_title: "Antes E Depois De Verdade",
    ba_sub: "Fotos reais transformadas em personagens ilustrados.",
    ba_pairs: ["Do berço para a aventura", "Uma menina cheia de imaginação", "Sorriso que vira personagem", "Da foto ao herói da história", "Todo mundo pode ser protagonista"],
    hiw_title: "Como Funciona", hiw_sub: "Você manda as fotos. A gente faz o livro, com seu filho como personagem.",
    hiw: [
      { t: "Envie As Fotos", p: "Da criança e de quem entra na história." },
      { t: "A Gente Cria O Livro", p: "Um personagem parecido com a foto e uma história só de vocês." },
      { t: "O Livro Fica Pronto", p: "Páginas ilustradas para ler e guardar." },
    ],
    hiw_main: [
      { t: "Preencha os Dados", p: "Envie as informações, escolha o tema da história e envie fotos nítidas relacionadas à história que deseja criar." },
      { t: "Acompanhe a Criação", p: "Criamos o personagem ilustrado com base nas fotos enviadas. Desenvolvemos uma história única e envolvente. Você confere e aprova antes de avançarmos." },
      { t: "Revise e Aprove", p: "Revise a prévia, capa e páginas para aprovação. Após sua confirmação, o livro é enviado para produção." },
    ],
    passo_title: "Passo a Passo",
    passo: [
      { t: "Envie Foto do Protagonista", p: "Envie fotos nítidas do personagem, protagonista da sua história. Essas imagens servem de referência para preservar rostos, cabelos, olhos e características da criança, de familiares, animais ou outros personagens." },
      { t: "Envie Fotos do Personagem Adicional", p: "Adicione fotos de um ou mais personagens relacionadas à história que deseja criar." },
      { t: "Revise e Aprove", p: "Revise a prévia, capa e páginas para aprovação. Após sua confirmação, o livro é enviado para produção." },
    ],
    hiw_foot: [
      { t: "Envie a Foto e Defina os Detalhes", p: "Escolha o tema e o formato do livro." },
      { t: "Criamos o Personagem e a História", p: "História, capa e páginas com o mesmo rosto da criança." },
      { t: "Você Recebe e Aprova o Livro", p: "Veja a prévia, aprove e receba o livro impresso." },
    ],
    shot_sub: "Envie a foto e defina os detalhes.",
    shots: [
      { t: "A Criança", p: "3 a 5 fotos de frente, bem iluminadas, com o rosto inteiro. Sem filtro, chapéu ou óculos." },
      { t: "Família E Pets", p: "2 ou 3 fotos de cada pessoa, sozinha. Do pet, uma de frente e outra de corpo inteiro." },
      { t: "Dados Do Livro", p: "Nome, idade, tema e idioma: português, espanhol ou inglês." },
    ],
    shot_title: "Dicas Para A Foto Perfeita",
    cartoon_shot_sub: "Envie uma foto nítida da criança, com o rosto centralizado.",
    cartoon_shots: ["Nítida, bem iluminada e centralizada", "Mais de uma pessoa na foto", "Rosto de lado"],
    cartoon_hiw_title: "Você Envia A Foto",
    cartoon_hiw_photo: "Uma foto da criança já basta para começar.",
    hero_books: [
      "Martin, O Grande Goleiro Do Chile",
      "Emilia E Os Primeiros Passos Da Bailarina",
      "Antonio E Sua Bicicleta",
      "Maria Jesus E A Disciplina No Hockey",
      "Facundo E O Motocross Com Cuidado",
    ],
    vid_title: "Vídeos", vid_sub: "A mesma história ganha voz, trilha e movimento — perfeita para assistir em família.",
    vid_dur: "~2 min", vid_cta: "Criar Meu Vídeo",
    videos: [
      { t: "Meu Pai, Meu Herói", p: "Papai e o bebê lado a lado — cada página ganha movimento suave." },
      { t: "Sofia e a Floresta Encantada", p: "Bichinhos gentis e luzes de vaga-lume, com trilha suave." },
      { t: "Matteo e o Mundo dos Dinossauros", p: "Uma viagem ao vale dos dinossauros, com voz e trilha." },
    ],
    vid_soon: "Em Breve",
    book_badge: "Exemplo Real",
    story_title: "Folheie Nossos Livros",
    story_sub: "Livros criados pela plataforma a partir de uma única foto — escolha um exemplo.",
    story_hint: "Clique nas laterais do livro (ou use as setas) para virar as páginas.",
    chloe_title: "A História de Chloe",
    fmt_title: "Escolha O Formato", fmt_sub: "Do mesmo personagem, três formas de guardar a história.",
    formats: [
      { t: "Livro Em PDF", p: "Capa e páginas ilustradas, prontas na plataforma. O impresso é sob consulta.", feats: ["Capa + páginas ilustradas", "PDF na hora", "Personagem fiel à foto"], cta: "Criar Meu Livro", badge: "Mais Amado" },
      { t: "Vídeo Narrado", p: "A história ganha voz e trilha, perfeita para assistir em família.", feats: ["Narração encantadora", "Cenas ilustradas", "Fácil de compartilhar"], cta: "Criar Meu Vídeo", badge: "" },
      { t: "Animação", p: "O personagem ganha vida numa animação curta.", feats: ["Movimento e magia", "Baseada na sua história", "Um presente diferente"], cta: "Criar Animação", badge: "" },
    ],
    cat_title: "Nossos Livros", cat_sub: "Cada tema se transforma em uma história ilustrada, com seu filho como protagonista da própria história.",
    personalize: "Personalizar",
    a11y_theme: "Alternar tema claro/escuro",
    a11y_menu: "Menu",
    a11y_slide: "Slide",
    photo_real_alt: "Foto De Exemplo Da Criança",
    fb_prev: "Página Anterior",
    fb_next: "Próxima Página",
    fb_turn: "Virar Página",
    fb_cover: "Capa",
    fb_photo: "Na Mão",
    theme_to_light: "Claro",
    theme_to_dark: "Escuro",
    privacy_link: "Privacidade",
    terms_link: "Termos",
    catalog: [
      { t: "Martin, O Grande Goleiro Do Chile", p: "Goleiro que cai, levanta e defende: coragem e perseverança no campo.", cover: "Hard", size: "M", tag: "Esporte e coragem", quote: "Cair, levantar e continuar!" },
      { t: "Emilia E Os Primeiros Passos Da Bailarina", p: "Primeiros passos no ballet com disciplina, equilíbrio e confiança.", cover: "Soft", size: "M", tag: "Ballet e sonhos", quote: "Pequenos passos, grandes conquistas." },
      { t: "Antonio E Sua Bicicleta", p: "Pedalar, aprender e explorar o mundo em pequenas aventuras.", cover: "Soft", size: "M", tag: "Aventura e movimento", quote: "Pedalar, aprender e sorrir!" },
      { t: "Aprendendo O Alfabeto Com A Sofia", p: "Letras e descobertas na floresta, alfabetizar brincando.", cover: "Soft", size: "M", tag: "Alfabetizar brincando", quote: "Cada letra abre um mundo novo." },
      { t: "Cristobal E Seu Esporte Favorito", p: "No caiaque, equilíbrio, coragem e respeito pelo rio.", cover: "Hard", size: "M", tag: "Esporte e coragem", quote: "Pequenas remadas, grandes conquistas." },
      { t: "Nicolas, Meu Primeiro Amor", p: "Um momento de carinho eterno entre mamãe e filho, cheio de ternura para guardar para sempre.", cover: "Soft", size: "M", tag: "Amor de mãe", quote: "Primeiro filho, eterno amor!" },
      { t: "O Amor De Mãe", p: "Pequenas histórias de um grande amor: a ternura da mamãe em cada página, para guardar para sempre.", cover: "Hard", size: "M", tag: "Amor de mãe", quote: "No colo da mamãe, encontro meu lugar." },
      { t: "Mamãe, Papai E Matteo", p: "Uma celebração da família: o carinho de mamãe e papai unidos em uma história só deles.", cover: "Hard", size: "M", tag: "Amor de família", quote: "Juntos, fazemos do amor o nosso lar." },
      { t: "Amor De Bisavó", p: "Uma homenagem à bisavó: colo, carinho e histórias que atravessam gerações, para guardar para sempre.", cover: "Hard", size: "M", tag: "Amor entre gerações", quote: "Bisavó tem abraço que acolhe e guarda todo o meu carinho." },
      { t: "Natal Com A Meme E O Tata", p: "Um Natal em família: o carinho da Meme e do Tata, luzes na árvore e um abraço apertado para guardar para sempre.", cover: "Hard", size: "M", tag: "Natal em família", quote: "Natal é mais gostoso ao lado de quem a gente ama." },
      { t: "Nano E Suas Aventuras", p: "Uma aventura marítima só dele: vento nas orelhas, mar azul e a alegria de explorar ao lado de quem ama, para guardar para sempre.", cover: "Hard", size: "M", tag: "Aventura e mar", quote: "Vento nas orelhas, mar pela frente — a aventura começou!" },
      { t: "Maya, Minha Cachorra Carinhosa", p: "Uma amizade cheia de carinho entre uma menina e sua cadela: cuidado, afeto e companhia em cada página.", cover: "Soft", size: "M", tag: "Amizade e cuidado", quote: "Amor e cuidado, todos os dias." },
      { t: "Mako, Meu Amigo Fiel", p: "Um bebê e seu cão fiel: lealdade, proteção e carinho em uma amizade só deles.", cover: "Soft", size: "M", tag: "Amizade e lealdade", quote: "Amor fiel, todos os dias." },
      { t: "O Aniversário Especial De Ester", p: "Velas, abraços e um pedido no coração: o aniversário do seu filho vira uma história só dele.", cover: "Hard", size: "M", tag: "Aniversário", quote: "Mais um ano de felicidade!" },
      { t: "Raquel E Papai: Aventuras Para Sempre", p: "Mão na mão com o papai, cada caminho vira memória — uma aventura para guardar para sempre.", cover: "Hard", size: "M", tag: "Papai e eu", quote: "Juntos, a aventura nunca acaba." },
      { t: "Rebeca, A Pequena Grande Heroína", p: "Capa ao vento e coragem no peito: o seu filho salva o dia com o coração.", cover: "Hard", size: "M", tag: "Super-heróis", quote: "Ser herói começa com um sorriso." },
      { t: "Abigail Em Uma Aventura Pelo Espaço", p: "Foguetes, planetas e curiosidade: uma viagem estelar com o seu filho no comando.", cover: "Hard", size: "M", tag: "Espaço", quote: "Coragem, curiosidade e descobertas!" },
      { t: "Miriam E Os Segredos Do Fundo Do Mar", p: "Tartarugas, corais e amizade: o seu filho explora o oceano com cuidado e encanto.", cover: "Hard", size: "M", tag: "Fundo do Mar", quote: "Cuidar do mar é cuidar dos amigos." },
      { t: "Noé Na Terra Dos Dinossauros", p: "Fósseis, amigos gigantes e coragem: uma expedição pré-histórica com o seu filho.", cover: "Hard", size: "M", tag: "Dinossauros", quote: "Descobrir juntos é a melhor aventura." },
      { t: "Amor De Tia", p: "O carinho da tia em cada página: colo, riso e um amor que a família guarda para sempre.", cover: "Hard", size: "M", tag: "Amor de tia", quote: "Tia é abraço que não acaba." },
      { t: "Davi, O Menino Pastor", p: "Um menino, sua harpa e as ovelhas: coragem e fé numa história para guardar para sempre.", cover: "Hard", size: "M", tag: "Fé e coragem", quote: "Pequeno no campo, grande no coração." },
      { t: "Meu Pai, Meu Herói", p: "Papai e o bebê, lado a lado: proteção, carinho e um herói só da família.", cover: "Hard", size: "M", tag: "Papai herói", quote: "Meu herói tem o colo do papai." },
      { t: "Enzo, Meu Primo Predileto", p: "Dois primos, um abraço e o mar: amizade que a família nos dá, para guardar para sempre.", cover: "Hard", size: "M", tag: "Amor de primo", quote: "Primo é amigo que a família nos dá." },
      { t: "Lucas E Seu Amigo Max", p: "Um menino e seu cachorro: cuidado, passeio e uma amizade para guardar para sempre.", cover: "Hard", size: "M", tag: "Amigo fiel", quote: "Max é o amigo de todas as horas." },
      { t: "Esther E Os Superpoderes Da Higiene", p: "Mãos limpas, dentes escovados e um sorriso: hábitos de higiene que viram superpoderes.", cover: "Hard", size: "M", tag: "Higiene", quote: "Cuidar de si é um superpoder." },
      { t: "Pequeno Construtor, Grande Empreendedor", p: "Capacete, blocos e um plano no papel: construir, tentar de novo e ver a ideia ficar de pé.", cover: "Hard", size: "M", tag: "Construir e criar", quote: "Pequenas mãos, grandes ideias." },
      { t: "Meu Herói Favorito, O Bombeiro", p: "Sirene, coragem e um herói de verdade: o bombeiro que cuida da cidade e da família.", cover: "Hard", size: "M", tag: "Heróis de verdade", quote: "Meu herói protege todo mundo." },
      { t: "Meu Herói Favorito, O Policial", p: "Farda, cuidado e um herói da cidade: o policial que protege quem a gente ama.", cover: "Hard", size: "M", tag: "Heróis de verdade", quote: "Meu herói cuida da gente todos os dias." },
      { t: "Meu Herói Favorito, A Aranha", p: "Uma teia no jardim e uma amizade miúda: descobrir a natureza com cuidado e encanto.", cover: "Hard", size: "M", tag: "Natureza e amizade", quote: "Até o menor amigo pode ser um herói." },
      { t: "Tia Especial, Não Existe Igual", p: "Passeio, colo e risada: a tia que transforma qualquer dia numa memória para guardar.", cover: "Hard", size: "M", tag: "Amor de tia", quote: "Com a tia, todo dia vira passeio." },
      { t: "Amor De Avô, Meu Porto Seguro", p: "O colo do avô, o lago e um abraço que não acaba: um porto seguro só da família.", cover: "Hard", size: "M", tag: "Amor de avô", quote: "No colo do avô, encontro meu porto seguro." },
      { t: "Feliz Páscoa", p: "Ovos, flores e um coelhinho no jardim: a Páscoa da criança vira uma história para guardar.", cover: "Hard", size: "M", tag: "Páscoa", quote: "Páscoa é alegria para compartilhar." },
      { t: "Nossa Família", p: "Avós, pais e crianças juntos no gramado: o carinho de toda a família numa história só deles.", cover: "Hard", size: "M", tag: "Nossa família", quote: "Juntos, a família é o nosso lugar." },
      { t: "Minha Grande Aventura", p: "Um menino, seu cachorro e um castelo no horizonte: cada passo da trilha ensina a ver, ouvir e cuidar.", cover: "Hard", size: "M", tag: "Aventura", quote: "Com um amigo ao lado, o mundo encanta." },
      { t: "Bruno Em Uma Aventura Animal", p: "Leão, girafa e zebra ao redor: Bruno descobre os animais e aprende a cuidar de cada um.", cover: "Hard", size: "M", tag: "Animais", quote: "Pequenas aventuras, grandes descobertas." },
      { t: "Aprendendo Economia Com O Gael", p: "Cofrinho, moedas e um plano: Gael aprende a guardar hoje para realizar um sonho amanhã.", cover: "Hard", size: "M", tag: "Economia", quote: "Cada moedinha ajuda o sonho a crescer." },
      { t: "Maria Jesus E A Disciplina No Hockey", p: "Patins, treino e um sorriso no gelo: disciplina e coragem para chegar ao gol.", cover: "Hard", size: "M", tag: "Esporte e coragem", quote: "Patinar, aprender e sorrir." },
    ],
    promise_title: "Um Presente Personalizado Para Eternizar Momentos Inesquecíveis.",
    promise_sub: "Da foto à prévia final, cada detalhe é criado com carinho, dando vida a um presente único para toda a vida.",
    promise: [
      { t: "Privacidade Da Foto", p: "A foto que você envia é usada só para criar o livro — nunca para divulgação. Os exemplos desta página são demonstrações da plataforma." },
      { t: "Impressão Pensada como Presente", p: "Preparado para ficar lindo em mãos, na leitura em família e na hora de entregar." },
      { t: "Prévia Antes De Avançar", p: "Você vê a capa e as páginas e entende o que está criando antes de finalizar." },
      { t: "Entrega Sem Complicação", p: "O PDF fica pronto na plataforma. O livro impresso é sob consulta — em até 24h enviamos a cotação e o prazo." },
    ],
    faq_title: "Perguntas Frequentes", faq_sub: "Tudo o que você precisa saber.",
    faq: [
      { q: "Como crio um livro personalizado?", a: "Escolha um tema, envie uma foto da criança e adicione o nome e uma dedicatória. A IA transforma a foto em ilustrações e você vê a prévia antes de finalizar." },
      { q: "Posso ver o livro antes?", a: "Sim! Você recebe uma prévia completa (capa e páginas) antes de baixar ou pedir a impressão." },
      { q: "A foto e os dados da criança estão seguros?", a: "Sim. Usamos a foto que você envia apenas para criar o livro e não compartilhamos seus dados. Os exemplos da página inicial são demonstrações, separados do que você envia." },
      { q: "Recebo digital ou impresso?", a: "O e-book digital fica pronto na plataforma. Se quiser o impresso, peça a cotação depois de aprovar o livro." },
      { q: "Posso pedir alterações?", a: "Pode! Ajuste o nome, a dedicatória e regenere as ilustrações na prévia até ficar do seu jeito." },
      { q: "Como funciona o vídeo narrado?", a: "Depois do ebook pronto, na tela de resultado você pode gerar o vídeo narrado (voz + cenas ilustradas) ou uma animação curta do personagem." },
    ],
    rev_title: "O Que As Famílias Dizem", rev_sub: "Histórias que viraram memórias para sempre.",
    reviews: [
      { q: "Meu filho pede para ler o livro dele toda noite. Emocionante vê-lo como herói!", name: "Ana C." },
      { q: "Enviei uma foto e recebi um livro lindo. Virou o presente de aniversário da vovó.", name: "Rafael M." },
      { q: "A ilustração ficou idêntica ao meu bebê. Vamos guardar para sempre.", name: "Juliana P." },
      { q: "O vídeo narrado fez a família toda se emocionar. Vale cada segundo.", name: "Marcos e Bia" },
      { q: "A vovó se viu no livro com a neta e chorou de alegria. Guardamos na estante da sala.", name: "Camila R." },
      { q: "Vi a prévia da capa e das páginas antes de finalizar. Ficou com o rostinho da minha filha.", name: "Pedro L." },
      { q: "No aniversário, minha filha abriu o livro e não largou mais. Virou a história da noite.", name: "Fernanda S." },
      { q: "Coloquei o cachorro na aventura e meu filho mostrou para a família inteira.", name: "Helena V." },
      { q: "Todo domingo o pai lê com ele. Os dois se reconhecem em cada página.", name: "Thiago A." },
      { q: "Fizemos o livro dos primos. Eles riram ao se ver juntos na mesma história.", name: "Larissa M." },
    ],
    features: ["Histórias Personalizadas", "Conexão Em Família", "Memórias Que Ficam Para Sempre", "Um Presente Inesquecível"],
    band_title: "Pronto para Virar Protagonista?",
    band_sub: "Envie sua foto e receba uma história única, criada só para você.",
    band_cta: "Criar Minha Conta",
    tagline: "Feito com amor. Criado para encantar.",
    foot_copy: "© 2026 Story R Us — Where Memories Become Magic.",
  },
  en: {
    nav: ["How It Works", "Books", "Videos", "FAQ"],
    reviews_link: "Reviews",
    videos_link: "Videos",
    my_books: "My Books",
    see_all_books: "See All Books",
    view_all: "View All",
    cat_empty: "We don't have an example for this theme yet.",
    cats_label: "Books",
    realistic_link: "Realistic",
    cartoon_link: "Cartoon Books",
    quick_links: "Quick Links",
    font_label: "Cover Font",
    explore: "Explore Now",
    eyebrow: "Preserve Moments. Gift Your Family An Unforgettable Story.",
    h_pre: "Turn a photo into an ", w1: "unforgettable story", c1: ", where your child is the ", w2: "hero", h_suf: " !",
    lead: "You send the photo and we turn your child into an illustrated character, creating an adventure made just for them — a book to gift the family and keep forever.",
    cta_login: "Log In",
    cta_play: "Sign Up",
    account: "My Account",
    logout: "Log Out",
    orders: "My Orders",
    users: "Users",
    hero_cta: "Create My Book",
    cta_story: "Create My Story",
    hero_sign: "One photo. One story. One lasting memory.",
    book_carousel: "Book Carousel",
    cats: [
      {
        name: "Themes",
        subs: ["Adventure", "Dinosaurs", "Under the Sea", "Space", "Princesses", "Superheroes", "Sports"],
        feats: ["Princesses", "Adventure", "Cristobal and His Favorite Sport", "Nano and His Adventures"],
      },
      {
        name: "You and Me",
        subs: ["Mommy and Me", "Daddy and Me", "Grandma and Me", "Grandpa and Me", "Our Family", "Siblings and Cousins", "Newborns", "Wedding", "Pets"],
        feats: ["Mommy and Me", "Grandma and Me", "Our Family", "A Mother's Love"],
      },
      {
        name: "Special Occasions",
        subs: [
          "International Women's Day · March 8",
          "Mother-in-law's Day · March 26",
          "Easter",
          "Mother's Day · May 10",
          "International Family Day · May 15",
          "Siblings' Day · May 30",
          "Valentine's Day · June 12",
          "Friendship Day · July 20",
          "Grandparents' Day · July 26",
          "Aunt and Uncle's Day · July 26",
          "Father's Day · August 9",
          "Sons and Daughters Day · August 11",
          "Brazil's Independence Day · September 7",
          "International Day of Older Persons · October 1",
          "World Animal Day · October 4",
          "Children's Day · October 12",
          "Christmas · December 25",
          "Birthday",
        ],
        feats: ["Christmas", "Mother's Day", "Grandparents' Day", "Father's Day"],
      },
      {
        name: "Educational",
        subs: ["Biblical", "Colors", "Hygiene", "Animals", "Feelings", "Bedtime", "Sharing", "Body", "Savings"],
        feats: ["Animals", "Hygiene", "David, the Shepherd Boy"],
      },
    ],
    cat_below: "Preserve Moments. Gift Your Family An Unforgettable Story.",
    cat_below_lead: "Turn a photo into a personalized book, where your child is the hero.",
    trust: "Delighting Families From Start To Finish",
    ba_before: "BEFORE", ba_after: "AFTER", ba_caption: "You send the photo. We create the magic.",
    ba_preview: "PREVIEW",
    ba_title: "Real Before And After",
    ba_sub: "Real photos turned into illustrated characters.",
    ba_pairs: ["From crib to adventure", "A girl full of imagination", "A smile that becomes a character", "From photo to story hero", "Anyone can be the hero"],
    hiw_title: "How It Works", hiw_sub: "You send the photos. We make the book, with your child as the character.",
    hiw: [
      { t: "Send The Photos", p: "Of your child and anyone else in the story." },
      { t: "We Make The Book", p: "A character that looks like the photo, and a story just for you." },
      { t: "The Book Is Ready", p: "Illustrated pages to read and keep." },
    ],
    hiw_main: [
      { t: "Fill In The Details", p: "Send the information, choose the story theme, and send clear photos related to the story you want to create." },
      { t: "Follow The Creation", p: "We create the illustrated character from the photos you send. We develop a unique, engaging story. You review and approve it before we continue." },
      { t: "Review And Approve", p: "Review the preview, cover, and pages for approval. After you confirm, the book goes to production." },
    ],
    passo_title: "Step By Step",
    passo: [
      { t: "Send The Hero Photo", p: "Send clear photos of the character, the hero of your story. These images keep faces, hair, eyes, and the features of the child, relatives, animals, or other characters." },
      { t: "Send Photos Of An Extra Character", p: "Add photos of one or more characters related to the story you want to create." },
      { t: "Review And Approve", p: "Review the preview, cover, and pages for approval. After you confirm, the book goes to production." },
    ],
    hiw_foot: [
      { t: "Send The Photo And Set The Details", p: "Choose the theme and the book format." },
      { t: "We Create The Character And The Story", p: "Story, cover, and pages with the same face as the child." },
      { t: "You Receive And Approve The Book", p: "See the preview, approve it, and receive the printed book." },
    ],
    shot_sub: "Send the photo and set the details.",
    shots: [
      { t: "The Child", p: "3 to 5 front-facing, well-lit photos, with the full face. No filter, hat, or sunglasses." },
      { t: "Family And Pets", p: "2 or 3 photos of each person, alone. For a pet, one facing forward and one full body." },
      { t: "Book Details", p: "Name, age, theme, and language: Portuguese, Spanish, or English." },
    ],
    shot_title: "Tips For The Perfect Photo",
    cartoon_shot_sub: "Upload a clear photo of your child with the face centered.",
    cartoon_shots: ["Clear, well-lit and centered", "More than one person in the photo", "Face at an angle"],
    cartoon_hiw_title: "You Send The Photo",
    cartoon_hiw_photo: "One photo of your child is all it takes to begin.",
    hero_books: [
      "Martin, The Great Goalkeeper Of Chile",
      "Emilia And The Ballerina's First Steps",
      "Antonio And His Bicycle",
      "Maria Jesus And Hockey Discipline",
      "Facundo And Careful Motocross",
    ],
    vid_title: "Videos", vid_sub: "The same story gains voice, music and motion — perfect to watch together.",
    vid_dur: "~2 min", vid_cta: "Create My Video",
    videos: [
      { t: "My Dad, My Hero", p: "Dad and baby side by side — each page comes gently to life." },
      { t: "Sofia and the Enchanted Forest", p: "Gentle little creatures and firefly lights, with a soft soundtrack." },
      { t: "Matteo and the Dinosaur World", p: "A journey through the dinosaur valley, with voice and music." },
    ],
    vid_soon: "Coming Soon",
    book_badge: "Real Example",
    story_title: "Flip Through Our Books",
    story_sub: "Books created by the platform from a single photo — pick an example.",
    story_hint: "Click the sides of the book (or use the arrows) to turn the pages.",
    chloe_title: "Chloe's Story",
    fmt_title: "Choose The Format", fmt_sub: "From the same character, three ways to keep the story.",
    formats: [
      { t: "PDF Book", p: "Cover and illustrated pages, ready on the platform. Print is quoted on request.", feats: ["Cover + illustrated pages", "PDF right away", "Character true to the photo"], cta: "Create My Book", badge: "Most Loved" },
      { t: "Narrated Video", p: "The story gets a voice and music, perfect to watch together.", feats: ["Enchanting narration", "Illustrated scenes", "Easy to share"], cta: "Create My Video", badge: "" },
      { t: "Animation", p: "The character comes alive in a short animation.", feats: ["Movement and magic", "Based on your story", "A different gift"], cta: "Create Animation", badge: "" },
    ],
    cat_title: "Our Books", cat_sub: "Each theme becomes an illustrated story, with your child as the hero of their own story.",
    personalize: "Personalize",
    a11y_theme: "Toggle light/dark theme",
    a11y_menu: "Menu",
    a11y_slide: "Slide",
    photo_real_alt: "Example Photo Of The Child",
    fb_prev: "Previous Page",
    fb_next: "Next Page",
    fb_turn: "Turn Page",
    fb_cover: "Cover",
    fb_photo: "In Hand",
    theme_to_light: "Light",
    theme_to_dark: "Dark",
    privacy_link: "Privacy",
    terms_link: "Terms",
    catalog: [
      { t: "Martin, The Great Goalkeeper Of Chile", p: "A goalkeeper who falls, rises and defends: courage and grit on the field.", cover: "Hard", size: "M", tag: "Sport and courage", quote: "Fall, rise, and keep going!" },
      { t: "Emilia And The Ballerina's First Steps", p: "Ballet's first steps with discipline, balance and confidence.", cover: "Soft", size: "M", tag: "Ballet and dreams", quote: "Small steps, big achievements." },
      { t: "Antonio And His Bicycle", p: "Pedal, learn and explore the world in small adventures.", cover: "Soft", size: "M", tag: "Adventure and movement", quote: "Pedal, learn and smile!" },
      { t: "Learning The Alphabet With Sofia", p: "Letters and forest discoveries — literacy through play.", cover: "Soft", size: "M", tag: "Literacy through play", quote: "Every letter opens a new world." },
      { t: "Cristobal And His Favorite Sport", p: "On the kayak: balance, courage and respect for the river.", cover: "Hard", size: "M", tag: "Sport and courage", quote: "Small paddles, big victories." },
      { t: "Nicolas, My First Love", p: "A tender, eternal moment between mom and son, full of warmth to treasure forever.", cover: "Soft", size: "M", tag: "A mother's love", quote: "First child, eternal love!" },
      { t: "A Mother's Love", p: "Small stories of a big love: mom's tenderness on every page, to treasure forever.", cover: "Hard", size: "M", tag: "A mother's love", quote: "In mom's arms, I find my place." },
      { t: "Mommy, Daddy And Matteo", p: "A celebration of family: mom and dad's love coming together in a story all their own.", cover: "Hard", size: "M", tag: "Family love", quote: "Together, we make love our home." },
      { t: "A Great-Grandmother's Love", p: "A tribute to great-grandma: hugs, warmth and stories that cross generations, to treasure forever.", cover: "Hard", size: "M", tag: "Love across generations", quote: "Great-grandma's hug holds all my love." },
      { t: "Christmas With Tata And Meme", p: "A family Christmas: the warmth of grandma and grandpa, twinkling lights and a big hug to treasure forever.", cover: "Hard", size: "M", tag: "Family Christmas", quote: "Christmas feels warmer with the ones we love." },
      { t: "Nano And His Adventures", p: "A sea adventure all his own: the wind in his ears, the blue ocean and the joy of exploring beside the ones he loves, to treasure forever.", cover: "Hard", size: "M", tag: "Adventure and sea", quote: "Wind in his ears, sea ahead — the adventure has begun!" },
      { t: "Maya, My Loving Dog", p: "A heartwarming friendship between a girl and her dog: care, affection and companionship on every page.", cover: "Soft", size: "M", tag: "Friendship and care", quote: "Love and care, every day." },
      { t: "Mako, My Loyal Friend", p: "A baby and his loyal dog: loyalty, protection and affection in a friendship all their own.", cover: "Soft", size: "M", tag: "Friendship and loyalty", quote: "Loyal love, every day." },
      { t: "Ester's Special Birthday", p: "Candles, hugs and a wish from the heart: your child's birthday becomes a story all their own.", cover: "Hard", size: "M", tag: "Birthday", quote: "One more year of happiness!" },
      { t: "Raquel And Dad: Adventures Forever", p: "Hand in hand with dad, every path becomes a memory — an adventure to keep forever.", cover: "Hard", size: "M", tag: "Dad and me", quote: "Together, the adventure never ends." },
      { t: "Rebeca, The Little Great Heroine", p: "Cape in the wind and courage in her heart: your child saves the day with kindness.", cover: "Hard", size: "M", tag: "Superheroes", quote: "Being a hero starts with a smile." },
      { t: "Abigail On A Space Adventure", p: "Rockets, planets and curiosity: a starry journey with your child at the helm.", cover: "Hard", size: "M", tag: "Space", quote: "Courage, curiosity and discovery!" },
      { t: "Miriam And The Secrets Of The Deep Sea", p: "Turtles, coral and friendship: your child explores the ocean with care and wonder.", cover: "Hard", size: "M", tag: "Under the Sea", quote: "Caring for the sea is caring for friends." },
      { t: "Noé In The Land Of Dinosaurs", p: "Fossils, giant friends and courage: a prehistoric expedition with your child.", cover: "Hard", size: "M", tag: "Dinosaurs", quote: "Discovering together is the best adventure." },
      { t: "An Aunt's Love", p: "An aunt's tenderness on every page: a hug, a laugh, and a love the family keeps forever.", cover: "Hard", size: "M", tag: "Aunt's love", quote: "An aunt's hug never ends." },
      { t: "David, The Shepherd Boy", p: "A boy, his harp and the sheep: courage and faith in a story to keep forever.", cover: "Hard", size: "M", tag: "Faith and courage", quote: "Small in the field, great in heart." },
      { t: "My Dad, My Hero", p: "Dad and baby, side by side: protection, care, and a hero who belongs to the family.", cover: "Hard", size: "M", tag: "Dad the hero", quote: "My hero has Dad's arms." },
      { t: "Enzo, My Favorite Cousin", p: "Two cousins, one hug and the sea: a friendship the family gives, to keep forever.", cover: "Hard", size: "M", tag: "Cousin love", quote: "A cousin is the friend family gives us." },
      { t: "Lucas And His Friend Max", p: "A boy and his dog: care, walks and a friendship to keep forever.", cover: "Hard", size: "M", tag: "Loyal friend", quote: "Max is a friend for every hour." },
      { t: "Esther And The Superpowers Of Hygiene", p: "Clean hands, brushed teeth and a smile: hygiene habits that become superpowers.", cover: "Hard", size: "M", tag: "Hygiene", quote: "Taking care of yourself is a superpower." },
      { t: "Little Builder, Big Entrepreneur", p: "A hard hat, blocks and a plan on paper: build, try again and watch the idea stand up.", cover: "Hard", size: "M", tag: "Build and create", quote: "Small hands, big ideas." },
      { t: "My Favorite Hero, The Firefighter", p: "A siren, courage and a real hero: the firefighter who looks after the city and the family.", cover: "Hard", size: "M", tag: "Real heroes", quote: "My hero protects everyone." },
      { t: "My Favorite Hero, The Police Officer", p: "A uniform, care and a hero of the city: the officer who protects the people we love.", cover: "Hard", size: "M", tag: "Real heroes", quote: "My hero looks after us every day." },
      { t: "My Favorite Hero, The Spider", p: "A web in the garden and a tiny friendship: discovering nature with care and wonder.", cover: "Hard", size: "M", tag: "Nature and friendship", quote: "Even the smallest friend can be a hero." },
      { t: "A Special Aunt, One Of A Kind", p: "A walk, a hug and a laugh: the aunt who turns any day into a memory to keep.", cover: "Hard", size: "M", tag: "Aunt's love", quote: "With aunt, every day becomes an outing." },
      { t: "Grandpa's Love, My Safe Harbor", p: "Grandpa's arms, the lake and a hug that never ends: a safe harbor just for the family.", cover: "Hard", size: "M", tag: "Grandpa's love", quote: "In grandpa's arms, I find my safe harbor." },
      { t: "Happy Easter", p: "Eggs, flowers and a little bunny in the garden: Easter becomes a story to keep.", cover: "Hard", size: "M", tag: "Easter", quote: "Easter is joy to share." },
      { t: "Our Family", p: "Grandparents, parents and children together on the grass: the whole family's love in one story.", cover: "Hard", size: "M", tag: "Our family", quote: "Together, family is our place." },
      { t: "My Great Adventure", p: "A boy, his dog and a castle on the horizon: every step on the trail teaches him to look, listen and care.", cover: "Hard", size: "M", tag: "Adventure", quote: "With a friend beside him, the world feels wonderful." },
      { t: "Bruno On An Animal Adventure", p: "A lion, a giraffe and a zebra all around: Bruno meets the animals and learns to care for each one.", cover: "Hard", size: "M", tag: "Animals", quote: "Small adventures, big discoveries." },
      { t: "Learning Savings With Gael", p: "A piggy bank, coins and a plan: Gael learns to save today so a dream can happen tomorrow.", cover: "Hard", size: "M", tag: "Savings", quote: "Every little coin helps the dream grow." },
      { t: "Maria Jesus And Discipline In Hockey", p: "Skates, practice and a smile on the ice: discipline and courage to reach the goal.", cover: "Hard", size: "M", tag: "Sport and courage", quote: "Skate, learn and smile." },
    ],
    promise_title: "Every Detail Crafted to Feel Special",
    promise_sub: "From the photo to the preview, everything is made so the book is ready to gift.",
    promise: [
      { t: "Photo Privacy", p: "The photo you upload is used only to create the book — never for promotion. The examples on this page are platform demos." },
      { t: "Print Made as a Gift", p: "Prepared to look beautiful in hand, in shared reading and at the moment you give it." },
      { t: "Preview Before You Continue", p: "You see the cover and pages and understand what you're creating before finishing." },
      { t: "Hassle-Free Delivery", p: "The PDF is ready on the platform. Printed books are quoted on request — we send price and timing within 24 hours." },
    ],
    faq_title: "Frequently Asked Questions", faq_sub: "Everything you need to know.",
    faq: [
      { q: "How do I create a personalized book?", a: "Pick a theme, upload a photo of your child and add the name and a dedication. The AI turns the photo into illustrations and you see a preview before finishing." },
      { q: "Can I see the book before?", a: "Yes! You get a full preview (cover and pages) before downloading or ordering the print." },
      { q: "Are my child's photo and data safe?", a: "Yes. We use the photo you upload only to create the book and never share your data. Homepage examples are demos, separate from what you send." },
      { q: "Digital or printed?", a: "The digital e-book is ready on the platform. If you want a printed copy, request a quote after you approve the book." },
      { q: "Can I request changes?", a: "You can! Adjust the name, the dedication and regenerate the illustrations in the preview." },
      { q: "How does the narrated video work?", a: "After the ebook is ready, on the result screen you can generate a narrated video (voice + illustrated scenes) or a short character animation." },
    ],
    rev_title: "What Families Say", rev_sub: "Stories that became memories forever.",
    reviews: [
      { q: "My son asks to read his book every night. Seeing him as the hero is moving!", name: "Ana C." },
      { q: "I sent a photo and got a beautiful book. It became grandma's birthday gift.", name: "Rafael M." },
      { q: "The illustration looks just like my baby. We'll keep it forever.", name: "Juliana P." },
      { q: "The narrated video moved the whole family. Worth every second.", name: "Marcos & Bia" },
      { q: "Grandma saw herself in the book with her granddaughter and cried happy tears. It lives on our shelf.", name: "Camila R." },
      { q: "I saw the cover and pages in the preview before finishing. It has my daughter's face.", name: "Pedro L." },
      { q: "On her birthday, my daughter opened the book and wouldn't put it down. It became the bedtime story.", name: "Fernanda S." },
      { q: "I put the dog in the adventure and my son showed it to the whole family.", name: "Helena V." },
      { q: "Every Sunday his dad reads it with him. They recognize themselves on every page.", name: "Thiago A." },
      { q: "We made the cousins' book. They laughed seeing themselves in the same story.", name: "Larissa M." },
    ],
    features: ["Personalized Stories", "Family Connection", "Memories That Last Forever", "An Unforgettable Gift"],
    band_title: "Ready to Become the Hero?",
    band_sub: "Send your photo and get a unique story, made just for you.",
    band_cta: "Create My Account",
    tagline: "Made with love. Created to enchant.",
    foot_copy: "© 2026 Story R Us — Where Memories Become Magic.",
  },
  es: {
    nav: ["Cómo Funciona", "Libros", "Videos", "FAQ"],
    reviews_link: "Reseñas",
    videos_link: "Videos",
    my_books: "Mis Libros",
    see_all_books: "Ver Todos Los Libros",
    view_all: "Ver Todos",
    cat_empty: "Todavía no tenemos un ejemplo de este tema.",
    cats_label: "Libros",
    realistic_link: "Realista",
    cartoon_link: "Libros Cartoon",
    quick_links: "Accesos Rápidos",
    font_label: "Fuente Del Título",
    explore: "Explorar Ahora",
    eyebrow: "Eterniza Momentos. Regala A Tu Familia Una Historia Inolvidable.",
    h_pre: "Convierte una foto en una ", w1: "historia inolvidable", c1: ", donde tu hijo es el ", w2: "protagonista", h_suf: " !",
    lead: "Envías la foto y transformamos a tu hijo en un personaje ilustrado, creando una aventura personalizada especialmente para él — un libro para regalar a la familia y guardar para siempre.",
    cta_login: "Entrar",
    cta_play: "Crear Cuenta",
    account: "Mi Cuenta",
    logout: "Salir",
    orders: "Mis Pedidos",
    users: "Usuarios",
    hero_cta: "Crear Mi Libro",
    cta_story: "Crear Mi Historia",
    hero_sign: "Una foto. Una historia. Una memoria eterna.",
    book_carousel: "Carrusel De Libros",
    cats: [
      {
        name: "Temáticas",
        subs: ["Aventura", "Dinosaurios", "Fondo del Mar", "Espacio", "Princesas", "Superhéroes", "Deportes"],
        feats: ["Princesas", "Aventura", "Cristobal y su deporte favorito", "Nano y sus aventuras"],
      },
      {
        name: "Tú y Yo",
        subs: ["Mamá y Yo", "Papá y Yo", "Abuela y Yo", "Abuelo y Yo", "Nuestra Familia", "Hermanos y Primos", "Recién Nacidos", "Boda", "Mascotas"],
        feats: ["Mamá y Yo", "Abuela y Yo", "Nuestra Familia", "El Amor de Mamá"],
      },
      {
        name: "Ocasiones Especiales",
        subs: [
          "Día Internacional de la Mujer · 8 de marzo",
          "Día de la Suegra · 26 de marzo",
          "Pascua",
          "Día de la Madre · 10 de mayo",
          "Día Internacional de la Familia · 15 de mayo",
          "Día del Hermano · 30 de mayo",
          "Día de los Enamorados · 12 de junio",
          "Día del Amigo · 20 de julio",
          "Día de los Abuelos · 26 de julio",
          "Día del Tío y de la Tía · 26 de julio",
          "Día del Padre · 9 de agosto",
          "Día de los Hijos · 11 de agosto",
          "Independencia de Brasil · 7 de septiembre",
          "Día Internacional de las Personas Mayores · 1 de octubre",
          "Día de los Animales · 4 de octubre",
          "Día del Niño · 12 de octubre",
          "Navidad · 25 de diciembre",
          "Cumpleaños",
        ],
        feats: ["Navidad", "Día de la Madre", "Día de los Abuelos", "Día del Padre"],
      },
      {
        name: "Educativo",
        subs: ["Bíblico", "Colores", "Higiene", "Animales", "Sentimientos", "Hora de Dormir", "Compartir", "Cuerpo", "Economía"],
        feats: ["Animales", "Higiene", "David, el Niño Pastor"],
      },
    ],
    cat_below: "Eterniza Momentos. Regala A Tu Familia Una Historia Inolvidable.",
    cat_below_lead: "Convierte una foto en un libro personalizado, donde tu hijo es el protagonista.",
    trust: "Encantando a las familias de principio a fin",
    ba_before: "ANTES", ba_after: "DESPUÉS", ba_caption: "Tú envías la foto. Nosotros creamos la magia.",
    ba_preview: "VISTA PREVIA",
    ba_title: "Antes Y Después De Verdad",
    ba_sub: "Fotos reales convertidas en personajes ilustrados.",
    ba_pairs: ["De la cuna a la aventura", "Una niña llena de imaginación", "Una sonrisa que se vuelve personaje", "De la foto al héroe de la historia", "Cualquiera puede ser protagonista"],
    hiw_title: "Cómo Funciona", hiw_sub: "Tú envías las fotos. Nosotros hacemos el libro, con tu hijo como personaje.",
    hiw: [
      { t: "Envía Las Fotos", p: "Del niño y de quien más entra en la historia." },
      { t: "Creamos El Libro", p: "Un personaje parecido a la foto y una historia solo de ustedes." },
      { t: "El Libro Queda Listo", p: "Páginas ilustradas para leer y guardar." },
    ],
    hiw_main: [
      { t: "Completa Los Datos", p: "Envía la información, elige el tema de la historia y envía fotos nítidas relacionadas con la historia que quieres crear." },
      { t: "Acompaña La Creación", p: "Creamos el personaje ilustrado a partir de las fotos enviadas. Desarrollamos una historia única y envolvente. Tú revisas y apruebas antes de que avancemos." },
      { t: "Revisa Y Aprueba", p: "Revisa la vista previa, la portada y las páginas para aprobar. Tras tu confirmación, el libro se envía a producción." },
    ],
    passo_title: "Paso a Paso",
    passo: [
      { t: "Envía La Foto Del Protagonista", p: "Envía fotos nítidas del personaje, protagonista de tu historia. Esas imágenes sirven de referencia para preservar rostros, cabellos, ojos y las características del niño, de familiares, animales u otros personajes." },
      { t: "Envía Fotos Del Personaje Adicional", p: "Agrega fotos de uno o más personajes relacionadas con la historia que quieres crear." },
      { t: "Revisa Y Aprueba", p: "Revisa la vista previa, la portada y las páginas para aprobar. Tras tu confirmación, el libro se envía a producción." },
    ],
    hiw_foot: [
      { t: "Envía La Foto Y Define Los Detalles", p: "Elige el tema y el formato del libro." },
      { t: "Creamos El Personaje Y La Historia", p: "Historia, portada y páginas con el mismo rostro del niño." },
      { t: "Recibes Y Apruebas El Libro", p: "Mira la vista previa, aprueba y recibe el libro impreso." },
    ],
    shot_sub: "Envía la foto y define los detalles.",
    shots: [
      { t: "El Niño", p: "De 3 a 5 fotos de frente, bien iluminadas, con el rostro completo. Sin filtro, sombrero ni gafas." },
      { t: "Familia Y Mascotas", p: "2 o 3 fotos de cada persona, sola. De la mascota, una de frente y otra de cuerpo entero." },
      { t: "Datos Del Libro", p: "Nombre, edad, tema e idioma: portugués, español o inglés." },
    ],
    shot_title: "Consejos Para La Foto Perfecta",
    cartoon_shot_sub: "Envía una foto nítida del niño, con el rostro centrado.",
    cartoon_shots: ["Nítida, bien iluminada y centrada", "Más de una persona en la foto", "Rostro de lado"],
    cartoon_hiw_title: "Tú Envías La Foto",
    cartoon_hiw_photo: "Una foto del niño ya basta para empezar.",
    hero_books: [
      "Martin, El Gran Arquero De Chile",
      "Emilia Y Los Primeros Pasos De La Bailarina",
      "Antonio Y Su Bicicleta",
      "Maria Jesus Y La Disciplina En El Hockey",
      "Facundo Y El Motocross Con Cuidado",
    ],
    vid_title: "Videos", vid_sub: "La misma historia gana voz, música y movimiento — perfecta para ver en familia.",
    vid_dur: "~2 min", vid_cta: "Crear Mi Video",
    videos: [
      { t: "Mi Papá, Mi Héroe", p: "Papá y el bebé lado a lado — cada página cobra movimiento suave." },
      { t: "Sofia Y El Bosque Encantado", p: "Animalitos gentiles y luces de luciérnaga, con una banda suave." },
      { t: "Matteo Y El Mundo De Los Dinosaurios", p: "Un viaje al valle de los dinosaurios, con voz y música." },
    ],
    vid_soon: "Pronto",
    book_badge: "Ejemplo Real",
    story_title: "Hojea Nuestros Libros",
    story_sub: "Libros creados por la plataforma a partir de una sola foto — elige un ejemplo.",
    story_hint: "Haz clic en los laterales del libro (o usa las flechas) para pasar las páginas.",
    chloe_title: "La Historia De Chloe",
    fmt_title: "Elige El Formato", fmt_sub: "Del mismo personaje, tres formas de guardar la historia.",
    formats: [
      { t: "Libro En PDF", p: "Portada y páginas ilustradas, listas en la plataforma. El impreso es bajo consulta.", feats: ["Portada + páginas ilustradas", "PDF al instante", "Personaje fiel a la foto"], cta: "Crear Mi Libro", badge: "Más Querido" },
      { t: "Video Narrado", p: "La historia gana voz y música, perfecta para ver en familia.", feats: ["Narración encantadora", "Escenas ilustradas", "Fácil de compartir"], cta: "Crear Mi Video", badge: "" },
      { t: "Animación", p: "El personaje cobra vida en una animación corta.", feats: ["Movimiento y magia", "Basada en tu historia", "Un regalo diferente"], cta: "Crear Animación", badge: "" },
    ],
    cat_title: "Nuestros Libros", cat_sub: "Cada tema se transforma en una historia ilustrada, con tu hijo como protagonista de su propia historia.",
    personalize: "Personalizar",
    a11y_theme: "Cambiar Tema Claro/Oscuro",
    a11y_menu: "Menú",
    a11y_slide: "Diapositiva",
    photo_real_alt: "Foto De Ejemplo Del Niño",
    fb_prev: "Página Anterior",
    fb_next: "Página Siguiente",
    fb_turn: "Pasar Página",
    fb_cover: "Portada",
    fb_photo: "En Manos",
    theme_to_light: "Claro",
    theme_to_dark: "Oscuro",
    privacy_link: "Privacidad",
    terms_link: "Términos",
    catalog: [
      { t: "Martin, El Gran Arquero De Chile", p: "Arquero que cae, se levanta y defiende: coraje y perseverancia en el campo.", cover: "Hard", size: "M", tag: "Deporte y coraje", quote: "¡Caer, levantarse y seguir!" },
      { t: "Emilia Y Los Primeros Pasos De La Bailarina", p: "Primeros pasos en el ballet con disciplina, equilibrio y confianza.", cover: "Soft", size: "M", tag: "Ballet y sueños", quote: "Pequeños pasos, grandes logros." },
      { t: "Antonio Y Su Bicicleta", p: "Pedalear, aprender y explorar el mundo en pequeñas aventuras.", cover: "Soft", size: "M", tag: "Aventura y movimiento", quote: "¡Pedalear, aprender y sonreír!" },
      { t: "Aprendiendo El Alfabeto Con Sofia", p: "Letras y descubrimientos en el bosque, alfabetizar jugando.", cover: "Soft", size: "M", tag: "Alfabetizar jugando", quote: "Cada letra abre un mundo nuevo." },
      { t: "Cristobal Y Su Deporte Favorito", p: "En el kayak: equilibrio, coraje y respeto por el río.", cover: "Hard", size: "M", tag: "Deporte y coraje", quote: "Pequeñas paladas, grandes conquistas." },
      { t: "Nicolas, Mi Primer Amor", p: "Un momento de cariño eterno entre mamá e hijo, lleno de ternura para guardar para siempre.", cover: "Soft", size: "M", tag: "Amor de madre", quote: "¡Primer hijo, amor eterno!" },
      { t: "El Amor De Mamá", p: "Pequeñas historias de un gran amor: la ternura de mamá en cada página, para guardar para siempre.", cover: "Hard", size: "M", tag: "Amor de madre", quote: "En los brazos de mamá, encuentro mi lugar." },
      { t: "Mamá, Papá Y Matteo", p: "Una celebración de la familia: el cariño de mamá y papá unidos en una historia solo de ellos.", cover: "Hard", size: "M", tag: "Amor de familia", quote: "Juntos, hacemos del amor nuestro hogar." },
      { t: "Amor De Bisabuela", p: "Un homenaje a la bisabuela: abrazos, cariño e historias que atraviesan generaciones, para guardar para siempre.", cover: "Hard", size: "M", tag: "Amor entre generaciones", quote: "El abrazo de la bisabuela guarda todo mi cariño." },
      { t: "Navidad Con Tata Y Meme", p: "Una Navidad en familia: el cariño de la Meme y el Tata, luces en el árbol y un abrazo apretado para guardar para siempre.", cover: "Hard", size: "M", tag: "Navidad en familia", quote: "La Navidad es más linda junto a quienes amamos." },
      { t: "Nano Y Sus Aventuras", p: "Una aventura marítima solo para él: viento en las orejas, mar azul y la alegría de explorar junto a quienes ama, para guardar para siempre.", cover: "Hard", size: "M", tag: "Aventura y mar", quote: "Viento en las orejas, mar por delante — ¡la aventura comenzó!" },
      { t: "Maya, Mi Perrita Cariñosa", p: "Una amistad llena de cariño entre una niña y su perrita: cuidado, afecto y compañía en cada página.", cover: "Soft", size: "M", tag: "Amistad y cuidado", quote: "Amor y cuidado, todos los días." },
      { t: "Mako, Mi Amigo Fiel", p: "Un bebé y su perro fiel: lealtad, protección y cariño en una amistad solo de ellos.", cover: "Soft", size: "M", tag: "Amistad y lealtad", quote: "Amor fiel, todos los días." },
      { t: "El Cumpleaños Especial De Ester", p: "Velas, abrazos y un deseo en el corazón: el cumpleaños de tu hijo se vuelve una historia solo de él.", cover: "Hard", size: "M", tag: "Cumpleaños", quote: "¡Un año más de felicidad!" },
      { t: "Raquel Y Papá: Aventuras Para Siempre", p: "De la mano con papá, cada camino se vuelve recuerdo — una aventura para guardar para siempre.", cover: "Hard", size: "M", tag: "Papá y yo", quote: "Juntos, la aventura nunca termina." },
      { t: "Rebeca, La Pequeña Gran Heroína", p: "Capa al viento y coraje en el pecho: tu hijo salva el día con el corazón.", cover: "Hard", size: "M", tag: "Superhéroes", quote: "Ser héroe empieza con una sonrisa." },
      { t: "Abigail En Una Aventura Por El Espacio", p: "Cohetes, planetas y curiosidad: un viaje estelar con tu hijo al mando.", cover: "Hard", size: "M", tag: "Espacio", quote: "¡Coraje, curiosidad y descubrimientos!" },
      { t: "Miriam Y Los Secretos Del Fondo Del Mar", p: "Tortugas, corales y amistad: tu hijo explora el océano con cuidado y encanto.", cover: "Hard", size: "M", tag: "Fondo del Mar", quote: "Cuidar el mar es cuidar a los amigos." },
      { t: "Noé En La Tierra De Los Dinosaurios", p: "Fósiles, amigos gigantes y coraje: una expedición prehistórica con tu hijo.", cover: "Hard", size: "M", tag: "Dinosaurios", quote: "Descubrir juntos es la mejor aventura." },
      { t: "El Amor De La Tía", p: "El cariño de la tía en cada página: abrazo, risa y un amor que la familia guarda para siempre.", cover: "Hard", size: "M", tag: "Amor de tía", quote: "El abrazo de la tía no se acaba." },
      { t: "David, El Niño Pastor", p: "Un niño, su arpa y las ovejas: coraje y fe en una historia para guardar para siempre.", cover: "Hard", size: "M", tag: "Fe y coraje", quote: "Pequeño en el campo, grande de corazón." },
      { t: "Mi Papá, Mi Héroe", p: "Papá y el bebé, lado a lado: protección, cariño y un héroe solo de la familia.", cover: "Hard", size: "M", tag: "Papá héroe", quote: "Mi héroe tiene los brazos de papá." },
      { t: "Enzo, Mi Primo Favorito", p: "Dos primos, un abrazo y el mar: amistad que da la familia, para guardar para siempre.", cover: "Hard", size: "M", tag: "Amor de primo", quote: "El primo es el amigo que da la familia." },
      { t: "Lucas Y Su Amigo Max", p: "Un niño y su perro: cuidado, paseos y una amistad para guardar para siempre.", cover: "Hard", size: "M", tag: "Amigo fiel", quote: "Max es el amigo de todas las horas." },
      { t: "Esther Y Los Superpoderes De La Higiene", p: "Manos limpias, dientes cepillados y una sonrisa: hábitos de higiene que se vuelven superpoderes.", cover: "Hard", size: "M", tag: "Higiene", quote: "Cuidarse es un superpoder." },
      { t: "Pequeño Constructor, Gran Emprendedor", p: "Casco, bloques y un plano en el papel: construir, intentar de nuevo y ver la idea de pie.", cover: "Hard", size: "M", tag: "Construir y crear", quote: "Manos pequeñas, grandes ideas." },
      { t: "Mi Héroe Favorito, El Bombero", p: "Sirena, coraje y un héroe de verdad: el bombero que cuida la ciudad y la familia.", cover: "Hard", size: "M", tag: "Héroes de verdad", quote: "Mi héroe protege a todo el mundo." },
      { t: "Mi Héroe Favorito, El Policía", p: "Uniforme, cuidado y un héroe de la ciudad: el policía que protege a quienes amamos.", cover: "Hard", size: "M", tag: "Héroes de verdad", quote: "Mi héroe cuida de nosotros todos los días." },
      { t: "Mi Héroe Favorito, La Araña", p: "Una tela en el jardín y una amistad pequeña: descubrir la naturaleza con cuidado y encanto.", cover: "Hard", size: "M", tag: "Naturaleza y amistad", quote: "Hasta el amigo más pequeño puede ser un héroe." },
      { t: "Una Tía Especial, No Hay Otra Igual", p: "Paseo, abrazo y risa: la tía que convierte cualquier día en un recuerdo para guardar.", cover: "Hard", size: "M", tag: "Amor de tía", quote: "Con la tía, todo día se vuelve paseo." },
      { t: "El Amor Del Abuelo, Mi Puerto Seguro", p: "Los brazos del abuelo, el lago y un abrazo que no se acaba: un puerto seguro solo de la familia.", cover: "Hard", size: "M", tag: "Amor de abuelo", quote: "En los brazos del abuelo, encuentro mi puerto seguro." },
      { t: "Feliz Pascua", p: "Huevos, flores y un conejito en el jardín: la Pascua del niño se vuelve una historia para guardar.", cover: "Hard", size: "M", tag: "Pascua", quote: "Pascua es alegría para compartir." },
      { t: "Nuestra Familia", p: "Abuelos, padres y niños juntos en el césped: el cariño de toda la familia en una historia solo de ellos.", cover: "Hard", size: "M", tag: "Nuestra familia", quote: "Juntos, la familia es nuestro lugar." },
      { t: "Mi Gran Aventura", p: "Un niño, su perro y un castillo en el horizonte: cada paso del camino enseña a ver, oír y cuidar.", cover: "Hard", size: "M", tag: "Aventura", quote: "Con un amigo al lado, el mundo encanta." },
      { t: "Bruno En Una Aventura Animal", p: "León, jirafa y cebra alrededor: Bruno conoce a los animales y aprende a cuidar de cada uno.", cover: "Hard", size: "M", tag: "Animales", quote: "Pequeñas aventuras, grandes descubrimientos." },
      { t: "Aprendiendo Economía Con Gael", p: "Alcancía, monedas y un plan: Gael aprende a guardar hoy para cumplir un sueño mañana.", cover: "Hard", size: "M", tag: "Economía", quote: "Cada monedita ayuda a crecer el sueño." },
      { t: "Maria Jesus Y La Disciplina En El Hockey", p: "Patines, entrenamiento y una sonrisa en el hielo: disciplina y coraje para llegar al gol.", cover: "Hard", size: "M", tag: "Deporte y coraje", quote: "Patinar, aprender y sonreír." },
    ],
    promise_title: "Cada Detalle Pensado Para Ser Especial",
    promise_sub: "Del envío de la foto a la vista previa, todo está hecho para que el libro quede listo para regalar.",
    promise: [
      { t: "Privacidad de la Foto", p: "La foto que envías se usa solo para crear el libro — nunca para promoción. Los ejemplos de esta página son demostraciones de la plataforma." },
      { t: "Impresión Pensada como Regalo", p: "Preparado para verse hermoso en las manos, en la lectura en familia y al momento de entregarlo." },
      { t: "Vista Previa antes de Avanzar", p: "Ves la portada y las páginas y entiendes lo que estás creando antes de finalizar." },
      { t: "Entrega sin Complicaciones", p: "El PDF queda listo en la plataforma. El libro impreso es bajo consulta — en hasta 24h enviamos la cotización y el plazo." },
    ],
    faq_title: "Preguntas Frecuentes", faq_sub: "Todo lo que necesitas saber.",
    faq: [
      { q: "¿Cómo creo un libro personalizado?", a: "Elige un tema, envía una foto del niño y agrega el nombre y una dedicatoria. La IA transforma la foto en ilustraciones y ves la vista previa antes de finalizar." },
      { q: "¿Puedo ver el libro antes?", a: "¡Sí! Recibes una vista previa completa (portada y páginas) antes de descargar o pedir la impresión." },
      { q: "¿La foto y los datos del niño están seguros?", a: "Sí. Usamos la foto que envías solo para crear el libro y no compartimos tus datos. Los ejemplos de la página inicial son demostraciones, separados de lo que tú envías." },
      { q: "¿Recibo digital o impreso?", a: "El e-book digital queda listo en la plataforma. Si quieres el impreso, pide la cotización después de aprobar el libro." },
      { q: "¿Puedo pedir cambios?", a: "¡Puedes! Ajusta el nombre, la dedicatoria y regenera las ilustraciones en la vista previa hasta que quede a tu gusto." },
      { q: "¿Cómo funciona el video narrado?", a: "Después del ebook listo, en la pantalla de resultado puedes generar el video narrado (voz + escenas ilustradas) o una animación corta del personaje." },
    ],
    rev_title: "Lo Que Dicen Las Familias", rev_sub: "Historias que se volvieron recuerdos para siempre.",
    reviews: [
      { q: "Mi hijo pide leer su libro todas las noches. ¡Emocionante verlo como héroe!", name: "Ana C." },
      { q: "Envié una foto y recibí un libro hermoso. Se volvió el regalo de cumpleaños de la abuela.", name: "Rafael M." },
      { q: "La ilustración quedó idéntica a mi bebé. Lo vamos a guardar para siempre.", name: "Juliana P." },
      { q: "El video narrado emocionó a toda la familia. Vale cada segundo.", name: "Marcos y Bia" },
      { q: "La abuela se vio en el libro con su nieta y lloró de alegría. Lo guardamos en la estantería.", name: "Camila R." },
      { q: "Vi la portada y las páginas en la vista previa antes de finalizar. Quedó con la carita de mi hija.", name: "Pedro L." },
      { q: "En el cumpleaños, mi hija abrió el libro y no lo soltó. Se volvió la historia de la noche.", name: "Fernanda S." },
      { q: "Puse al perro en la aventura y mi hijo se lo mostró a toda la familia.", name: "Helena V." },
      { q: "Cada domingo el papá lo lee con él. Los dos se reconocen en cada página.", name: "Thiago A." },
      { q: "Hicimos el libro de los primos. Se rieron al verse juntos en la misma historia.", name: "Larissa M." },
    ],
    features: ["Historias Personalizadas", "Conexión En Familia", "Recuerdos Que Quedan Para Siempre", "Un Regalo Inolvidable"],
    band_title: "¿Listo Para Ser El Protagonista?",
    band_sub: "Envía tu foto y recibe una historia única, creada solo para ti.",
    band_cta: "Crear Mi Cuenta",
    tagline: "Hecho con amor. Creado para encantar.",
    foot_copy: "© 2026 Story R Us — Where Memories Become Magic.",
  },
} as const;

/** "fold" = página dobrando (landing-flip-fold.css). "fade" = esmaecer. */
const FLIP_FX = "fade" as "fade" | "fold";
const FLIP_MS = FLIP_FX === "fold" ? 1100 : 700;
const FLIP_AUTO_MS = 3600;
const FLIP_HOLD_MS = 10000;
const FOLD_N = 2;

function FoldMesh({ src, kind }: { src: string; kind: string }) {
  let node: ReactNode = null;
  for (let i = FOLD_N - 1; i >= 0; i--) {
    node = (
      <div
        className={`fb-seg${i === 0 ? " fb-seg-first" : ""}${i === FOLD_N - 1 ? " fb-seg-last" : ""}`}
        style={{ "--k": String(i / Math.max(1, FOLD_N - 1)) } as CSSProperties}
      >
        <span className="fb-seg-front">
          <img className={`fb-page ${kind}`} src={src} alt="" aria-hidden style={{ left: `${-i * 100}%` }} />
        </span>
        <span className="fb-seg-back" aria-hidden />
        {node}
      </div>
    );
  }
  return (
    <div className="fb-fold" style={{ "--folds": FOLD_N } as CSSProperties} aria-hidden>
      {node}
    </div>
  );
}

function prefersReducedMotion() {
  try {
    return !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

function FlipBook({
  pages,
  index,
  onIndex,
  labels,
}: {
  pages: string[];
  index: number;
  onIndex: (next: number) => void;
  labels: { prev: string; next: string; turn: string; cover: string; photo: string };
}) {
  const [anim, setAnim] = useState<"next" | "prev" | null>(null);
  const [target, setTarget] = useState(index);
  const [frame, setFrame] = useState<{ w: number; h: number } | null>(null);
  const [paused, setPaused] = useState(false);
  const busy = useRef(false);
  const fromSelf = useRef(false);
  const didMount = useRef(false);
  const holdUntil = useRef(0);
  const indexRef = useRef(index);
  const onIndexRef = useRef(onIndex);
  const pagesRef = useRef(pages);
  indexRef.current = index;
  onIndexRef.current = onIndex;
  pagesRef.current = pages;
  const pageSrc = pages[index];
  const pageKey = pages.join("|");
  useEffect(() => {
    pages.forEach((src) => {
      const img = new Image();
      img.src = exUrl(src);
    });
  }, [pageKey]);
  useEffect(() => {
    const img = new Image();
    let alive = true;
    const apply = () => {
      if (!alive || !img.naturalWidth || !img.naturalHeight) return;
      const maxW = Math.max(240, Math.min(img.naturalWidth, window.innerWidth - 160));
      const maxH = Math.max(180, Math.min(img.naturalHeight, window.innerHeight * 0.72));
      const scale = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight);
      setFrame({
        w: Math.round(img.naturalWidth * scale),
        h: Math.round(img.naturalHeight * scale),
      });
    };
    img.onload = apply;
    img.src = exUrl(pageSrc);
    if (img.complete) apply();
    window.addEventListener("resize", apply);
    return () => {
      alive = false;
      window.removeEventListener("resize", apply);
    };
  }, [pageSrc]);
  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      setTarget(index);
      return;
    }
    if (fromSelf.current) {
      fromSelf.current = false;
      return;
    }
    busy.current = false;
    setAnim(null);
    setTarget(index);
    holdUntil.current = Date.now() + FLIP_HOLD_MS;
  }, [index]);
  const commit = (next: number) => {
    fromSelf.current = true;
    onIndexRef.current(next);
  };
  const finish = (next: number) => {
    if (!busy.current) return;
    busy.current = false;
    setAnim(null);
    commit(next);
  };
  const flip = (dir: "next" | "prev", fromUser = false) => {
    const list = pagesRef.current;
    if (busy.current || list.length < 2) return;
    const cur = indexRef.current;
    const next = dir === "next" ? (cur + 1) % list.length : (cur - 1 + list.length) % list.length;
    if (fromUser) holdUntil.current = Date.now() + FLIP_HOLD_MS;
    if (prefersReducedMotion()) {
      commit(next);
      return;
    }
    busy.current = true;
    setTarget(next);
    setAnim(dir);
  };
  useEffect(() => {
    if (pages.length < 2) return;
    const tick = () => {
      if (busy.current || paused || document.hidden) return;
      if (Date.now() < holdUntil.current) return;
      flip("next");
    };
    const id = window.setInterval(tick, FLIP_AUTO_MS);
    return () => window.clearInterval(id);
  }, [pageKey, paused]);
  const onLeafEnd = (e: { animationName?: string; target?: EventTarget; currentTarget?: EventTarget }) => {
    if (!anim) return;
    if (e.target !== e.currentTarget) return;
    if (e.animationName && !/^(fbPeel|fbFade)/.test(e.animationName)) return;
    finish(target);
  };
  useEffect(() => {
    if (!anim) return;
    const id = window.setTimeout(() => finish(target), FLIP_MS + 80);
    return () => window.clearTimeout(id);
  }, [anim, target]);
  const folding = FLIP_FX === "fold";
  const underSrc = folding
    ? (anim === "next" ? pages[target] : pages[index])
    : (anim ? pages[target] : pages[index]);
  const leafSrc = folding
    ? (anim === "next" ? pages[index] : (anim === "prev" ? pages[target] : pages[index]))
    : pages[index];
  const underIdx = folding
    ? (anim === "next" ? target : index)
    : (anim ? target : index);
  const leafIdx = folding
    ? (anim === "next" ? index : (anim === "prev" ? target : index))
    : index;
  const pageKind = (idx: number) => {
    const slot = ((idx % 3) + 3) % 3;
    if (slot === 0) return "fb-page--cover";
    if (slot === 2) return "fb-page--photo";
    return "fb-page--spread";
  };
  const pageLabel = (idx: number) => {
    const slot = ((idx % 3) + 3) % 3;
    if (slot === 0) return labels.cover;
    if (slot === 2) return labels.photo;
    return labels.turn;
  };
  const bookBase = Math.floor(index / 3) * 3;
  const bookDots = [bookBase, bookBase + 1, bookBase + 2].filter((i) => i < pages.length);
  const single = pages.length < 2;
  const onStage = (e: RMouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    if (e.clientX - r.left > r.width / 2) flip("next", true); else flip("prev", true);
  };
  const onStageKey = (e: RKeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " " || e.key === "ArrowRight") {
      e.preventDefault();
      flip("next", true);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      flip("prev", true);
    }
  };
  const goTo = (i: number) => {
    if (i === index || busy.current) return;
    const wrapNext = index === pages.length - 1 && i === 0;
    const wrapPrev = index === 0 && i === pages.length - 1;
    const step = Math.abs(i - index) === 1 || wrapNext || wrapPrev;
    if (step) {
      flip(wrapPrev || i < index ? "prev" : "next", true);
      return;
    }
    holdUntil.current = Date.now() + FLIP_HOLD_MS;
    commit(i);
  };
  return (
    <div
      className="flipbook"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setPaused(false);
      }}
    >
      <div className="fb-board">
        {single ? null : <button className="fb-nav" type="button" onClick={() => flip("prev", true)} disabled={!!anim} aria-label={labels.prev}>‹</button>}
        <div
          className="fb-stage"
          onClick={single ? undefined : onStage}
          onKeyDown={single ? undefined : onStageKey}
          role={single ? "img" : "button"}
          tabIndex={single ? undefined : 0}
          aria-label={single ? pageLabel(index) : labels.turn}
          style={frame ? { width: frame.w, height: "auto", aspectRatio: `${frame.w} / ${frame.h}`, maxWidth: "100%" } : undefined}
        >
          <span className="fb-spine" />
          <img className={`fb-page fb-under ${pageKind(underIdx)}`} src={exUrl(underSrc)} alt="" aria-hidden />
          <span className="fb-under-shade" aria-hidden />
          <div
            className={`fb-leaf fb-fx-${FLIP_FX}${anim ? ` ${anim}` : ""}`}
            onAnimationEnd={(e) => onLeafEnd(e)}
          >
            <img className={`fb-page fb-leaf-front ${pageKind(leafIdx)}`} src={exUrl(leafSrc)} alt={pageLabel(index)} data-testid="landing-hero-flip" />
            {folding ? <FoldMesh src={exUrl(leafSrc)} kind={pageKind(leafIdx)} /> : null}
            {folding ? <span className="fb-leaf-back" aria-hidden /> : null}
            {folding ? <span className="fb-leaf-shade" aria-hidden /> : null}
          </div>
        </div>
        {single ? null : <button className="fb-nav" type="button" onClick={() => flip("next", true)} disabled={!!anim} aria-label={labels.next}>›</button>}
      </div>
      {single ? null : (
        <div className="fb-dots" role="tablist" aria-label={labels.turn}>
          {bookDots.map((i, slot) => (
            <button
              key={`${pages[i]}-${i}`}
              type="button"
              className={`fb-dot${i === index ? " on" : ""}`}
              role="tab"
              aria-selected={i === index}
              aria-label={pageLabel(i)}
              data-testid={`landing-hero-flip-dot-${slot}`}
              onClick={() => goTo(i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// M R$ 177 e P R$ 157. Inglês em dólar e espanhol em euro (câmbio de 2 out 2026: USD 5,22 e EUR 5,88).
const FORMAT_COPY: Record<Lang, {
  pages: string;
  hard: string;
  soft: string;
  sizeM: string;
  sizeP: string;
  priceM: string;
  priceP: string;
  hardText: string;
  softText: string;
}> = {
  pt: {
    pages: "Livro 16 Páginas",
    hard: "HARD",
    soft: "SOFT",
    sizeM: "20 × 20 cm",
    sizeP: "15 × 15 cm",
    priceM: "R$ 177,00",
    priceP: "R$ 157,00",
    hardText: "Resistente e durável. Utilizada em edições especiais ou colecionáveis.",
    softText: "Leve e flexível. Comum em livros e edições econômicas.",
  },
  en: {
    pages: "Book. 16 Pages.",
    hard: "HARD",
    soft: "SOFT",
    sizeM: "20 × 20 cm",
    sizeP: "15 × 15 cm",
    priceM: "$33.91",
    priceP: "$30.08",
    hardText: "Sturdy and durable. Used for special or collectible editions.",
    softText: "Light and flexible. Common in books and economical editions.",
  },
  es: {
    pages: "Libro. 16 Páginas.",
    hard: "HARD",
    soft: "SOFT",
    sizeM: "20 × 20 cm",
    sizeP: "15 × 15 cm",
    priceM: "30,10 €",
    priceP: "26,70 €",
    hardText: "Resistente y duradera. Utilizada en ediciones especiales o de colección.",
    softText: "Ligera y flexible. Común en libros y ediciones económicas.",
  },
};
export type CatalogCardBook = {
  t: string;
  img: string;
  theme: string;
  cover?: string;
  size?: string;
  tag?: string;
  heroi?: string;
  catalogI?: number;
  story?: string;
  quote?: string;
};
const BOOK_PAGE_COPY: Record<Lang, { summary: string; details: string; cover: string; page: string; photo: string }> = {
  pt: { summary: "Resumo Da História", details: "Detalhes Do Livro", cover: "Capa", page: "Página", photo: "Foto" },
  en: { summary: "Story Summary", details: "Book Details", cover: "Cover", page: "Page", photo: "Photo" },
  es: { summary: "Resumen De La Historia", details: "Detalles Del Libro", cover: "Portada", page: "Página", photo: "Foto" },
};
export function CatalogBookCard({
  book,
  lang,
  personalize,
  modo = "realista",
  linkBook = true,
  showStory = false,
  layout = "card",
}: {
  book: CatalogCardBook;
  lang: Lang;
  personalize: string;
  modo?: "realista" | "cartoon";
  linkBook?: boolean;
  showStory?: boolean;
  layout?: "card" | "page";
}) {
  const [cover, setCover] = useState<CatalogCoverChoice>(catalogCoverChoice(book.cover));
  const [size, setSize] = useState<CatalogSizeChoice>(catalogSizeChoice(book.size));
  const copy = FORMAT_COPY[lang];
  const bookHref = book.catalogI != null ? `/livro/${book.catalogI}` : null;
  const linked = linkBook && bookHref != null;
  const image = <img src={exUrl(book.img)} alt={book.t} loading="lazy" />;
  const notes = (
    <div className="cat-notes">
      <div className="cat-notes-sizes">
        <p className="cat-notes-lead">{copy.pages}</p>
        {(["P", "M"] as const).map((choice) => (
          <p key={choice} className="cat-note-line">
            <span className="cat-opt">
              <button
                type="button"
                className={size === choice ? "is-on" : ""}
                aria-pressed={size === choice}
                onClick={() => setSize(choice)}
              >
                {choice}
              </button>
            </span>
            <span>
              {choice === "M" ? copy.sizeM : copy.sizeP}:{" "}
              <span className={size === choice ? "is-price" : undefined}>
                {choice === "M" ? copy.priceM : copy.priceP}.
              </span>
            </span>
          </p>
        ))}
      </div>
      <div className="cat-note-grid">
        {(["hard", "soft"] as const).map((choice) => (
          <div key={choice} className="cat-note-line">
            <span className="cat-opt">
              <button
                type="button"
                className={cover === choice ? "is-on" : ""}
                aria-pressed={cover === choice}
                onClick={() => setCover(choice)}
              >
                {choice === "hard" ? copy.hard : copy.soft}
              </button>
            </span>
            <p>{choice === "hard" ? copy.hardText : copy.softText}</p>
          </div>
        ))}
      </div>
    </div>
  );
  const go = (
    <Link
      to={personalizeHref({
        theme: book.theme,
        title: book.t,
        historia: book.tag,
        heroi: book.heroi,
        size,
        cover,
        modo: modo ?? "realista",
        catalogI: book.catalogI,
      })}
      className="kbtn kbtn-primary cat-go"
      data-testid="landing-personalize"
    >
      {personalize}
    </Link>
  );
  if (layout === "page") {
    const pageCopy = BOOK_PAGE_COPY[lang];
    const series =
      book.catalogI != null
        ? catalogSeriesShots(book.catalogI, lang)
        : [{ key: "cover" as const, src: book.img }];
    return (
      <article className="cat-card book-sheet reveal" data-testid="landing-catalog-card" data-format="catalog">
        <div className="cat-display book-series" data-testid="book-series">
          {series.map((shot) => (
            <figure key={shot.key} className={`book-series-shot is-${shot.key}`} data-testid={`book-series-${shot.key}`}>
              <div className="book-series-frame">
                <div className="cat-book" data-size={shot.key === "cover" ? size : "M"}>
                  <img src={exUrl(shot.src)} alt={`${book.t} — ${pageCopy[shot.key]}`} loading="lazy" />
                </div>
              </div>
              <figcaption>{pageCopy[shot.key]}</figcaption>
            </figure>
          ))}
        </div>
        <div className="cat-body">
          {book.tag ? <p className="book-tag">{book.tag}</p> : null}
          <h1 title={book.t}>{book.t}</h1>
          <section className="book-block">
            <h2>{pageCopy.summary}</h2>
            {book.story ? <p className="cat-story" data-testid="book-story">{book.story}</p> : null}
            {book.quote ? <p className="cat-quote">{book.quote}</p> : null}
          </section>
          <section className="book-block">
            <h2>{pageCopy.details}</h2>
            {notes}
          </section>
          {go}
        </div>
      </article>
    );
  }
  return (
    <div className="cat-card" data-testid="landing-catalog-card" data-format="catalog">
      <div className="cat-display">
        <div className="cat-book" data-size={size}>
          {linked ? <Link to={bookHref} className="cat-book-link">{image}</Link> : image}
        </div>
      </div>
      <div className="cat-body">
        <h3 title={book.t}>{linked ? <Link to={bookHref} title={book.t}>{book.t}</Link> : book.t}</h3>
        {showStory && book.story ? <p className="cat-story" data-testid="book-story">{book.story}</p> : null}
        {showStory && book.quote ? <p className="cat-quote">{book.quote}</p> : null}
        {notes}
        {go}
      </div>
    </div>
  );
}
function toCatalogCard(lang: Lang, index: number): CatalogCardBook | null {
  if (index === 13 || index === 32) return null;
  const book = I18N[lang].catalog[index];
  const theme = CATALOG_THEMES[index];
  if (!book || !theme || !CATALOG_IMGS[index]) return null;
  return {
    t: book.t,
    story: book.p,
    quote: book.quote,
    img: catalogCoverFile(index, lang, "photo"),
    theme,
    cover: book.cover,
    size: book.size,
    tag: book.tag,
    heroi: HERO_BY_CATALOG[index],
    catalogI: index,
  };
}
export function readSiteLang(): Lang {
  return readStoredLang("pt");
}
export function catalogPageCopy(lang: Lang) {
  const t = I18N[lang];
  return {
    title: t.cat_title,
    personalize: t.personalize,
    back: t.see_all_books,
    empty: t.cat_empty,
    cats: t.cats_label,
    hiw: t.hiw_title,
    passo: t.passo_title,
    videos: t.videos_link,
    reviews: t.reviews_link,
    cartoon: t.cartoon_link,
  };
}
/** Rótulo de subcategoria no catálogo: tira a data do menu ("Natal · 25 de dezembro" → "Natal"). */
function catalogSubLabel(label: string): string {
  const cut = label.indexOf(" · ");
  return cut === -1 ? label : label.slice(0, cut);
}
function rankCatalogIndex(index: number): number {
  const lead = CATALOG_LEAD.indexOf(index);
  return lead === -1 ? CATALOG_LEAD.length + index : lead;
}
function sortCatalogBooks(books: CatalogCardBook[]): CatalogCardBook[] {
  return [...books].sort(
    (a, b) => rankCatalogIndex(a.catalogI ?? Number.MAX_SAFE_INTEGER) - rankCatalogIndex(b.catalogI ?? Number.MAX_SAFE_INTEGER),
  );
}
export type CatalogSubSection = {
  id: string;
  name: string;
  books: CatalogCardBook[];
};
export type CatalogSection = {
  id: string;
  name: string;
  color: string;
  subs: CatalogSubSection[];
  books: CatalogCardBook[];
};
export function catalogCategory(lang: Lang, id: string): CatalogSection | null {
  if (id === "sentimentos") {
    const name = lang === "en" ? "Feelings" : lang === "es" ? "Sentimientos" : "Sentimentos";
    const books = sortCatalogBooks(
      CATALOG_THEMES.flatMap((theme, index) => {
        if (!FEELING_THEMES.has(theme)) return [];
        const card = toCatalogCard(lang, index);
        return card ? [card] : [];
      }),
    );
    return {
      id,
      name,
      color: "#f0a0c0",
      subs: books.length ? [{ id: "sentimentos", name, books }] : [],
      books,
    };
  }
  return catalogSections(lang).find((section) => section.id === id) ?? null;
}
export function catalogEntry(lang: Lang, index: number) {
  const card = toCatalogCard(lang, index);
  if (!card) return null;
  const section = NAV_CAT_META.find((meta) => CATALOG_SECTION_THEMES[meta.id]?.includes(card.theme));
  return { ...card, sectionId: section?.id ?? "aventuras" };
}
export function catalogSections(lang: Lang): CatalogSection[] {
  const names = I18N[lang].cats;
  return NAV_CAT_META.map((meta, i) => {
    const catCopy = names[i];
    const sectionThemes = CATALOG_SECTION_THEMES[meta.id] ?? [];
    const placed = new Set<number>();
    const subs = meta.subs.flatMap((subMeta, j) => {
      const theme = themeFromHref(subMeta.href);
      if (!theme || !sectionThemes.includes(theme)) return [];
      const books = sortCatalogBooks(
        CATALOG_THEMES.flatMap((bookTheme, index) => {
          if (bookTheme !== theme || placed.has(index) || isCartoonOnlyCover(index)) return [];
          const card = toCatalogCard(lang, index);
          if (!card) return [];
          placed.add(index);
          return [card];
        }),
      );
      if (!books.length) return [];
      return [{
        id: theme,
        name: catalogSubLabel(catCopy?.subs[j] ?? theme),
        books,
      }];
    });
    return {
      id: meta.id,
      name: catCopy?.name ?? meta.id,
      color: meta.color,
      subs,
      books: subs.flatMap((sub) => sub.books),
    };
  });
}

export function Landing({ variant = "photo" }: { variant?: "photo" | "cartoon" } = {}) {
  const { pathname } = useLocation();
  usePageMeta(
    pathname === "/cartoon" || variant === "cartoon"
      ? staticPageMeta("/cartoon")
      : pathname === "/landing"
        ? staticPageMeta("/landing")
        : staticPageMeta("/"),
  );
  const rootRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef<HTMLDivElement | null>(null);
  const [openCat, setOpenCat] = useState<number | null>(null);
  const [subHover, setSubHover] = useState<{ cat: number; sub: number } | null>(null);
  const [featCat, setFeatCat] = useState<number | null>(null);
  const [mobileCat, setMobileCat] = useState<number | null>(null);
  const [mobileSub, setMobileSub] = useState<{ cat: number; sub: number } | null>(null);
  const [lang, setLang] = useResolvedLang();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try { const s = localStorage.getItem("theme"); if (s === "light" || s === "dark") return s; } catch { /* ignore */ }
    return "dark";
  });
  const [heroPick, setHeroPick] = useState(0);
  const [coverFont] = useState<CoverFont>(() => {
    try {
      const s = localStorage.getItem("coverFont");
      if (s === "fredoka" || s === "baloo" || s === "lilita") return s;
    } catch { /* ignore */ }
    return "fredoka";
  });
  const t = I18N[lang];
  const [session, setSession] = useState<LandingSession>(() =>
    getToken() ? { status: "loading" } : { status: "out" },
  );
  const signedIn = session.status === "in";
  const isOwner = session.status === "in" && session.isOwner;
  const createHref = signedIn || getToken() ? "/app" : "/cadastro";
  const headerCtaLabel = signedIn ? t.hero_cta : t.cta_play;
  const bandCtaLabel = signedIn ? t.hero_cta : t.band_cta;
  const hiwSteps = t.hiw_main;
  const howImgs = variant === "cartoon" ? HOW_IMGS : HOW_SCENE_IMGS;
  const navHrefs = ["#como", "#catalogo", "#videos", "#faq"];
  const heroStrip = HERO_STRIP.flatMap((book) => {
    if (variant !== "cartoon") return [book];
    const shot = CARTOON_HERO[book.name];
    if (!shot) return [];
    return [{
      ...book,
      cover: shot.cover ? heroAsset(shot.cover) : book.cover,
      page: shot.page ? heroAsset(shot.page) : book.page,
      photo: shot.photo ? heroAsset(shot.photo) : book.photo,
    }];
  });
  const catalogBooks = t.catalog
        .map((c, i) => ({ c, i }))
        .filter(({ i }) => (variant === "cartoon"
          ? Boolean(CARTOON_COVER[i])
          : (CATALOG_NEW_INDEXES.has(i) || i < CATALOG_LIMIT) && !CATALOG_CARTOON_INDEXES.has(i) && !isCartoonOnlyCover(i)))
        .sort((a, b) => {
          const rank = (i: number) => {
            const lead = CATALOG_LEAD.indexOf(i);
            return lead === -1 ? CATALOG_LEAD.length + i : lead;
          };
          return rank(a.i) - rank(b.i);
        })
        .map(({ c, i }) => ({
          t: c.t,
          img: catalogCoverFile(i, lang, variant),
          theme: CATALOG_THEMES[i],
          cover: c.cover,
          size: c.size,
          tag: c.tag,
          heroi: HERO_BY_CATALOG[i],
          catalogI: i,
        }));
  const reviewPhotos = variant === "cartoon" ? CARTOON_REVIEW_PHOTOS : REVIEW_PHOTOS;
  const heroPages = heroStrip.flatMap((book) => [book.cover[lang], book.page[lang], book.photo[lang]]);
  const flipLabels = { prev: t.fb_prev, next: t.fb_next, turn: t.fb_turn, cover: t.fb_cover, photo: t.fb_photo };
  const navCats = t.cats.map((cat, i) => ({
    ...cat,
    id: NAV_CAT_META[i].id,
    color: NAV_CAT_META[i].color,
    subs: cat.subs.flatMap((label, j) => {
      const meta = NAV_CAT_META[i].subs[j];
      const when = "when" in meta ? meta.when : undefined;
      if (when && !occasionDue(when, new Date())) return [];
      const theme = themeFromHref(meta.href);
      const books = theme ? MENU_BOOKS[theme] ?? [] : [];
      const rawOnly = books.length === 1 ? books[0] : undefined;
      const only = rawOnly !== undefined && (variant !== "cartoon" || CARTOON_COVER[rawOnly]) ? rawOnly : undefined;
      const bookTheme = only !== undefined ? CATALOG_THEMES[only] ?? theme : theme;
      // Tema e capa em destaque abrem o catálogo da categoria, não a ficha do livro.
      const href = `/catalogo#${NAV_CAT_META[i].id}`;
      return [{
        label,
        href,
        theme: bookTheme ?? theme,
        due: when ? nextOccasionDate(when, new Date()) : null,
      }];
    }).sort((a, b) => {
      if (a.due && b.due) return a.due.getTime() - b.due.getTime();
      if (a.due) return -1;
      if (b.due) return 1;
      return 0;
    }),
    feats: cat.feats.flatMap((label, j) => {
      const meta = NAV_CAT_META[i].feats[j];
      if (variant === "cartoon" && !CARTOON_COVER[meta.catalogI]) return [];
      return [{
        label,
        href: `/catalogo#${NAV_CAT_META[i].id}`,
        img: catalogCoverFile(meta.catalogI, lang, variant),
      }];
    }).slice(0, 4),
  }));
  const voceEeuCount = navCats.find((cat) => cat.id === "voce-e-eu")?.subs.length ?? 0;
  const menuCats = navCats.map((cat) => {
    if (cat.id !== "ocasioes" || cat.subs.length <= voceEeuCount) return cat;
    const open = cat.subs.filter((sub) => !sub.due);
    const dated = cat.subs.filter((sub) => sub.due);
    const room = Math.max(voceEeuCount - open.length, 0);
    return { ...cat, subs: [...dated.slice(0, room), ...open].slice(0, voceEeuCount) };
  });
  const shownCats = menuCats;
  const menuBooks = (theme: string) => (MENU_BOOKS[theme] ?? []).flatMap((i) => {
    if (variant === "cartoon" && !CARTOON_COVER[i]) return [];
    if (variant !== "cartoon" && isCartoonOnlyCover(i)) return [];
    const book = t.catalog[i];
    const img = CATALOG_IMGS[i];
    if (!book || !img) return [];
    return [{ label: book.t, href: `/catalogo#${catalogSectionId(theme)}`, img: catalogCoverFile(i, lang, variant) }];
  }).slice(0, 4);

  const featIcons = [IcSparkle, IcHeart, IcBook, IcGift];

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      setSession({ status: "out" });
      return;
    }
    setSession((cur) => (cur.status === "in" ? cur : { status: "loading" }));
    (async () => {
      try {
        const me = await api.me();
        if (cancelled) return;
        if (me.is_guest || !me.email_verified) {
          setSession({ status: "out" });
          return;
        }
        setSession({
          status: "in",
          name: sessionDisplayName(me.full_name, me.email),
          email: me.email,
          isOwner: Boolean(me.is_admin || me.is_owner),
        });
      } catch {
        if (!cancelled) setSession({ status: "out" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    const el = id ? document.getElementById(id) : null;
    if (!el) return;
    const offset = (headerRef.current?.getBoundingClientRect().height ?? 0) + 12;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top });
  }, []);

  useEffect(() => {
    const header = headerRef.current;
    const root = rootRef.current;
    if (!header || !root) return;
    const sync = () => {
      root.style.setProperty("--khead-h", `${Math.ceil(header.getBoundingClientRect().height)}px`);
    };
    sync();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(sync);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const els = rootRef.current?.querySelectorAll(".reveal") ?? [];
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    els.forEach((el, i) => { (el as HTMLElement).style.transitionDelay = `${(i % 3) * 0.1}s`; io.observe(el); });
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    try { localStorage.setItem("coverFont", coverFont); } catch { /* ignore */ }
  }, [coverFont]);

  useEffect(() => {
    if (!navOpen && openCat === null && !accountOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setNavOpen(false);
        setMobileCat(null);
        setMobileSub(null);
        setOpenCat(null);
        setSubHover(null);
        setFeatCat(null);
        setAccountOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen, openCat, accountOpen]);

  useEffect(() => {
    if (openCat === null && !navOpen && !accountOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node | null;
      if (accountOpen && (!target || !accountRef.current?.contains(target))) {
        setAccountOpen(false);
      }
      if (target && headerRef.current?.contains(target)) return;
      setOpenCat(null);
      setSubHover(null);
      setFeatCat(null);
      setNavOpen(false);
      setMobileCat(null);
      setMobileSub(null);
    };
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, [navOpen, openCat, accountOpen]);

  const closeNav = () => {
    setNavOpen(false);
    setMobileCat(null);
    setMobileSub(null);
    setOpenCat(null);
    setSubHover(null);
    setFeatCat(null);
    setAccountOpen(false);
  };

  function onLogout() {
    api.logout();
    setSession({ status: "out" });
    closeNav();
  }

  return (
    <div className={`kid cover-${coverFont}`} ref={rootRef} id="top">
      <div className="sky" aria-hidden>
        <IcStar className="dstar d1" /><IcStar className="dstar d2" /><IcSparkle className="dstar d3" /><IcStar className="dstar d4" />
        <svg className="dmoon m1" viewBox="0 0 24 24" aria-hidden><path d="M17 15A8 8 0 1 1 9 4a7 7 0 0 0 8 11z" fill="#f4b740" /></svg>
        <svg className="dmoon m2" viewBox="0 0 24 24" aria-hidden><path d="M17 15A8 8 0 1 1 9 4a7 7 0 0 0 8 11z" fill="#7fb2e3" /></svg>
      </div>

      <header className="khead" ref={headerRef}>
        <div className="khead-inner">
        <a href="#top" className="kbrand" data-testid="landing-brand"><img src={logo} alt="Story.R.Us" /></a>
        <div className="khead-main">
          <div className="khead-bar">
            <div className="khead-bar-inner">
              <nav className="kcats" aria-label={t.cats_label}>
                <div
                  className={`kcat${openCat === 0 ? " open" : ""}`}
                  onMouseEnter={() => setOpenCat(0)}
                  onMouseLeave={() => { setOpenCat(null); setSubHover(null); setFeatCat(null); }}
                >
                  <button
                    type="button"
                    className="kcat-btn"
                    style={{ "--cat": "#9b8cff" } as CSSProperties}
                    aria-expanded={openCat === 0}
                    aria-haspopup="true"
                    aria-controls="cat-panel"
                    onClick={() => {
                      const next = openCat === 0 ? null : 0;
                      setOpenCat(next);
                      if (next !== null) setFeatCat((cur) => cur ?? 0);
                    }}
                  >
                    <span className="kcat-dot" style={{ background: "#9b8cff", boxShadow: "0 0 10px #9b8cff" }} />
                    {t.cats_label}
                  </button>
                  <div className="kcat-panel kcat-panel-all" id="cat-panel">
                    <div className="kcat-groups">
                      {shownCats.map((cat, i) => (
                        <div
                          key={cat.id}
                          className="kcat-group"
                          style={{ "--group": cat.color } as CSSProperties}
                          onMouseEnter={() => {
                            setFeatCat(i);
                            setSubHover((cur) => (cur?.cat === i ? cur : null));
                          }}
                        >
                          <Link to={`/catalogo#${cat.id}`} className="kcat-group-name is-chip" onClick={closeNav}>
                            <span className="kcat-dot" style={{ background: cat.color, boxShadow: `0 0 8px ${cat.color}` }} />
                            {cat.name}
                          </Link>
                          <ul className="kcat-subs">
                            {cat.subs.map((sub, j) => (
                              <li key={sub.label} className={subHover?.cat === i && subHover.sub === j ? "on" : ""}>
                                <Link
                                  to={sub.href}
                                  onClick={closeNav}
                                  onMouseEnter={() => setSubHover({ cat: i, sub: j })}
                                  onFocus={() => setSubHover({ cat: i, sub: j })}
                                ><SubLabel label={sub.label} /></Link>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                    <div className="kcat-feats" data-testid="landing-cat-feats">
                      {(() => {
                        const hoverCat = subHover ? shownCats[subHover.cat] : featCat != null ? shownCats[featCat] : null;
                        const activeSub = subHover && hoverCat ? hoverCat.subs[subHover.sub] : null;
                        const activeTheme = activeSub?.theme ?? (activeSub ? themeFromHref(activeSub.href) : null);
                        const shown = (activeTheme ? menuBooks(activeTheme) : hoverCat?.feats ?? []).slice(0, 4);
                        const allHref = hoverCat ? `/catalogo#${hoverCat.id}` : "/catalogo";
                        return (
                          <>
                            {shown.map((feat) => (
                              <Link key={`${feat.href}-${feat.label}`} className="kcat-feat" to={feat.href} onClick={closeNav}>
                                <span className="kcat-feat-cover">
                                  <img src={exUrl(feat.img)} alt="" />
                                </span>
                                <span>{feat.label}</span>
                              </Link>
                            ))}
                            {activeTheme && shown.length === 0 ? <p className="kcat-empty">{t.cat_empty}</p> : null}
                            <Link to={allHref} className="kbtn kbtn-go kcat-all" onClick={closeNav}>{t.view_all}</Link>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </div>
                <a href="#como" className="kcat-btn" style={{ "--cat": "#7aa2ff" } as CSSProperties} onClick={closeNav}>
                  <span className="kcat-dot" style={{ background: "#7aa2ff", boxShadow: "0 0 10px rgba(122,162,255,.9)" }} />
                  {t.hiw_title}
                </a>
                <a href="#passo" className="kcat-btn" style={{ "--cat": "#f08a4b" } as CSSProperties} onClick={closeNav}>
                  <span className="kcat-dot" style={{ background: "#f08a4b", boxShadow: "0 0 10px rgba(240,138,75,.9)" }} />
                  {t.passo_title}
                </a>
                <Link to={variant === "cartoon" ? "/" : "/cartoon"} className="kcat-btn" style={{ "--cat": variant === "cartoon" ? "#7aa2ff" : "#3ecf8e" } as CSSProperties} onClick={closeNav}>
                  <span className="kcat-dot" style={{ background: variant === "cartoon" ? "#7aa2ff" : "#3ecf8e", boxShadow: variant === "cartoon" ? "0 0 10px rgba(122,162,255,.95)" : "0 0 10px rgba(62,207,142,.95)" }} />
                  {variant === "cartoon" ? t.realistic_link : t.cartoon_link}
                </Link>
                <a href="#videos" className="kcat-btn" style={{ "--cat": "#e07a9a" } as CSSProperties} onClick={closeNav}>
                  <span className="kcat-dot" style={{ background: "#e07a9a", boxShadow: "0 0 10px rgba(224,122,154,.9)" }} />
                  {t.videos_link}
                </a>
                <a href="#reviews" className="kcat-btn" style={{ "--cat": "#f4b740" } as CSSProperties} onClick={closeNav}>
                  <span className="kcat-dot" style={{ background: "#f4b740", boxShadow: "0 0 10px rgba(244,183,64,.95)" }} />
                  {t.reviews_link}
                </a>
              </nav>
            </div>
          </div>
        </div>
        <div className="khead-actions">
          <div className="khead-utils">
            <button className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={t.a11y_theme}>
              {theme === "dark" ? <IcSun className="ti" /> : <IcMoon className="ti" />}
              <span className="theme-toggle-label">{theme === "dark" ? t.theme_to_light : t.theme_to_dark}</span>
            </button>
            <div className="lang" role="group" aria-label="Idioma / Language / Idioma" data-testid="landing-lang">
              <button className={lang === "pt" ? "on" : ""} onClick={() => setLang("pt")} data-testid="landing-lang-pt">PT</button>
              <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")} data-testid="landing-lang-en">EN</button>
              <button className={lang === "es" ? "on" : ""} onClick={() => setLang("es")} data-testid="landing-lang-es">ES</button>
            </div>
            <div className="khead-links" data-testid="landing-header-auth">
              {signedIn ? (
                <>
                  <div className="khead-account" ref={accountRef}>
                    <button
                      type="button"
                      className={`khead-user${accountOpen ? " is-open" : ""}`}
                      data-testid="landing-header-user"
                      aria-expanded={accountOpen}
                      aria-haspopup="menu"
                      aria-controls="landing-account-menu"
                      onClick={() => setAccountOpen((open) => !open)}
                    >
                      <span>{session.name}</span>
                      <IcChevron className="khead-user-chev" />
                    </button>
                    {accountOpen && (
                      <div
                        id="landing-account-menu"
                        className="khead-account-menu"
                        role="menu"
                        data-testid="landing-header-account-menu"
                      >
                        <a
                          className="khead-account-item"
                          role="menuitem"
                          href="/pedidos"
                          data-testid="landing-header-orders"
                          onClick={() => setAccountOpen(false)}
                        >
                          {t.orders}
                        </a>
                        {isOwner && (
                          <a
                            className="khead-account-item"
                            role="menuitem"
                            href="/usuarios"
                            data-testid="landing-header-users"
                            onClick={() => setAccountOpen(false)}
                          >
                            {t.users}
                          </a>
                        )}
                        <Link
                          className="khead-account-item"
                          role="menuitem"
                          to="/conta"
                          data-testid="landing-header-account"
                          onClick={() => setAccountOpen(false)}
                        >
                          {t.account}
                        </Link>
                        <button
                          type="button"
                          className="khead-account-item"
                          role="menuitem"
                          data-testid="landing-header-logout"
                          onClick={onLogout}
                        >
                          {t.logout}
                        </button>
                      </div>
                    )}
                  </div>
                  <Link to="/app" className="kbtn kbtn-primary" data-testid="landing-header-cta">
                    {headerCtaLabel}
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/entrar" className="kbtn kbtn-login" data-testid="landing-header-login">{t.cta_login}</Link>
                  <Link to={createHref} className="kbtn kbtn-primary" data-testid="landing-header-cta">{headerCtaLabel}</Link>
                </>
              )}
            </div>
          </div>
          <button
            className="khamb"
            aria-label={t.a11y_menu}
            aria-expanded={navOpen}
            aria-controls="site-menu"
            data-testid="landing-menu"
            onClick={() => setNavOpen((v) => !v)}
          >☰</button>
        </div>
        <nav id="site-menu" className={`kmobile${navOpen ? " open" : ""}`} data-testid="landing-site-menu">
          <div className="kmobile-section">
            <p className="kmobile-label">{t.cats_label}</p>
            {shownCats.map((cat, i) => (
              <div key={cat.id} className={`kmobile-cat${mobileCat === i ? " open" : ""}`} style={{ "--group": cat.color } as CSSProperties}>
                <div className="kmobile-cat-btn">
                  <Link to={`/catalogo#${cat.id}`} onClick={closeNav}>
                    <span className="kcat-dot" style={{ background: cat.color }} />
                    {cat.name}
                  </Link>
                  <button
                    type="button"
                    className="kmobile-cat-toggle"
                    aria-expanded={mobileCat === i}
                    aria-controls={`mobile-cat-${i}`}
                    aria-label={cat.name}
                    onClick={() => {
                      setMobileCat(mobileCat === i ? null : i);
                      setMobileSub(null);
                    }}
                  >
                    <IcChevron className="faq-chev" />
                  </button>
                </div>
                <div className="kmobile-subs" id={`mobile-cat-${i}`}>
                  <div className="kmobile-subs-inner">
                    {mobileCat === i && mobileSub?.cat !== i && cat.feats.length > 0 ? (
                      <div className="kmobile-feats" data-testid={`landing-mobile-feats-${cat.id}`}>
                        {cat.feats.map((feat) => (
                          <Link key={`${feat.href}-${feat.label}`} className="kcat-feat" to={feat.href} onClick={closeNav}>
                            <span className="kcat-feat-cover">
                              <img src={exUrl(feat.img)} alt="" />
                            </span>
                            <span>{feat.label}</span>
                          </Link>
                        ))}
                      </div>
                    ) : null}
                    {cat.subs.map((sub, j) => {
                      const subName = sub.label.split(" · ")[0];
                      const subOpen = mobileSub?.cat === i && mobileSub.sub === j;
                      const subBooks = sub.theme ? menuBooks(sub.theme) : [];
                      return (
                        <div key={sub.label} className={`kmobile-sub${subOpen ? " on" : ""}`}>
                          <div className="kmobile-sub-row">
                            <Link to={sub.href} onClick={closeNav}><SubLabel label={sub.label} /></Link>
                            <button
                              type="button"
                              className="kmobile-sub-toggle"
                              aria-expanded={subOpen}
                              aria-controls={`mobile-sub-${i}-${j}`}
                              aria-label={subName}
                              onClick={() => setMobileSub(subOpen ? null : { cat: i, sub: j })}
                            >
                              <IcChevron className="faq-chev" />
                            </button>
                          </div>
                          {subOpen ? (
                            <div className="kmobile-feats" id={`mobile-sub-${i}-${j}`} data-testid={`landing-mobile-feats-${cat.id}-${j}`}>
                              {subBooks.length === 0 ? <p className="kmobile-empty">{t.cat_empty}</p> : subBooks.map((feat) => (
                                <Link key={`${feat.href}-${feat.label}`} className="kcat-feat" to={feat.href} onClick={closeNav}>
                                  <span className="kcat-feat-cover">
                                    <img src={exUrl(feat.img)} alt="" />
                                  </span>
                                  <span>{feat.label}</span>
                                </Link>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
            <Link to="/catalogo" className="kmobile-all" onClick={closeNav}>{t.view_all}</Link>
          </div>
          <div className="kmobile-section">
            <p className="kmobile-label">{t.quick_links}</p>
            <a className="kmobile-link" href="#como" onClick={closeNav}>{t.hiw_title}</a>
            <a className="kmobile-link" href="#passo" onClick={closeNav}>{t.passo_title}</a>
            <Link className="kmobile-link" to={variant === "cartoon" ? "/" : "/cartoon"} onClick={closeNav}>{variant === "cartoon" ? t.realistic_link : t.cartoon_link}</Link>
            <a className="kmobile-link" href="#videos" onClick={closeNav}>{t.videos_link}</a>
            <a className="kmobile-link" href="#reviews" onClick={closeNav}>{t.reviews_link}</a>
            <a className="kmobile-link" href="#catalogo" onClick={closeNav}>{t.nav[1]}</a>
            <a className="kmobile-link" href="#faq" onClick={closeNav}>{t.nav[3]}</a>
          </div>
          <div
            className={`kmobile-auth${signedIn ? " is-signed" : ""}`}
            data-testid="landing-mobile-auth"
          >
            {signedIn ? (
              <>
                <span className="khead-user" data-testid="landing-mobile-user">
                  {session.name}
                </span>
                <a className="kutil" href="/pedidos" data-testid="landing-mobile-orders" onClick={closeNav}>
                  {t.orders}
                </a>
                {isOwner && (
                  <a className="kutil" href="/usuarios" data-testid="landing-mobile-users" onClick={closeNav}>
                    {t.users}
                  </a>
                )}
                <Link to="/conta" className="kutil" data-testid="landing-mobile-account" onClick={closeNav}>
                  {t.account}
                </Link>
                <button
                  type="button"
                  className="kutil"
                  data-testid="landing-mobile-logout"
                  onClick={onLogout}
                >
                  {t.logout}
                </button>
                <Link to="/app" className="kbtn kbtn-primary" data-testid="landing-mobile-cta" onClick={closeNav}>
                  {headerCtaLabel}
                </Link>
              </>
            ) : (
              <>
                <Link to="/entrar" className="kbtn kbtn-login" data-testid="landing-mobile-login" onClick={closeNav}>{t.cta_login}</Link>
                <Link to={createHref} className="kbtn kbtn-primary" data-testid="landing-mobile-cta" onClick={closeNav}>{headerCtaLabel}</Link>
              </>
            )}
          </div>
        </nav>
        </div>
      </header>

      {variant === "cartoon" ? (
        <div className="ksection site-back-wrap">
          <SiteBackNav />
        </div>
      ) : null}

      {/* HERO — proposta de valor + faixa de livros */}
      <section className="kbanner-hero" aria-label={t.hero_sign}>
        <div className="khero-intro">
          <h1>{t.h_pre}<em className="g1">{t.w1}</em>{t.c1}<em className="g2">{t.w2}</em>{t.h_suf}</h1>
          <span className="keyebrow"><IcSparkle className="ei" /> {t.hero_sign}</span>
        </div>
        <div className="hero-carousel" aria-label={t.book_carousel}>
          <div className="hero-carousel-track">
            {[0, 1].map((copy) => heroStrip.map((book, seriesIndex) => {
              const shots = [book.cover[lang], book.page[lang], book.photo[lang]];
              const seriesOn = Math.floor(heroPick / 3) === seriesIndex;
              return (
                <div
                  className={`hero-slide${seriesOn ? " on" : ""}${seriesIndex === 0 ? " is-lead" : ""}`}
                  key={`${copy}-${book.name}-${seriesIndex}`}
                  aria-hidden={copy === 1 ? true : undefined}
                >
                  <span className="hero-slide-frame">
                    {shots.map((src, part) => {
                      const i = seriesIndex * 3 + part;
                      return (
                        <button
                          type="button"
                          className={`hero-shot${i === heroPick ? " on" : ""}`}
                          key={src}
                          aria-pressed={copy === 0 ? i === heroPick : undefined}
                          aria-label={book.name}
                          tabIndex={copy === 1 ? -1 : 0}
                          onClick={() => setHeroPick(i)}
                          data-testid={copy === 0 ? `landing-hero-pick-${i}` : undefined}
                        >
                          <img
                            src={exUrl(src)}
                            alt=""
                            data-testid={copy === 0 ? `landing-hero-slide-${i}` : undefined}
                          />
                        </button>
                      );
                    })}
                  </span>
                </div>
              );
            }))}
          </div>
        </div>
        <div className="khero-flipbook">
          <FlipBook
            key={lang}
            pages={heroPages}
            index={Math.min(heroPick, Math.max(heroPages.length - 1, 0))}
            onIndex={setHeroPick}
            labels={flipLabels}
          />
        </div>
        <div className="khero-after">
          <span className="keyebrow"><IcSparkle className="ei" /> {t.eyebrow}</span>
          <Link to={createHref} className="kbtn kbtn-primary" data-testid="landing-hero-cta">{t.hero_cta}</Link>
        </div>
      </section>

      {/* COMO FUNCIONA + DICAS */}
      <section className="ksection ksection-como" id="como">
        <div className="como-panel reveal">
          <h2 className="ktitle">{t.hiw_title}</h2>
          <div className="howex">
            {hiwSteps.map((h, i) => {
              return (
              <Fragment key={h.t}>
                <figure className="howex-card howex-card-scene">
                  <div className="howex-lead">
                    <h3>{h.t}</h3>
                  </div>
                  <div className="howex-media">
                    <img src={exUrl(howImgs[i])} alt={h.t} loading="lazy" />
                    <span className="howex-num">{i + 1}</span>
                  </div>
                  <figcaption>
                    <p>{h.p}</p>
                  </figcaption>
                </figure>
                {i < hiwSteps.length - 1 && <span className="howex-arrow" aria-hidden><IcArrow /></span>}
              </Fragment>
              );
            })}
          </div>
        </div>
      </section>

      <section className="ksection ksection-como" id="passo">
        <div className="como-panel reveal">
          <h2 className="ktitle">{t.passo_title}</h2>
          <div className="howex">
            {t.passo.map((h, i) => (
              <Fragment key={h.t}>
                <figure className="howex-card howex-card-scene">
                  <div className="howex-lead">
                    <h3>{h.t}</h3>
                  </div>
                  <div className="howex-media">
                    <img src={exUrl(PASSO_IMGS[i])} alt={h.t} loading="lazy" />
                    <span className="howex-num">{i + 1}</span>
                  </div>
                  <figcaption>
                    <p>{h.p}</p>
                  </figcaption>
                </figure>
                {i < t.passo.length - 1 && <span className="howex-arrow" aria-hidden><IcArrow /></span>}
              </Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* NOSSOS LIVROS */}
      <section className="ksection" id="catalogo">
        <h2 className="ktitle reveal">{t.cat_title}</h2>
        <p className="ksub reveal">{t.cat_sub}</p>
        <div className="cat-grid">
          {catalogBooks.map((c) => (
            <CatalogBookCard
              key={c.t}
              book={c}
              lang={lang}
              personalize={t.personalize}
              modo={variant === "cartoon" ? "cartoon" : "realista"}
            />
          ))}
        </div>
      </section>

      {/* NOSSA PROMESSA — logo abaixo dos livros */}
      <section className="ksection promise-section" id="promessa">
        <h2 className="ktitle reveal promise-heading">
          {lang === "pt" ? (
            <>
              Um <span className="promise-mark">Presente</span> Personalizado para Eternizar Momentos Inesquecíveis.
            </>
          ) : t.promise_title}
        </h2>
        <p className="ksub reveal">{t.promise_sub}</p>
        <div className="promise-grid">
          {t.promise.map((pr, i) => {
            const Icon = PROMISE_ICONS[i];
            return (
              <div className="promise-card reveal" key={pr.t}>
                <span className="promise-ic"><Icon /></span>
                <h3>{pr.t}</h3>
                <p>{pr.p}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* VÍDEOS NARRADOS */}
      <section className="ksection" id="videos">
        <h2 className="ktitle reveal">{t.vid_title}</h2>
        <p className="ksub reveal">{t.vid_sub}</p>
        <div className="vid-grid">
          {t.videos.map((v, i) => {
            const src = VIDEO_SRCS[i];
            const canPlay = Boolean(src);
            return (
              <figure className="vid-card reveal" key={v.t}>
                <div className="vid-thumb">
                  {canPlay && src ? (
                    <AutoMutedVideo key={src} src={exUrl(src)} poster={exUrl(VIDEO_IMGS[i])} />
                  ) : (
                    <button
                      type="button"
                      className="vid-play-btn"
                      aria-label={`${v.t} — ${t.vid_soon}`}
                      disabled
                    >
                      <img src={exUrl(VIDEO_IMGS[i])} alt={v.t} loading="lazy" />
                      <span className="vid-dur">{t.vid_soon}</span>
                    </button>
                  )}
                </div>
                <figcaption><h3>{v.t}</h3><p>{v.p}</p></figcaption>
              </figure>
            );
          })}
        </div>
        <div className="vid-cta"><Link to={createHref} className="kbtn kbtn-primary big">{t.vid_cta}</Link></div>
      </section>

      {/* AVALIAÇÕES */}
      <section className="ksection" id="reviews">
        <h2 className="ktitle reveal">{t.rev_title}</h2>
        <p className="ksub reveal">{t.rev_sub}</p>
        <div className="rev-carousel reveal" aria-label={t.rev_title}>
          <div className="rev-carousel-track">
            {[0, 1].map((copy) => reviewPhotos.map((b, i) => (
              <figure className="rev-photo" key={`${copy}-${b.tab}`} aria-hidden={copy === 1 ? true : undefined}>
                <span className="rev-photo-frame">
                  <img
                    src={exUrl(b.tab)}
                    alt={copy === 0 ? b.name : ""}
                    loading="lazy"
                    data-testid={copy === 0 ? `landing-review-cover-${i}` : undefined}
                  />
                </span>
                <figcaption data-testid={copy === 0 ? `landing-review-name-${i}` : undefined}>{b.name}</figcaption>
              </figure>
            )))}
          </div>
        </div>
        <div className="rev-grid">
          {t.reviews.map((r) => (
            <figure className="rev-card reveal" key={r.name}>
              <div className="rev-stars">★★★★★</div>
              <blockquote>{r.q}</blockquote>
              <figcaption><span className="rev-av">{r.name.charAt(0)}</span>{r.name}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="ksection" id="faq">
        <h2 className="ktitle reveal">{t.faq_title}</h2>
        <p className="ksub reveal">{t.faq_sub}</p>
        <div className="reveal"><Faq items={t.faq} /></div>
      </section>

      {/* FAIXA DE ATRIBUTOS */}
      <section className="featurebar" id="presente">
        {t.features.map((f, i) => {
          const Icon = featIcons[i];
          return (<div className="feat" key={f}><Icon className="feat-ic" /><span>{f}</span></div>);
        })}
      </section>

      {/* CTA */}
      <section className="kband" id="familias">
        <IcSparkle className="twk b1" /><IcStar className="twk b2" />
        <h2>{t.band_title}</h2><p>{t.band_sub}</p>
        <Link to={createHref} className="kbtn kbtn-primary big">{bandCtaLabel}</Link>
      </section>

      {/* FOOTER */}
      <footer className="kfoot">
        <div className="kfoot-links">
          <div className="kfoot-nav">
            {t.nav.map((label, i) => { const Icon = FOOT_ICONS[i]; return (<a key={label} href={navHrefs[i]}><Icon className="ni" />{label}</a>); })}
          </div>
          <div className="kfoot-contacts">
            <a href={`mailto:${CONTACT_EMAIL}`} className="kfoot-contact">
              <IcMail className="ni" />
              <span>{CONTACT_EMAIL}</span>
            </a>
            <a
              href={`https://www.instagram.com/${CONTACT_INSTA}/`}
              className="kfoot-contact"
              target="_blank"
              rel="noopener noreferrer"
            >
              <IcInstagram className="ni" />
              <span>@{CONTACT_INSTA}</span>
            </a>
            <Link to="/privacidade" className="kfoot-contact">{t.privacy_link}</Link>
            <Link to="/termos" className="kfoot-contact">{t.terms_link}</Link>
          </div>
        </div>
        <p className="kfoot-tag"><IcHeart className="ci" /> {t.tagline}</p>
        <p className="kfoot-copy">{t.foot_copy}</p>
      </footer>
    </div>
  );
}
