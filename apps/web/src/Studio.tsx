import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Job, Project } from "./types";
import { demoIdFromSearch, getDemoExample } from "./demoExample";
import { themePreset } from "./studioPreset";
import {
  ageLimit,
  castFromQuery,
  emptyCast,
  subjectCode,
  subjectCopy,
  type StudioGender,
  type StudioWho,
} from "./studioSubject";
import logo from "./assets/logo.png";
import { SiteBackNav } from "./SiteBackNav";
import type { StudioAssets } from "./studio/assets";
import { PreviewTrio } from "./studio/PreviewTrio";
import {
  previewChainSteps,
  previewEtaMinutes,
  previewImageActivity,
  type PreviewStepId,
} from "./studio/previewSteps";
import { useStudioPolling } from "./studio/useStudioPolling";
import type { StudioCopy } from "./studio/i18n";
import {
  StudioLangProvider,
  useStudioI18n,
  useStudioLangState,
} from "./studio/useStudioI18n";
import "./landing.css";
import "./studio.css";

export { ProgressList } from "./studio/ProgressList";

const PHOTO_LIMIT = 8;

function previewStepLabel(t: StudioCopy, id: PreviewStepId): string {
  if (id === "AVATAR") return t.previewStepCharacter;
  if (id === "STORY") return t.previewStepStory;
  return t.previewStepImages;
}

function previewStepHint(
  t: StudioCopy,
  id: PreviewStepId,
  imageActivity: ReturnType<typeof previewImageActivity> | null,
): string {
  if (id === "AVATAR") return t.previewStepCharacterHint;
  if (id === "STORY") return t.previewStepStoryHint;
  if (imageActivity === "cover") return t.previewImageCover;
  if (imageActivity === "page") return t.previewImagePage;
  if (imageActivity === "hand") return t.previewImageHand;
  if (imageActivity === "book") return t.previewImageBook;
  return t.previewStepImagesHint;
}

function previewStepStateLabel(t: StudioCopy, state: "wait" | "queued" | "now" | "done"): string {
  if (state === "done") return t.previewStepDone;
  if (state === "now") return t.previewStepNow;
  if (state === "queued") return t.previewStepQueued;
  return t.previewStepWait;
}

type StoryPageBlock = { kind: "title" | "page" | "body"; label: string; lines: string[] };

/** Collapse soft line-breaks into paragraphs so justified page text stays full-width. */
function verseLines(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((para) => para.replace(/\s*\n\s*/g, " ").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

/** Split story text into titled pages when markers like "Página 1:" / "Título:" exist. */
function parseStoryPages(text: string): StoryPageBlock[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  const parts = trimmed
    .split(/(?=(?:T[íi]tulo\s*:|P[aá]gina\s+\d+\s*:))/i)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length <= 1 && !/^(?:T[íi]tulo\s*:|P[aá]gina\s+\d+\s*:)/i.test(trimmed)) {
    return [{ kind: "body", label: "", lines: verseLines(trimmed) }];
  }
  return parts.map((part) => {
    const titleMatch = part.match(/^T[íi]tulo\s*:\s*([\s\S]*)$/i);
    if (titleMatch) {
      return { kind: "title" as const, label: "Título", lines: verseLines(titleMatch[1]) };
    }
    const pageMatch = part.match(/^(P[aá]gina\s+\d+)\s*:\s*([\s\S]*)$/i);
    if (pageMatch) {
      return { kind: "page" as const, label: pageMatch[1], lines: verseLines(pageMatch[2]) };
    }
    return { kind: "body" as const, label: "", lines: verseLines(part) };
  });
}

function photoKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function previewUrl(file: File): string {
  if (typeof URL.createObjectURL !== "function") return "";
  return URL.createObjectURL(file);
}

function releasePreview(url: string) {
  if (url && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(url);
}

function imageFiles(list: Iterable<File>): File[] {
  return [...list].filter(
    (file) => file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|heic|heif)$/i.test(file.name),
  );
}

function unsupportedPhoto(file: File): boolean {
  const type = (file.type || "").toLowerCase();
  return type === "image/heic" || type === "image/heif" || /\.(heic|heif)$/i.test(file.name);
}

function oneLine(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function validEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

type FieldKey =
  | "name"
  | "age"
  | "title"
  | "theme"
  | "alsoName"
  | "gender"
  | "alsoGender"
  | "photo"
  | "consent"
  | "clientName"
  | "clientEmail"
  | "clientPhone"
  | "clientAddress";

const BOOK_FIELD_ORDER: FieldKey[] = [
  "name",
  "age",
  "gender",
  "alsoName",
  "alsoGender",
  "title",
  "theme",
  "photo",
  "consent",
  "clientName",
  "clientEmail",
  "clientPhone",
  "clientAddress",
];

const CLIENT_FIELD_ORDER: FieldKey[] = ["clientName", "clientEmail", "clientPhone", "clientAddress"];

function focusMissingField(key: FieldKey) {
  const el = document.getElementById(`studio-field-${key}`);
  if (!el) return;
  if (typeof el.scrollIntoView === "function") {
    try {
      el.scrollIntoView({ block: "center" });
    } catch {
      /* jsdom */
    }
  }
  if (typeof el.focus === "function") {
    try {
      el.focus({ preventScroll: true });
    } catch {
      el.focus();
    }
  }
}

/* ---------------- ícones (SVG, sem emojis) ---------------- */
type IconProps = { className?: string };
const ICON_STROKE = 2.2;
const Svg = ({ className, children }: { className?: string; children: ReactNode }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={ICON_STROKE}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    {children}
  </svg>
);
const IcSun = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="12" cy="12" r="4.2" />
    <path d="M12 2.5v2.4M12 19.1v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7" />
  </Svg>
);
const IcMoon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M20 15A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 11z" />
  </Svg>
);

export function Studio({ onLogout }: { onLogout?: () => void }) {
  const langState = useStudioLangState();
  return (
    <StudioLangProvider value={langState}>
      <StudioInner onLogout={onLogout} />
    </StudioLangProvider>
  );
}

function StudioInner({ onLogout }: { onLogout?: () => void }) {
  const { lang, setLang, t, langs } = useStudioI18n();
  const [accountKind, setAccountKind] = useState<"unknown" | "guest" | "account">("unknown");
  const [accountEmail, setAccountEmail] = useState("");
  const [accountName, setAccountName] = useState("");
  const [isOwner, setIsOwner] = useState(false);
  const [clientDone, setClientDone] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [photos, setPhotos] = useState<{ key: string; file: File; url: string }[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [childName, setChildName] = useState("");
  const [childAge, setChildAge] = useState<string>("");
  const [bookTitle, setBookTitle] = useState("");
  const [themeText, setThemeText] = useState("");
  const [temaId, setTemaId] = useState("");
  const [onlyName, setOnlyName] = useState(false);
  const [bookSize, setBookSize] = useState<"M" | "P">("M");
  const [coverType, setCoverType] = useState<"soft" | "hard">("hard");
  const [extraNames, setExtraNames] = useState("");
  const [castWho, setCastWho] = useState<StudioWho>("child");
  const [gender, setGender] = useState<StudioGender | null>("f");
  const [alsoWho, setAlsoWho] = useState<StudioWho | null>(null);
  const [alsoGender, setAlsoGender] = useState<StudioGender | null>(null);
  const [alsoName, setAlsoName] = useState("");
  const [askGender, setAskGender] = useState(true);
  const alsoHero = useRef<string | null>(null);
  const [orderSent, setOrderSent] = useState(false);
  const [artMode, setArtMode] = useState<"realista" | "cartoon">("realista");
  const [dedication, setDedication] = useState("");
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientAddress, setClientAddress] = useState("");
  const [clientNotes, setClientNotes] = useState("");
  const [assets, setAssets] = useState<StudioAssets | null>(null);
  const [storyDraft, setStoryDraft] = useState("");
  const [photoNotes, setPhotoNotes] = useState("");
  const [changesSent, setChangesSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState<Partial<Record<FieldKey, true>>>({});
  const [isDemo, setIsDemo] = useState(() => Boolean(demoIdFromSearch()));
  const titlePreset = useRef<{ hero: string; title: string } | null>(null);
  const titleTouched = useRef(false);
  const storyTouched = useRef(false);
  const presetApplied = useRef(false);
  const [mediaConsent, setMediaConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const startLock = useRef(false);
  const [colorTheme, setColorTheme] = useState<"light" | "dark">(() => {
    try {
      const s = localStorage.getItem("theme");
      if (s === "light" || s === "dark") return s;
    } catch {
      /* ignore */
    }
    return "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", colorTheme);
  }, [colorTheme]);

  useEffect(() => {
    if (!isDemo) return;
    const demo = getDemoExample();
    setChildName(demo.childName);
    setChildAge(demo.childAge);
    setBookTitle(demo.bookTitle);
    setThemeText(demo.themeText);
    setDedication(demo.dedication);
    setProject(demo.project);
    setAssets(demo.assets);
    setStoryDraft(demo.project.story_text ?? "");
    setOrderSent(true);
    setJobs([]);
  }, [isDemo]);

  useEffect(() => {
    if (presetApplied.current || isDemo) return;
    const q = new URLSearchParams(window.location.search);
    const tema = q.get("tema");
    const titulo = q.get("titulo");
    const historia = q.get("historia");
    const heroi = q.get("heroi");
    if (!tema && !titulo && !historia) return;
    presetApplied.current = true;
    if (tema) setTemaId(tema);
    if (q.get("tamanho") === "P" || q.get("tamanho") === "M") setBookSize(q.get("tamanho") as "M" | "P");
    const capa = (q.get("capa") || "").toLowerCase();
    if (capa === "soft" || capa === "hard") setCoverType(capa);
    if (q.get("modo") === "cartoon") setArtMode("cartoon");
    const onlyTheme = q.get("campos") === "tema" || q.get("campos") === "nome";
    if (q.get("campos") === "nome") setOnlyName(true);
    const cast = tema || titulo || historia ? castFromQuery(q) : emptyCast();
    setCastWho(cast.who);
    setGender(cast.gender ?? "f");
    setAlsoWho(cast.also?.who ?? null);
    setAlsoGender(cast.also?.gender ?? null);
    setAskGender(cast.askGender);
    alsoHero.current = cast.also?.hero ?? null;
    const fallback = tema ? themePreset(tema, lang) : null;
    const themeBody = historia || fallback?.theme || "";
    if (themeBody) setThemeText(themeBody);
    if (q.get("campos") === "nome" && titulo) {
      setBookTitle(titulo);
      if (heroi) titlePreset.current = { hero: heroi, title: titulo };
    }
    if (onlyTheme) return;
    const title = titulo || fallback?.title || "";
    if (title) setBookTitle(title);
    if (heroi && titulo) titlePreset.current = { hero: heroi, title: titulo };
  }, [isDemo, lang]);

  const refreshMe = useCallback(async () => {
    try {
      const me = await api.me();
      const registered = !me.is_guest && me.email_verified;
      setAccountKind(registered ? "account" : me.is_guest ? "guest" : "unknown");
      setAccountEmail(me.email);
      setAccountName(me.full_name?.trim() || "");
      setIsOwner(Boolean(me.is_admin || me.is_owner));
      if (registered) {
        const addressLine = [
          me.street,
          me.number,
          me.complement,
          me.district,
          me.city,
          me.state,
          me.country,
          me.postal_code,
        ]
          .map((p) => (p || "").trim())
          .filter(Boolean)
          .join(", ");
        if (me.full_name?.trim()) setClientName(me.full_name.trim());
        setClientEmail(me.email);
        if (me.phone?.trim()) setClientPhone(me.phone.trim());
        if (addressLine) setClientAddress(addressLine);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const getStoryBrief = useCallback(() => {
    const name = childName.trim();
    const title = bookTitle.trim();
    const theme = themeText.trim();
    const genderBit = gender === "f" ? "feminino" : gender === "m" ? "masculino" : "";
    const companion = alsoName.trim();
    const cm = bookSize === "P" ? "15×15 cm" : "20×20 cm";
    const look =
      artMode === "cartoon"
        ? "Estilo cartoon premium, traços desenhados, formas arredondadas, sem anime nem chibi."
        : "Estilo editorial suavemente realista: pele com luz suave, íris na fração da foto, cabelo fio a fio, sem cartoon.";
    const format = `Livro quadrado ${cm}, corte reto, página em sangria total, estrofe curta na faixa calma. ${look}`;
    if (lang === "en") {
      return (
        `Invent an original children's story. The book title must be: "${title}". ` +
        `Theme and ideas from the guardian: ${theme}. ` +
        (name ? `The hero's name is ${name}${genderBit ? ` (${genderBit})` : ""}. ` : "") +
        (companion ? `Also include ${companion}. ` : "") +
        format
      );
    }
    if (lang === "es") {
      return (
        `Inventa una historia infantil original. El título del libro debe ser: "${title}". ` +
        `Tema e ideas del responsable: ${theme}. ` +
        (name ? `El protagonista se llama ${name}${genderBit ? ` (${genderBit})` : ""}. ` : "") +
        (companion ? `También entra ${companion}. ` : "") +
        format
      );
    }
    return (
      `Invente uma história infantil original. O título do livro deve ser: "${title}". ` +
      `Tema e ideias do responsável: ${theme}. ` +
      (name ? `O protagonista se chama ${name}${genderBit ? ` e é do gênero ${genderBit}` : ""}. ` : "") +
      (companion ? `Também entra ${companion}. ` : "") +
      format
    );
  }, [alsoName, artMode, bookSize, bookTitle, childName, gender, lang, themeText]);

  const previewChainActive = jobs.some(
    (j) =>
      (j.type === "AVATAR" || j.type === "STORY" || j.type === "EBOOK" || j.type === "VIDEO") &&
      (j.status === "PENDING" || j.status === "RUNNING") &&
      Boolean(j.result?.payload?.preview_chain),
  );
  const previewFailedJob = jobs.find(
    (j) =>
      (j.type === "AVATAR" || j.type === "STORY" || j.type === "EBOOK") &&
      j.status === "FAILED" &&
      Boolean(j.result?.payload?.preview_chain),
  );
  const previewReady = Boolean(
    project?.story_text?.trim() &&
      (assets?.cover_url || assets?.page_images?.[0] || assets?.in_hand_url),
  );
  const previewFailed = Boolean(previewFailedJob) && !previewChainActive;

  useStudioPolling({
    project,
    jobs,
    setProject,
    setJobs,
    setAssets,
    isDemo,
    keepWatching: orderSent && !isDemo && !previewReady && !previewFailed && !error,
  });

  useEffect(() => {
    if (!project?.story_text || storyTouched.current) return;
    setStoryDraft(project.story_text);
  }, [project?.story_text]);

  function clearMissing(key: FieldKey) {
    setMissing((cur) => {
      if (!cur[key]) return cur;
      const next = { ...cur };
      delete next[key];
      return next;
    });
  }

  function buyerInfo() {
    const signedIn = accountKind === "account";
    return {
      name: signedIn ? oneLine(accountName || clientName || accountEmail) : oneLine(clientName),
      email: signedIn ? oneLine(accountEmail || clientEmail) : oneLine(clientEmail),
      phone: oneLine(clientPhone),
      address: oneLine(clientAddress),
    };
  }

  function buyerGaps(target: Partial<Record<FieldKey, true>>) {
    const buyer = buyerInfo();
    if (!buyer.name) target.clientName = true;
    if (!validEmail(buyer.email)) target.clientEmail = true;
    if (!buyer.phone) target.clientPhone = true;
    if (!buyer.address) target.clientAddress = true;
  }

  function applyMissing(next: Partial<Record<FieldKey, true>>, order: FieldKey[]) {
    setMissing(next);
    const first = order.find((key) => next[key]);
    if (!first) return false;
    window.setTimeout(() => focusMissingField(first), 0);
    return true;
  }

  function formReady(agreed = mediaConsent) {
    if (isDemo) return false;
    const next: Partial<Record<FieldKey, true>> = {};
    if (!childName.trim()) next.name = true;
    if (childAge.trim() === "") next.age = true;
    if (alsoWho && !alsoName.trim()) next.alsoName = true;
    if (!onlyName) {
      if (!bookTitle.trim()) next.title = true;
      if (!themeText.trim()) next.theme = true;
    }
    if (askGender && !gender) next.gender = true;
    if (askGender && alsoWho && !alsoGender) next.alsoGender = true;
    buyerGaps(next);
    if (photos.length === 0) next.photo = true;
    if (!agreed) next.consent = true;
    if (applyMissing(next, BOOK_FIELD_ORDER)) {
      setError(null);
      return false;
    }
    setError(null);
    return true;
  }

  async function start(agreed = mediaConsent) {
    if (startLock.current || busy) return;
    if (!formReady(agreed)) return;
    if (photos.some((item) => unsupportedPhoto(item.file))) {
      setError(t.errPhotoFormat);
      return;
    }
    const buyer = buyerInfo();
    const buyerNotes = oneLine(clientNotes);
    startLock.current = true;
    setBusy(true);
    setError(null);
    let accepted = false;
    try {
      const age = Number(childAge);
      const language = lang === "en" ? "en" : lang === "es" ? "es" : "pt-BR";
      const themeLabel = (onlyName ? bookTitle || themeText : themeText || bookTitle).trim();
      const p = await api.createProject({
        theme: temaId || themeText.trim(),
        childName,
        dedication,
        childAge: Number.isNaN(age) ? undefined : age,
        style: artMode === "cartoon" ? "cartoon" : "realistic",
        bookSize,
        coverType,
        language,
      });
      setMediaConsent(true);
      const uploadMeta = {
        language,
        themeLabel,
        extraNames: extraNames.trim(),
        gender: gender ?? undefined,
        subject: subjectCode(castWho),
        alsoName: alsoName.trim() || undefined,
        alsoGender: alsoGender ?? undefined,
        alsoSubject: alsoWho ? subjectCode(alsoWho) : undefined,
        clientName: buyer.name,
        clientEmail: buyer.email,
        clientPhone: buyer.phone,
        clientAddress: buyer.address,
        clientNotes: buyerNotes || undefined,
      };
      for (let i = 0; i < photos.length; i += 1) {
        await api.uploadPhoto(p.id, photos[i].file, {
          ...uploadMeta,
          finalize: i === photos.length - 1,
        });
      }
      accepted = true;
      setProject(p);
      setJobs([]);
      setAssets(null);
      setOrderSent(true);
      setChangesSent(false);
      storyTouched.current = false;
      setPhotoNotes("");
      const brief = getStoryBrief().trim();
      await api.startPreview(p.id, brief ? { brief: brief.slice(0, 2000) } : {});
      try {
        setJobs(await api.listJobs(p.id));
      } catch {
        // A prévia já foi aceita. O polling busca os jobs sem mostrar 500.
      }
    } catch (e) {
      setError((e as Error).message);
      if (!accepted) {
        window.setTimeout(() => {
          const el = document.getElementById("studio-form-error");
          if (el && typeof el.scrollIntoView === "function") {
            try {
              el.scrollIntoView({ block: "center" });
            } catch {
              /* jsdom */
            }
          }
        }, 0);
      }
    } finally {
      startLock.current = false;
      setBusy(false);
    }
  }

  // HTTP 500 ou job FAILED: não ficar preso em "montando sua prévia…".
  const showPreviewLoading =
    orderSent && !isDemo && !error && !previewFailed && (previewChainActive || !previewReady);
  const showPreviewRetry =
    orderSent && !isDemo && !previewReady && !previewChainActive && (Boolean(error) || previewFailed);
  const previewSteps = previewChainSteps(jobs);
  const imageJob = [...jobs].reverse().find((job) => job.type === "EBOOK" && job.result?.payload?.preview_chain);
  const imageActivity =
    previewSteps.find((step) => step.id === "EBOOK")?.state === "now"
      ? previewImageActivity(imageJob?.result?.progress?.done)
      : null;
  const imageProgress = imageJob?.result?.progress;
  const previewEta = previewEtaMinutes(
    previewSteps,
    imageProgress && typeof imageProgress.done === "number" && typeof imageProgress.total === "number"
      ? { done: imageProgress.done, total: imageProgress.total }
      : null,
  );
  const previewHeadline = previewReady && !showPreviewLoading && !showPreviewRetry
    ? t.previewReadyTitle
    : t.orderSent;

  const [previewWaitedSec, setPreviewWaitedSec] = useState(0);
  useEffect(() => {
    if (!showPreviewLoading) {
      setPreviewWaitedSec(0);
      return;
    }
    const started = Date.now();
    const id = window.setInterval(() => {
      setPreviewWaitedSec(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [showPreviewLoading, project?.id]);

  useEffect(() => {
    if (!orderSent) return;
    const title = `${previewHeadline} — Story R Us`;
    const apply = () => {
      document.title = title;
    };
    // O meta da rota /app roda no efeito do pai e sobrescreve o título.
    apply();
    const id = window.setTimeout(apply, 0);
    return () => {
      window.clearTimeout(id);
      document.title = "Estúdio — Story R Us";
    };
  }, [orderSent, previewHeadline]);

  async function retryPreview() {
    if (!project || isDemo || busy) return;
    setBusy(true);
    setError(null);
    try {
      const brief = getStoryBrief().trim();
      await api.startPreview(project.id, brief ? { brief: brief.slice(0, 2000) } : {});
      try {
        setJobs(await api.listJobs(project.id));
      } catch {
        /* polling */
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitChanges() {
    if (!project || isDemo) return;
    setBusy(true);
    setError(null);
    try {
      const nextStory = storyDraft.trim();
      if (nextStory) {
        const updated = await api.setStoryText(project.id, nextStory);
        setProject(updated);
        setStoryDraft(updated.story_text ?? nextStory);
      }
      setChangesSent(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function resetProject() {
    setProject(null);
    setAssets(null);
    setPhotos((cur) => {
      cur.forEach((item) => releasePreview(item.url));
      return [];
    });
    setOrderSent(false);
    setExtraNames("");
    setMediaConsent(false);
    setChildName("");
    setChildAge("");
    setBookTitle("");
    setThemeText("");
    setDedication("");
    setStoryDraft("");
    setPhotoNotes("");
    setChangesSent(false);
    storyTouched.current = false;
    titleTouched.current = false;
    setJobs([]);
    setError(null);
    setMissing({});
  }

  function exitDemo() {
    const url = new URL(window.location.href);
    url.searchParams.delete("exemplo");
    const next = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, "", next);
    setIsDemo(false);
    resetProject();
    setClientName("");
    setClientDone(false);
    setClientEmail("");
    setClientPhone("");
    setClientAddress("");
    setClientNotes("");
  }

  function toggleColorTheme() {
    setColorTheme((cur) => {
      const next = cur === "light" ? "dark" : "light";
      try {
        localStorage.setItem("theme", next);
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  const fieldsLocked = !!project;
  const showBook = isDemo || clientDone || accountKind === "account";
  const showClient = !isDemo && !clientDone && accountKind === "guest";

  function finishClient() {
    const next: Partial<Record<FieldKey, true>> = {};
    buyerGaps(next);
    if (applyMissing(next, CLIENT_FIELD_ORDER)) {
      setError(null);
      return;
    }
    setError(null);
    setClientDone(true);
  }

  const addPhotos = useCallback((list: Iterable<File>) => {
    const incoming = imageFiles(list);
    if (!incoming.length) return;
    if (incoming.some(unsupportedPhoto)) setError(t.errPhotoFormat);
    setPhotos((cur) => {
      const next = [...cur];
      for (const file of incoming) {
        if (next.length >= PHOTO_LIMIT) break;
        const key = photoKey(file);
        if (next.some((item) => item.key === key)) continue;
        next.push({ key, file, url: previewUrl(file) });
      }
      return next;
    });
    setMissing((cur) => {
      if (!cur.photo) return cur;
      const next = { ...cur };
      delete next.photo;
      return next;
    });
  }, [t]);

  function removePhoto(key: string) {
    setPhotos((cur) => {
      const found = cur.find((item) => item.key === key);
      if (found) releasePreview(found.url);
      return cur.filter((item) => item.key !== key);
    });
  }

  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) return;
      const files = imageFiles(event.clipboardData?.files ?? []);
      if (!files.length) return;
      event.preventDefault();
      addPhotos(files);
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [addPhotos]);
  const primary = subjectCopy(lang, castWho, gender);
  const companionCopy = alsoWho ? subjectCopy(lang, alsoWho, alsoGender) : null;
  const buyer = buyerInfo();
  const buyerNeedsFields =
    !buyer.name || !validEmail(buyer.email) || !buyer.phone || !buyer.address;
  const maxAge = ageLimit(castWho);

  function syncTitle(name: string, companion: string) {
    const preset = titlePreset.current;
    if (!preset || titleTouched.current) return;
    let next = preset.title;
    const typed = name.trim();
    if (preset.hero) next = typed ? next.split(preset.hero).join(typed) : next;
    const hero2 = alsoHero.current;
    const typed2 = companion.trim();
    if (hero2) next = typed2 ? next.split(hero2).join(typed2) : next;
    setBookTitle(next);
    if (next.trim()) clearMissing("title");
  }

  function genderButtons(
    value: StudioGender | null,
    onPick: (next: StudioGender) => void,
    label: string,
    field: "gender" | "alsoGender",
  ) {
    const invalid = Boolean(missing[field]);
    return (
      <div
        className={invalid ? "studio-choice studio-gender is-invalid" : "studio-choice studio-gender"}
        role="group"
        aria-label={label}
        id={`studio-field-${field}`}
        tabIndex={-1}
        aria-invalid={invalid || undefined}
      >
        <span className="studio-choice-label">{label}</span>
        <div className="studio-actions">
          {(["f", "m"] as const).map((choice) => (
            <button
              key={choice}
              type="button"
              className={value === choice ? "studio-pick is-on" : "studio-pick"}
              aria-pressed={value === choice}
              disabled={fieldsLocked}
              onClick={() => {
                onPick(choice);
                clearMissing(field);
              }}
            >
              {choice === "f" ? t.genderF : t.genderM}
            </button>
          ))}
        </div>
        {invalid ? (
          <p className="field-error" role="alert" data-testid={`studio-error-${field}`}>
            {t.errGender}
          </p>
        ) : null}
      </div>
    );
  }

  function fieldAlert(key: FieldKey, text: string) {
    if (!missing[key]) return null;
    return (
      <p className="field-error" id={`studio-field-${key}-error`} role="alert" data-testid={`studio-error-${key}`}>
        {text}
      </p>
    );
  }

  return (
    <div className="kid studio-app">
      <header className="khead" role="banner">
        <div className="khead-inner">
          <a href="/" className="kbrand" aria-label="Story R Us">
            <img className="hdr-logo" src={logo} alt="Story R Us" />
          </a>
          <div className="khead-main">
            <div className="khead-top">
              <div className="khead-top-inner">
                <div className="khead-utils">
                  <div
                    className="lang"
                    role="group"
                    aria-label={t.langAria}
                    data-testid="studio-lang"
                  >
                    {langs.map((code) => (
                      <button
                        key={code}
                        type="button"
                        className={lang === code ? "on" : ""}
                        aria-pressed={lang === code}
                        onClick={() => setLang(code)}
                      >
                        {code.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="theme-toggle"
                    onClick={toggleColorTheme}
                    aria-label={t.themeToggleAria}
                  >
                    {colorTheme === "dark" ? <IcSun className="ti" /> : <IcMoon className="ti" />}
                    <span className="theme-toggle-label">
                      {colorTheme === "dark" ? t.themeToLight : t.themeToDark}
                    </span>
                  </button>
                  {onLogout && (
                    <a className="kutil" href="/pedidos" data-testid="studio-orders">
                      {t.orders}
                    </a>
                  )}
                  {isOwner && (
                    <a className="kutil" href="/usuarios" data-testid="studio-users">
                      Usuários
                    </a>
                  )}
                  {onLogout && (
                    <>
                      <a className="kutil" href="/conta" data-testid="studio-account">
                        {t.account}
                      </a>
                      <button type="button" className="kutil link" onClick={onLogout} data-testid="studio-logout">
                        {t.logout}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="ksection site-back-wrap">
        <SiteBackNav />
      </div>

      <main id="studio-main" className="studio-page" aria-busy={busy || undefined}>
        {orderSent ? (
          <section
            className="studio-card studio-order studio-review"
            role="status"
            data-testid="studio-order-sent"
            aria-busy={showPreviewLoading || undefined}
          >
            <h2 data-testid={previewHeadline === t.previewReadyTitle ? "studio-preview-ready" : undefined}>
              {previewHeadline}
            </h2>
            {isDemo && (
              <div className="demo-banner" role="status" aria-live="polite">
                <p>{t.demoBanner}</p>
                <button type="button" className="kbtn kbtn-soft" onClick={exitDemo}>
                  {t.demoCta}
                </button>
              </div>
            )}
            {(error || (previewFailed && previewFailedJob?.error)) && (
              <p className="studio-error" role="alert">
                {error || previewFailedJob?.error}
              </p>
            )}
            {showPreviewRetry && (
              <button
                type="button"
                className="kbtn kbtn-primary studio-create"
                disabled={busy}
                data-testid="studio-retry-preview"
                onClick={() => void retryPreview()}
              >
                {t.previewRetry}
              </button>
            )}
            {showPreviewLoading ? (
              <div className="studio-preview-building" data-testid="studio-preview-building">
                <p className="studio-slogan">{t.previewBuilding}</p>
                <ol className="preview-steps" aria-label={t.ariaProgress}>
                  {previewSteps.map((step) => (
                    <li
                      key={step.id}
                      className={`preview-step is-${step.state}`}
                      data-testid={`studio-preview-step-${step.id}`}
                      data-step-state={step.state}
                    >
                      <span className="preview-step-mark" aria-hidden="true">
                        {step.state === "done" ? "✓" : ""}
                      </span>
                      <span className="preview-step-copy">
                        <span>{previewStepLabel(t, step.id)}</span>
                        <span className="preview-step-hint">
                          {previewStepHint(t, step.id, step.id === "EBOOK" ? imageActivity : null)}
                        </span>
                      </span>
                      <span className="preview-step-state">{previewStepStateLabel(t, step.state)}</span>
                    </li>
                  ))}
                </ol>
                <p className="studio-slogan preview-must-move" data-testid="studio-preview-must-move">
                  {t.previewMustMove}
                </p>
                <p className="studio-slogan preview-eta" data-testid="studio-preview-eta">
                  {t.previewEta(previewEta.min, previewEta.max)}
                </p>
                <p className="studio-slogan preview-elapsed" data-testid="studio-preview-elapsed">
                  {t.previewElapsed(previewWaitedSec)}
                </p>
                <p className="studio-slogan preview-stay">{t.previewStay}</p>
                <p className="studio-slogan preview-ready-cue">{t.previewReadyCue}</p>
              </div>
            ) : showPreviewRetry ? null : (
              <>
                <p className="studio-slogan">{t.orderFollowup}</p>

                <div
                  className="result-block studio-review-story"
                  data-testid="studio-story-result"
                  role="region"
                  aria-labelledby="studio-story-result-heading"
                >
                  <h3 className="field-label" id="studio-story-result-heading">
                    {t.storyPagesTitle}
                  </h3>
                  <div className="studio-story-book" lang={lang}>
                    {parseStoryPages(project?.story_text || storyDraft).map((page, index) => (
                      <article
                        key={`story-page-${index}`}
                        className={
                          page.kind === "title"
                            ? "studio-story-page is-title"
                            : "studio-story-page"
                        }
                        data-testid={index === 0 ? "studio-story-text" : undefined}
                      >
                        {page.label ? (
                          <header className="studio-story-page-head">
                            <span className="studio-story-page-num">{page.label}</span>
                          </header>
                        ) : null}
                        <div className="studio-story-verse">
                          {page.lines.map((line, lineIndex) => (
                            <p key={`verse-${index}-${lineIndex}`}>{line}</p>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                </div>

                <PreviewTrio
                  coverUrl={assets?.cover_url ?? assets?.page_images?.[0] ?? null}
                  pageUrl={
                    assets?.page_images?.[assets.cover_url ? 0 : 1] ??
                    assets?.page_images?.[0] ??
                    null
                  }
                  inHandUrl={assets?.in_hand_url ?? null}
                />

                <div
                  className="studio-review-changes"
                  data-testid="studio-review-changes"
                  role="region"
                  aria-labelledby="studio-changes-heading"
                >
                  <h3 className="field-label" id="studio-changes-heading">
                    {t.changesTitle}
                  </h3>
                  <label className="studio-field">
                    {t.bookTitle}
                    <input
                      value={bookTitle}
                      onChange={(e) => {
                        titleTouched.current = true;
                        setBookTitle(e.target.value);
                      }}
                      placeholder={t.bookTitlePh}
                      maxLength={120}
                      disabled={isDemo || busy}
                      data-testid="studio-review-title"
                    />
                  </label>
                  <label className="studio-field">
                    {t.themeFree}
                    <textarea
                      value={themeText}
                      onChange={(e) => setThemeText(e.target.value)}
                      placeholder={t.themeFreePh}
                      maxLength={500}
                      rows={3}
                      disabled={isDemo || busy}
                      data-testid="studio-review-theme"
                    />
                  </label>
                  <label className="studio-field">
                    {t.storyPagesTitle}
                    <textarea
                      value={storyDraft}
                      onChange={(e) => {
                        storyTouched.current = true;
                        setStoryDraft(e.target.value);
                      }}
                      placeholder={t.storyPlaceholder}
                      rows={8}
                      disabled={isDemo || busy}
                      data-testid="studio-review-story"
                    />
                  </label>
                  <label className="studio-field">
                    {t.photoChanges}
                    <textarea
                      value={photoNotes}
                      onChange={(e) => setPhotoNotes(e.target.value)}
                      placeholder={t.photoChangesPh}
                      maxLength={500}
                      rows={3}
                      disabled={isDemo || busy}
                      data-testid="studio-review-photo-notes"
                    />
                  </label>
                  {changesSent ? (
                    <p className="muted" role="status" data-testid="studio-changes-received">
                      {t.changesReceived}
                    </p>
                  ) : (
                    <button
                      type="button"
                      className="kbtn kbtn-primary studio-create"
                      disabled={isDemo || busy || !project}
                      data-testid="studio-submit-changes"
                      onClick={() => void submitChanges()}
                    >
                      {t.submitChanges}
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  className="link"
                  onClick={() => (isDemo ? exitDemo() : resetProject())}
                >
                  {isDemo ? t.createMyStory : t.newProject}
                </button>
              </>
            )}
          </section>
        ) : (
          <>
        <section className="studio-card" aria-labelledby="studio-create-heading">
          <h2 id="studio-create-heading">{t.createTitle}</h2>
          <p className="studio-slogan">{t.slogan}</p>

          {(showClient || (showBook && buyerNeedsFields)) && (
            <div className="studio-client" data-testid={showClient ? "studio-client" : "studio-buyer-gap"}>
              <h3 className="field-label">{t.clientTitle}</h3>
              <label className="studio-field">
                {t.clientName}
                <input
                  id="studio-field-clientName"
                  aria-label={t.clientName}
                  disabled={isDemo}
                  value={clientName}
                  onChange={(e) => {
                    setClientName(e.target.value);
                    if (oneLine(e.target.value)) clearMissing("clientName");
                  }}
                  placeholder={t.clientNamePh}
                  maxLength={120}
                  autoComplete="name"
                  aria-invalid={missing.clientName || undefined}
                  aria-describedby={missing.clientName ? "studio-field-clientName-error" : undefined}
                  className={missing.clientName ? "is-invalid" : undefined}
                  data-testid="studio-client-name"
                />
                {fieldAlert("clientName", t.errClientName)}
              </label>
              <label className="studio-field">
                {t.clientEmail}
                <input
                  id="studio-field-clientEmail"
                  aria-label={t.clientEmail}
                  disabled={isDemo}
                  type="email"
                  value={clientEmail}
                  onChange={(e) => {
                    setClientEmail(e.target.value);
                    if (validEmail(oneLine(e.target.value))) clearMissing("clientEmail");
                  }}
                  placeholder={t.clientEmailPh}
                  maxLength={160}
                  autoComplete="email"
                  aria-invalid={missing.clientEmail || undefined}
                  aria-describedby={missing.clientEmail ? "studio-field-clientEmail-error" : undefined}
                  className={missing.clientEmail ? "is-invalid" : undefined}
                  data-testid="studio-client-email"
                />
                {fieldAlert("clientEmail", t.errClientEmail)}
              </label>
              <label className="studio-field">
                {t.clientPhone}
                <input
                  id="studio-field-clientPhone"
                  aria-label={t.clientPhone}
                  disabled={isDemo}
                  type="tel"
                  value={clientPhone}
                  onChange={(e) => {
                    setClientPhone(e.target.value);
                    if (oneLine(e.target.value)) clearMissing("clientPhone");
                  }}
                  placeholder={t.clientPhonePh}
                  maxLength={40}
                  autoComplete="tel"
                  aria-invalid={missing.clientPhone || undefined}
                  aria-describedby={missing.clientPhone ? "studio-field-clientPhone-error" : undefined}
                  className={missing.clientPhone ? "is-invalid" : undefined}
                  data-testid="studio-client-phone"
                />
                {fieldAlert("clientPhone", t.errClientPhone)}
              </label>
              <label className="studio-field">
                {t.clientAddress}
                <textarea
                  id="studio-field-clientAddress"
                  aria-label={t.clientAddress}
                  disabled={isDemo}
                  value={clientAddress}
                  onChange={(e) => {
                    setClientAddress(e.target.value);
                    if (oneLine(e.target.value)) clearMissing("clientAddress");
                  }}
                  placeholder={t.clientAddressPh}
                  maxLength={300}
                  rows={3}
                  autoComplete="street-address"
                  aria-invalid={missing.clientAddress || undefined}
                  aria-describedby={missing.clientAddress ? "studio-field-clientAddress-error" : undefined}
                  className={missing.clientAddress ? "is-invalid" : undefined}
                  data-testid="studio-client-address"
                />
                {fieldAlert("clientAddress", t.errClientAddress)}
              </label>
              <label className="studio-field">
                {t.clientNotes}
                <textarea
                  disabled={isDemo}
                  value={clientNotes}
                  onChange={(e) => setClientNotes(e.target.value)}
                  placeholder={t.clientNotesPh}
                  maxLength={500}
                  rows={2}
                  data-testid="studio-client-notes"
                />
              </label>
              {showClient ? (
                <button type="button" className="kbtn kbtn-go studio-create" onClick={finishClient}>
                  {t.clientContinue}
                </button>
              ) : null}
            </div>
          )}

          {showBook && (
          <>
          <div className="how" role="region" aria-labelledby="studio-how-heading">
            <h3 className="field-label" id="studio-how-heading">
              {t.howTitle}
            </h3>
            <ol>
              {t.how.map((step) => (
                <li key={step.t}>
                  <div>
                    <strong>{step.t}</strong>
                    <p>{step.p}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="studio-grid two">
            <label className="studio-field">
              {primary.name}
              <input
                id="studio-field-name"
                aria-label={primary.name}
                disabled={fieldsLocked}
                value={childName}
                onChange={(e) => {
                  const name = e.target.value;
                  setChildName(name);
                  syncTitle(name, alsoName);
                  if (name.trim()) clearMissing("name");
                }}
                placeholder={primary.namePh}
                maxLength={80}
                aria-invalid={missing.name || undefined}
                aria-describedby={missing.name ? "studio-field-name-error" : undefined}
                className={missing.name ? "is-invalid" : undefined}
              />
              {fieldAlert("name", t.errName)}
            </label>
            <label className="studio-field">
              {primary.age}
              <input
                id="studio-field-age"
                aria-label={primary.age}
                disabled={fieldsLocked}
                type="number"
                inputMode="numeric"
                min={0}
                max={maxAge}
                value={childAge}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === "") {
                    setChildAge("");
                    return;
                  }
                  const n = Math.max(0, Math.min(maxAge, Math.floor(Number(v))));
                  const next = Number.isNaN(n) ? "" : String(n);
                  setChildAge(next);
                  if (next !== "") clearMissing("age");
                }}
                placeholder={t.childAgePh}
                aria-invalid={missing.age || undefined}
                aria-describedby={missing.age ? "studio-field-age-error" : undefined}
                className={missing.age ? "is-invalid" : undefined}
              />
              {fieldAlert("age", t.errAge)}
            </label>
          </div>
          {askGender ? genderButtons(gender, setGender, t.gender, "gender") : null}
          {companionCopy ? (
            <>
              <label className="studio-field studio-also">
                {companionCopy.name}
                <input
                  id="studio-field-alsoName"
                  aria-label={companionCopy.name}
                  disabled={fieldsLocked}
                  value={alsoName}
                  onChange={(e) => {
                    const name = e.target.value;
                    setAlsoName(name);
                    syncTitle(childName, name);
                    if (name.trim()) clearMissing("alsoName");
                  }}
                  placeholder={companionCopy.namePh}
                  maxLength={80}
                  aria-invalid={missing.alsoName || undefined}
                  aria-describedby={missing.alsoName ? "studio-field-alsoName-error" : undefined}
                  className={missing.alsoName ? "is-invalid" : undefined}
                  data-testid="studio-also-name"
                />
                {fieldAlert("alsoName", t.errAlsoName)}
              </label>
              {askGender ? genderButtons(alsoGender, setAlsoGender, t.gender, "alsoGender") : null}
            </>
          ) : null}

          {!fieldsLocked && (
            <>
              <label className="studio-field">
                {t.otherCharacters}
                <input
                  disabled={isDemo}
                  value={extraNames}
                  onChange={(e) => setExtraNames(e.target.value)}
                  placeholder={t.otherCharactersPh}
                  maxLength={300}
                  data-testid="studio-extra-names"
                />
              </label>
              <p className="muted field-hint">{primary.extras}</p>
            </>
          )}

          {!onlyName && (
            <label className="studio-field">
              {t.dedication}
              <input
                disabled={fieldsLocked}
                value={dedication}
                onChange={(e) => setDedication(e.target.value)}
                placeholder={t.dedicationPh}
                maxLength={200}
              />
            </label>
          )}

          {onlyName ? (
            <p className="studio-chosen" role="status">
              <span>{t.chosenBook}</span>
              <b>{bookTitle || themeText}</b>
            </p>
          ) : (
            <>
              <label className="studio-field">
                {t.bookTitle}
                <input
                  id="studio-field-title"
                  aria-label={t.bookTitle}
                  disabled={fieldsLocked}
                  value={bookTitle}
                  onChange={(e) => {
                    titleTouched.current = true;
                    setBookTitle(e.target.value);
                    if (e.target.value.trim()) clearMissing("title");
                  }}
                  placeholder={t.bookTitlePh}
                  maxLength={120}
                  aria-invalid={missing.title || undefined}
                  aria-describedby={missing.title ? "studio-field-title-error" : undefined}
                  className={missing.title ? "is-invalid" : undefined}
                />
                {fieldAlert("title", t.errTitle)}
              </label>

              <label className="studio-field">
                {t.themeFree}
                <textarea
                  id="studio-field-theme"
                  aria-label={t.themeFree}
                  disabled={fieldsLocked}
                  value={themeText}
                  onChange={(e) => {
                    setThemeText(e.target.value);
                    if (e.target.value.trim()) clearMissing("theme");
                  }}
                  placeholder={t.themeFreePh}
                  maxLength={500}
                  rows={3}
                  aria-invalid={missing.theme || undefined}
                  aria-describedby={missing.theme ? "studio-field-theme-error" : undefined}
                  className={missing.theme ? "is-invalid" : undefined}
                />
                {fieldAlert("theme", t.errTheme)}
              </label>
              <p className="muted field-hint">{t.themeHint}</p>
            </>
          )}

          <div className="studio-choices">
            <div className="studio-choice" role="group" aria-label={t.artStyle}>
              <span className="studio-choice-label">{t.artStyle}</span>
              <div className="studio-actions">
                {(["realista", "cartoon"] as const).map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    className={artMode === choice ? "studio-pick is-on" : "studio-pick"}
                    aria-pressed={artMode === choice}
                    disabled={fieldsLocked}
                    onClick={() => setArtMode(choice)}
                  >
                    {choice === "cartoon" ? t.artCartoon : t.artRealistic}
                  </button>
                ))}
              </div>
            </div>

            <div className="studio-choice" role="group" aria-label={t.coverType}>
              <span className="studio-choice-label">{t.coverType}</span>
              <div className="studio-actions">
                {(["hard", "soft"] as const).map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    className={coverType === choice ? "studio-pick is-on" : "studio-pick"}
                    aria-pressed={coverType === choice}
                    disabled={fieldsLocked}
                    onClick={() => setCoverType(choice)}
                  >
                    {choice === "hard" ? t.coverHard : t.coverSoft}
                  </button>
                ))}
              </div>
            </div>

            <div className="studio-choice" role="group" aria-label={t.bookSize}>
              <span className="studio-choice-label">{t.bookSize}</span>
              <div className="studio-actions">
                {(["M", "P"] as const).map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    className={bookSize === choice ? "studio-pick is-on" : "studio-pick"}
                    aria-pressed={bookSize === choice}
                    disabled={fieldsLocked}
                    onClick={() => setBookSize(choice)}
                  >
                    {choice === "M" ? t.bookSizeM : t.bookSizeP}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {!fieldsLocked && (
            <>
              <p className="studio-field">{t.photoCharacters}</p>
              <div
                id="studio-field-photo"
                tabIndex={-1}
                className={
                  missing.photo
                    ? dragOver
                      ? "studio-drop is-over is-invalid"
                      : "studio-drop is-invalid"
                    : dragOver
                      ? "studio-drop is-over"
                      : "studio-drop"
                }
                aria-invalid={missing.photo || undefined}
                data-testid="studio-photo-drop"
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!isDemo) setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  if (!isDemo) addPhotos(e.dataTransfer.files);
                }}
              >
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  disabled={isDemo}
                  data-testid="studio-photo-input"
                  aria-label={t.ariaSelectPhoto}
                  onChange={(e) => {
                    addPhotos(e.target.files ?? []);
                    e.target.value = "";
                  }}
                />
                <span className="studio-drop-title">{t.photoDrop}</span>
                <span className="studio-drop-hint">{t.photoDropHint}</span>
              </div>
              {fieldAlert("photo", t.errPhotoRequired)}
              {photos.length > 0 ? (
                <>
                  <p className="muted field-hint">{t.photoSelected(photos.length)}</p>
                  <ul className="studio-photo-list">
                    {photos.map((item) => (
                      <li key={item.key}>
                        <img src={item.url} alt="" />
                        <span>{item.file.name}</span>
                        <button type="button" onClick={() => removePhoto(item.key)}>
                          {t.photoRemove}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
              <label className={missing.consent ? "studio-consent is-invalid" : "studio-consent"}>
                <input
                  id="studio-field-consent"
                  type="checkbox"
                  checked={mediaConsent}
                  disabled={isDemo}
                  data-testid="studio-media-consent"
                  aria-invalid={missing.consent || undefined}
                  aria-describedby={missing.consent ? "studio-field-consent-error" : undefined}
                  onChange={(e) => {
                    setMediaConsent(e.target.checked);
                    if (e.target.checked) clearMissing("consent");
                  }}
                />
                {t.consent}
              </label>
              {fieldAlert("consent", t.errConsentPhoto)}
              {error ? (
                <p className="studio-error" id="studio-form-error" role="alert">
                  {error}
                </p>
              ) : null}
              <button
                type="button"
                className="kbtn kbtn-primary studio-create"
                disabled={isDemo || busy}
                data-testid="studio-generate-book"
                onClick={() => void start()}
              >
                {t.createProject}
              </button>
            </>
          )}
          </>
          )}
        </section>
          </>
        )}
      </main>
    </div>
  );
}
