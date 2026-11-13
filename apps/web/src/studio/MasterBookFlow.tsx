import { InternalReviewNotice } from "./InternalReviewNotice";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { CatalogDesignSamples } from "./CatalogBookDesign";
import { PreviewImageViewer } from "./PreviewImageViewer";
import { PostPreviewFlow } from "./PostPreviewFlow";
import { TitleSuggestions } from "./TitleSuggestions";
import { StudioStageHeading } from "./StudioStageHeading";
import { api } from "../api";
import type { Job, Project } from "../types";
import type { StudioAssets } from "./assets";
import { useStudioI18n } from "./useStudioI18n";
import { capitalizeChildName } from "./childName";
import { generationError, uncertainGeneration, internalGenerationIssue } from "./generationError";

const COPY = {
  pt: {
    preview: "Aprovo A Prévia?",
    yes: "Sim, aprovo",
    story: "Aprovo A História?",
    face: "Este É O Rosto?",
    next: "Próxima?",
    redo: "Gerar novamente",
    adjust: "Ajuste desta imagem",
    send: "Aplicar ajuste",
    waiting: "Gerando…",
    cover: "Capa",
    open: "Livro Aberto",
    reading: "Segurando o livro",
    noText: "Sem texto",
    withText: "Com texto",
    page: "Página",
    save: "Baixar imagem",
    suggest: "Sugerir melhoria",
    suggestField: "O que melhorar nesta imagem?",
    suggestSend: "Enviar sugestão",
    finish: "As 16 páginas estão prontas.",
    download: "Abrir livro",
    approveBook: "Aprovar livro",
    retry: "Tentar novamente",
    writeStory: "Gerar a história",
    edit: "Ajuste da história",
    editHint: "É para a história em geral. A mudança vale para todas as páginas.",
    alter: "Alterar",
    alterField: "O que devemos ajustar",
    alterSend: "Ajustar página",
    pageChanged: "Página alterada",
    undoPage: "Desfazer alteração",
    summary:
      "Cada página tem a versão sem texto e a versão com texto, nessa ordem. A prévia está no início.",
    continue: "Continuar",
    images: "As Imagens",
    previewImagesHint: "Confira a capa, o livro aberto e a leitura. Os ajustes ficam junto de cada imagem.",
    previewTitleHeading: "Revise O Título",
    previewNextHeading: "Tudo Certo Com A Prévia?",
    previewNextHint: "Confira as imagens e o título antes de continuar. A história será apresentada para sua revisão na próxima etapa.",
    storyHeading: "A História",
    reviewHeading: "Revisão",
    reviewLead: "A história está aprovada. Este é o resumo.",
    reviewTitle: "Título",
    reviewChild: "Criança",
    reviewTheme: "Tema",
    reviewStory: "Ver a história",
    titleLabel: "Título do livro",
    titleSave: "Atualizar título",
    titleHint: "A capa é refeita com este título. O restante da história fica.",
    titleOptions: "Outras opções de título",
    titleOptionsHint: "Escolha uma opção e confirme em Atualizar título.",
    titleUse: "Usar este título",
    titleChosen: "Selecionado",
    childHeading: "Quer alterar o nome ou a idade?",
    childHint: "Se precisar corrigir o nome ou a idade, atualize os campos e salve. Isso não gera novas imagens automaticamente.",
    childName: "Nome da criança",
    childAge: "Idade",
    costume: "Roupa na história (opcional)",
    costumePh: "Ex.: vestido azul de exploradora",
    trait: "Jeito da criança (opcional)",
    traitPh: "Ex.: curiosa e corajosa",
    interest: "O que ela gosta (opcional)",
    interestPh: "Ex.: estrelas e dinossauros",
    childSave: "Salvar dados da criança",
    goToOrder: "Ir para o pedido",
    pagesHeading: "Páginas Do Livro",
    improve: "O que melhorar nesta página",
    improveSend: "Melhorar esta página",
    previewAdjustTitle: "Ajustar Minha Prévia",
    previewAdjustHint: "Descreva o que deseja melhorar. Ao aplicar, a IA refaz a prévia e a história para uma nova revisão.",
    themeLabel: "Tema da história",
    previewNotes: "O que você quer melhorar?",
    cancelAdjust: "Cancelar ajustes",
    retryPreviewTitle: "Sua Prévia Precisa De Uma Nova Geração",
    retryPreviewHint: "Precisamos refazer esta prévia com IA antes da sua revisão. O livro só continuará depois da sua aprovação.",
    retryRealPreview: "Refazer prévia com IA",
    testTitle: "Modo De Teste · Sem Créditos",
    testHint: "As imagens e os textos são genéricos, gerados localmente, sem chamadas à IA. Cada etapa aguarda sua confirmação.",
    testContinue: "Aprovar prévia e continuar o teste",
    exitTest: "Gerar versão real com IA",
    retryGeneric: "Gerar prévia genérica de teste",
  },
  en: {
    preview: "Approve The Preview?",
    yes: "Yes, I approve",
    story: "Approve The Story?",
    face: "Is This The Face?",
    next: "Next?",
    redo: "Regenerate",
    adjust: "Adjustment to this image",
    send: "Apply adjustment",
    waiting: "Generating…",
    cover: "Cover",
    open: "Open Book",
    reading: "Holding the book",
    noText: "Without text",
    withText: "With text",
    page: "Page",
    save: "Download image",
    suggest: "Suggest an improvement",
    suggestField: "What should improve in this image?",
    suggestSend: "Send suggestion",
    finish: "All 16 pages are ready.",
    download: "Open book",
    approveBook: "Approve book",
    retry: "Try again",
    writeStory: "Write the story",
    edit: "Story adjustment",
    editHint: "This is for the story as a whole. The change applies to every page.",
    alter: "Change",
    alterField: "What should we adjust",
    alterSend: "Adjust page",
    pageChanged: "Page changed",
    undoPage: "Undo change",
    summary:
      "Each page has a version without text followed by a version with text. The preview is at the start.",
    continue: "Continue",
    images: "Images",
    previewImagesHint: "Review the cover, open book and reading scene. Adjustments are next to each image.",
    previewTitleHeading: "Review The Title",
    previewNextHeading: "Happy With The Preview?",
    previewNextHint: "Review the images and title before continuing. The story will be presented for your review in the next step.",
    storyHeading: "The Story",
    reviewHeading: "Review",
    reviewLead: "The story is approved. This is the summary.",
    reviewTitle: "Title",
    reviewChild: "Child",
    reviewTheme: "Theme",
    reviewStory: "See the story",
    titleLabel: "Book title",
    titleSave: "Update title",
    titleHint: "The cover is remade with this title. The rest of the story stays.",
    titleOptions: "Other title options",
    titleOptionsHint: "Choose an option and confirm with Update title.",
    titleUse: "Use this title",
    titleChosen: "Selected",
    childHeading: "Want to change the name or age?",
    childHint: "If you need to correct the name or age, update the fields and save. This does not generate new images automatically.",
    childName: "Child's name",
    childAge: "Age",
    costume: "Outfit in the story (optional)",
    costumePh: "e.g. blue explorer dress",
    trait: "The child's way (optional)",
    traitPh: "e.g. curious and brave",
    interest: "What the child likes (optional)",
    interestPh: "e.g. stars and dinosaurs",
    childSave: "Save the child's details",
    goToOrder: "Go to the order",
    pagesHeading: "Book Pages",
    improve: "What to improve on this page",
    improveSend: "Improve this page",
    previewAdjustTitle: "Adjust My Preview",
    previewAdjustHint: "Describe what you would like to improve. Applying changes asks AI to recreate the preview and story for a new review.",
    themeLabel: "Story theme",
    previewNotes: "What would you like to improve?",
    cancelAdjust: "Cancel adjustments",
    retryPreviewTitle: "Your Preview Needs To Be Generated Again",
    retryPreviewHint: "We need to recreate this preview with AI before your review. The book will only continue after your approval.",
    retryRealPreview: "Recreate preview with AI",
    testTitle: "Test Mode · No Credits",
    testHint: "Images and text are generic, generated locally without AI calls. Each step waits for your confirmation.",
    testContinue: "Approve preview and continue the test",
    exitTest: "Create the real version with AI",
    retryGeneric: "Create a generic test preview",
  },
  es: {
    preview: "¿Apruebas La Vista Previa?",
    yes: "Sí, apruebo",
    story: "¿Apruebas La Historia?",
    face: "¿Es Este El Rostro?",
    next: "¿Siguiente?",
    redo: "Generar de nuevo",
    adjust: "Ajuste de esta imagen",
    send: "Aplicar ajuste",
    waiting: "Generando…",
    cover: "Portada",
    open: "Libro Abierto",
    reading: "Sosteniendo el libro",
    noText: "Sin texto",
    withText: "Con texto",
    page: "Página",
    save: "Descargar imagen",
    suggest: "Sugerir mejora",
    suggestField: "¿Qué mejorar en esta imagen?",
    suggestSend: "Enviar sugerencia",
    finish: "Las 16 páginas están listas.",
    download: "Abrir libro",
    approveBook: "Aprobar libro",
    retry: "Intentar de nuevo",
    writeStory: "Escribir la historia",
    edit: "Ajuste de la historia",
    editHint: "Es para la historia en general. El cambio vale para todas las páginas.",
    alter: "Cambiar",
    alterField: "Qué debemos ajustar",
    alterSend: "Ajustar página",
    pageChanged: "Página cambiada",
    undoPage: "Deshacer cambio",
    summary:
      "Cada página tiene la versión sin texto y luego con texto. La vista previa está al inicio.",
    continue: "Continuar",
    images: "Las Imágenes",
    previewImagesHint: "Revisa la portada, el libro abierto y la lectura. Los ajustes están junto a cada imagen.",
    previewTitleHeading: "Revisa El Título",
    previewNextHeading: "¿Todo Bien Con La Vista Previa?",
    previewNextHint: "Revisa las imágenes y el título antes de continuar. La historia se presentará para tu revisión en el siguiente paso.",
    storyHeading: "La Historia",
    reviewHeading: "Revisión",
    reviewLead: "La historia está aprobada. Este es el resumen.",
    reviewTitle: "Título",
    reviewChild: "Protagonista",
    reviewTheme: "Tema",
    reviewStory: "Ver la historia",
    titleLabel: "Título del libro",
    titleSave: "Actualizar título",
    titleHint: "La portada se rehace con este título. El resto de la historia queda.",
    titleOptions: "Otras opciones de título",
    titleOptionsHint: "Elige una opción y confirma con Actualizar título.",
    titleUse: "Usar este título",
    titleChosen: "Seleccionado",
    childHeading: "¿Quieres cambiar el nombre o la edad?",
    childHint: "Si necesitas corregir el nombre o la edad, actualiza los campos y guarda. Esto no genera imágenes nuevas automáticamente.",
    childName: "Nombre del protagonista",
    childAge: "Edad",
    costume: "Ropa en la historia (opcional)",
    costumePh: "Ej.: vestido azul de exploradora",
    trait: "Manera de ser (opcional)",
    traitPh: "Ej.: curiosa y valiente",
    interest: "Lo que le gusta (opcional)",
    interestPh: "Ej.: estrellas y dinosaurios",
    childSave: "Guardar datos del protagonista",
    goToOrder: "Ir al pedido",
    pagesHeading: "Páginas Del Libro",
    improve: "Qué mejorar en esta página",
    improveSend: "Mejorar esta página",
    previewAdjustTitle: "Ajustar Mi Vista Previa",
    previewAdjustHint: "Describe qué te gustaría mejorar. Al aplicar, la IA vuelve a crear la vista previa y la historia para una nueva revisión.",
    themeLabel: "Tema de la historia",
    previewNotes: "¿Qué quieres mejorar?",
    cancelAdjust: "Cancelar ajustes",
    retryPreviewTitle: "Tu Vista Previa Necesita Una Nueva Generación",
    retryPreviewHint: "Necesitamos volver a crear esta vista previa con IA antes de tu revisión. El libro solo continuará después de tu aprobación.",
    retryRealPreview: "Volver a crear la vista previa con IA",
    testTitle: "Modo De Prueba · Sin Créditos",
    testHint: "Las imágenes y los textos son genéricos, generados localmente sin llamadas a IA. Cada paso espera tu confirmación.",
    testContinue: "Aprobar vista previa y continuar la prueba",
    exitTest: "Crear la versión real con IA",
    retryGeneric: "Crear vista previa genérica de prueba",
  },
};

type StoryBlock = { kind: "title" | "page" | "body"; label: string; lines: string[] };

const TITLE_ARTICLES = new Set(["a", "o", "os", "as", "um", "uma", "the", "el", "la", "los", "las", "un", "una"]);

function childDraftFrom(project: Project) {
  const profile = project.book_profile;
  return {
    name: capitalizeChildName(project.child_name || ""),
    age: project.child_age != null ? String(project.child_age) : "",
    costume: profile?.costume || "",
    trait: profile?.trait || project.child_trait || "",
    interest: profile?.interest || project.child_interest || "",
  };
}

function titleProtagonist(childName: string, title: string) {
  const named = childName.trim();
  if (named) return named;
  const first = title.trim().split(/\s+/)[0]?.replace(/[,:.]+$/g, "") || "";
  if (!first || TITLE_ARTICLES.has(first.toLocaleLowerCase())) return "";
  return first;
}

export function extraTitleOptions(lang: "pt" | "en" | "es", childName: string, title: string, theme: string) {
  const name = titleProtagonist(childName, title);
  if (!name) return [];
  const phrase = theme.trim();
  const topic = phrase.length >= 3 && phrase.length <= 40 && phrase.includes(" ") && !/[\n\r]/.test(phrase)
    ? phrase
    : "";
  const comparable = (value: string) => value.normalize("NFKD").replace(/\p{M}/gu, "")
    .toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  const topicMentions = comparable(topic).match(new RegExp(`(?:^| )${comparable(name)}(?= |$)`, "g"))?.length || 0;
  const fallback = lang === "en" ? `A new adventure with ${name}`
    : lang === "es" ? `Una nueva aventura con ${name}` : `${name}: uma nova aventura`;
  const candidate = topicMentions ? topic
    : lang === "en" ? `${name} and ${topic}` : lang === "es" ? `${name} y ${topic}` : `${name} e ${topic}`;
  const themedTitle = topic ? (topicMentions > 1 || comparable(candidate) === comparable(title) ? fallback : candidate) : "";
  const patterns = lang === "en"
    ? [
        `The story of ${name}`,
        `The great adventure of ${name}`,
        `${name} and a world of discoveries`,
        `A book about ${name}`,
        `A story for ${name}`,
        themedTitle,
      ]
    : lang === "es"
      ? [
          `La historia de ${name}`,
          `La gran aventura de ${name}`,
          `${name} y un mundo de descubrimientos`,
          `El libro de ${name}`,
          `Una historia para ${name}`,
          themedTitle,
        ]
      : [
          `A história de ${name}`,
          `A grande aventura de ${name}`,
          `${name} e um mundo de descobertas`,
          `O livro de ${name}`,
          `Uma história para ${name}`,
          themedTitle,
        ];
  const current = title.trim().toLocaleLowerCase();
  return [...new Set(patterns.map((item) => item.trim()).filter(Boolean))]
    .filter((item) => item.toLocaleLowerCase() !== current)
    .slice(0, 6);
}

function verseLines(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((para) => para.replace(/\s*\n\s*/g, " ").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function storyBlocks(text: string): StoryBlock[] {
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
    if (titleMatch) return { kind: "title", label: "Título", lines: verseLines(titleMatch[1]) };
    const pageMatch = part.match(/^(P[aá]gina\s+\d+)\s*:\s*([\s\S]*)$/i);
    if (pageMatch) return { kind: "page", label: pageMatch[1], lines: verseLines(pageMatch[2]) };
    return { kind: "body", label: "", lines: verseLines(part) };
  });
}

type Props = {
  project: Project;
  jobs: Job[];
  assets: StudioAssets | null;
  setProject: (project: Project) => void;
  setJobs: (jobs: Job[]) => void;
  setAssets?: (assets: StudioAssets) => void;
  canConfirmPayment?: boolean;
};

export function MasterBookFlow({
  project,
  jobs,
  assets,
  setProject,
  setJobs,
  setAssets,
  canConfirmPayment = false,
}: Props) {
  const { lang, t: studioCopy } = useStudioI18n();
  const t = COPY[lang];
  const [expandedImage, setExpandedImage] = useState<{ url: string; label: string } | null>(null);
  const expandLabel = lang === "en" ? "Enlarge" : lang === "es" ? "Ampliar" : "Ampliar";
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [adjustment, setAdjustment] = useState("");
  const [suggesting, setSuggesting] = useState("");
  const [alteringPage, setAlteringPage] = useState("");
  const [pageCorrections, setPageCorrections] = useState<Record<string, string>>({});
  const [suggestionText, setSuggestionText] = useState<Record<string, string>>({});
  const suggestionField = useRef<HTMLTextAreaElement>(null);
  const [editing, setEditing] = useState(false);
  const adjustmentPanel = useRef<HTMLDivElement>(null);
  const adjustmentNotes = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (!editing) return;
    adjustmentPanel.current?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    adjustmentNotes.current?.focus({ preventScroll: true });
  }, [editing]);
  useEffect(() => {
    if (suggesting) suggestionField.current?.focus();
  }, [suggesting]);
  const [editTitle, setEditTitle] = useState(project.book_profile?.title || "");
  const [childDraft, setChildDraft] = useState(() => childDraftFrom(project));
  useEffect(() => {
    setChildDraft(childDraftFrom(project));
  }, [project]);
  useEffect(() => {
    setEditTitle(project.book_profile?.title || "");
  }, [project.book_profile?.title]);
  const [editTheme, setEditTheme] = useState(
    project.purchase_flow?.theme_description || project.theme || "",
  );
  const [pageToAdjust, setPageToAdjust] = useState<number | null>(null);
  const [pageNotes, setPageNotes] = useState<Record<number, string>>({});
  const p = project.book_profile!;
  const testMode = Boolean(project.test_mode || p.test_mode);
  const active =
    sending ||
    jobs.some((j) => j.status === "RUNNING" || j.status === "PENDING");
  const lastJob = jobs[jobs.length - 1];
  const failed = lastJob?.status === "FAILED" ? lastJob : null;
  const stage = p.stage;
  const isPreviewReview = ["preview_ready", "story_ready", "cover_ready"].includes(stage)
    && !project.purchase_flow?.preview_approved_at;
  const storyReview = stage === "story_approved" && !project.purchase_flow?.preview_approved_at;
  const previews = [...(assets?.previews ?? [])].filter((shot) => stage !== "cover_ready" || shot.role === "01_CAPA").sort(
    (a, b) =>
      p.languages.indexOf(a.language) - p.languages.indexOf(b.language) ||
      a.role.localeCompare(b.role),
  );
  const versions = [...(assets?.page_versions ?? [])].sort(
    (a, b) =>
      (a.page ?? 0) - (b.page ?? 0) ||
      p.languages.indexOf(a.language) - p.languages.indexOf(b.language) ||
      (a.role === "sem_texto" ? -1 : 1),
  );
  async function runDownload(action: () => Promise<unknown>) {
    if (active) return;
    setSending(true);
    setError("");
    try { await action(); }
    catch (e) { setError((e as Error).message); }
    finally { setSending(false); }
  }

  async function downloadImage(image: import("./assets").BookImage) {
    if (!image.asset_id) throw new Error(lang === "en" ? "Reload the project before downloading." : lang === "es" ? "Vuelve a abrir el proyecto antes de descargar." : "Reabra o projeto antes de baixar.");
    const blob = await api.downloadBookImage(project.id, image.asset_id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = image.filename || "Storyrus-imagem.png";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function run(action: () => Promise<unknown>) {
    if (active) return;
    setSending(true);
    setError("");
    try {
      await action();
      setProject(await api.getProject(project.id));
      setJobs(await api.listJobs(project.id));
      if (setAssets) setAssets(await api.getAssets(project.id));
      setSuggesting("");
      setSuggestionText({});
      setAlteringPage("");
      setPageCorrections({});
      setAdjustment("");
      setPageToAdjust(null);
    } catch (e) {
      setError((e as Error).message);
      // An approval may have committed even if starting the next job failed.
      try {
        setProject(await api.getProject(project.id));
        setJobs(await api.listJobs(project.id));
      } catch {
        /* Keep the reviewable state. */
      }
    } finally {
      setSending(false);
    }
  }
  async function saveChild(event: FormEvent) {
    event.preventDefault();
    const name = capitalizeChildName(childDraft.name).trim();
    if (!name) {
      setError(t.childName);
      return;
    }
    const ageNumber = childDraft.age.trim() === "" ? undefined : Number(childDraft.age);
    await run(() =>
      api.saveChildProfile(project.id, {
        childName: name,
        childAge: ageNumber != null && !Number.isNaN(ageNumber) ? Math.max(0, Math.min(120, Math.floor(ageNumber))) : undefined,
        costume: childDraft.costume.trim(),
        trait: childDraft.trait.trim(),
        interest: childDraft.interest.trim(),
      }),
    );
  }
  const approveStory = async () => {
    await api.approveStory(project.id);
  };
  const approveFace = async () => {
    await api.approveCharacter(project.id);
    await api.nextBookPage(project.id);
  };
  const savedTitle = (p.title || "").trim();
  const titleOptions = extraTitleOptions(
    lang,
    project.child_name || "",
    savedTitle,
    project.purchase_flow?.theme_description || project.theme || "",
  );
  const canEditTitle =
    p.current_page === 0 &&
    ["preview_ready", "story_ready", "story_approved", "preview_approved"].includes(stage);
  const severalLanguages = new Set(previews.map((shot) => shot.language)).size > 1;
  const bookLanguage = project.language || "pt-BR";
  const finishedPages = versions.filter(
    (image) => image.language === bookLanguage && image.role === "com_texto" && image.page,
  );
  const reviewing = ["page_ready", "book_ready"].includes(stage) && finishedPages.length > 0;
  const gallery = previews.flatMap((shot) => {
    const cleanCover = reviewing && shot.role === "01_CAPA" ? assets?.book_cover_url : null;
    const url = cleanCover || shot.url;
    if (reviewing && url.includes("preview-mark")) return [];
    return [{ ...shot, url }];
  });
  const storyView = p.stories ? (
    <>
      {p.languages.map((language) => {
        const blocks = storyBlocks(p.stories?.[language] || "");
        return (
          <div key={language}>
            {p.languages.length > 1 && <h4 className="master-lang">{language.toUpperCase()}</h4>}
            <div className="master-story-book">
              {blocks.map((block, index) => {
                const page = block.kind === "page" ? Number(block.label.match(/\d+/)?.[0]) : 0;
                const altered =
                  page >= 1 && page <= 16 && Boolean(p.page_revisions?.[language]?.[String(page)]);
                const key = `${language}:${page}`;
                const note = pageCorrections[key] || "";
                const open = alteringPage === key;
                return (
                <article
                  key={`${language}-${index}`}
                  className={[
                    "studio-story-page",
                    block.kind === "title" ? "is-title" : "",
                    altered ? "is-altered" : "",
                  ].filter(Boolean).join(" ")}
                >
                  {block.label ? (
                    <header className="studio-story-page-head">
                      <span className="studio-story-page-num">{block.label}</span>
                      {altered && <span className="studio-story-page-mark">{t.pageChanged}</span>}
                    </header>
                  ) : null}
                  <div className="studio-story-verse">
                    {block.lines.map((line, lineIndex) => (
                      <p key={`${language}-${index}-${lineIndex}`}>{line}</p>
                    ))}
                  </div>
                  {stage === "story_ready" && block.kind === "page" && page >= 1 && page <= 16 && (
                      <div className="studio-story-actions">
                        <button
                          type="button"
                          className="story-alter-toggle"
                          aria-expanded={open}
                          disabled={active}
                          onClick={() => setAlteringPage((current) => (current === key ? "" : key))}
                        >
                          {t.alter}
                        </button>
                        {altered && (
                          <button
                            type="button"
                            className="story-undo"
                            disabled={active}
                            onClick={() => void run(() => api.undoStoryPage(project.id, page))}
                          >
                            {t.undoPage}
                          </button>
                        )}
                        {open && (
                          <div className="studio-story-alter">
                            <label className="studio-field">
                              {t.alterField}
                              <textarea
                                value={note}
                                maxLength={500}
                                rows={3}
                                onChange={(event) =>
                                  setPageCorrections((current) => ({ ...current, [key]: event.target.value }))
                                }
                              />
                            </label>
                            <button
                              type="button"
                              className="kbtn kbtn-soft"
                              disabled={active || !note.trim()}
                              onClick={() =>
                                void run(() =>
                                  api.startStep(project.id, "story", { page, brief: note.trim() }),
                                )
                              }
                            >
                              {t.alterSend}
                            </button>
                          </div>
                        )}
                      </div>
                  )}
                </article>
                );
              })}
            </div>
          </div>
        );
      })}
    </>
  ) : null;
  async function applyTitle(event: FormEvent) {
    event.preventDefault();
    const title = editTitle.trim();
    if (!title || title === savedTitle) return;
    await run(() => api.updatePreviewTitle(project.id, title));
  }
  if (!active && internalGenerationIssue(error || failed?.error, failed)) {
    return <InternalReviewNotice lang={lang} />;
  }
  if (p.credits_fallback) {
    return <section className="master-adjustment-panel" data-testid="studio-preview-recovery">
      <StudioStageHeading title={testMode ? t.testTitle : t.retryPreviewTitle} illustration={0}>
        <p>{testMode ? t.testHint : t.retryPreviewHint}</p>
      </StudioStageHeading>
      {error && <p className="studio-error" role="alert">{generationError(studioCopy, error)}</p>}
      <button type="button" className="kbtn kbtn-primary" disabled={active || uncertainGeneration(failed?.error, failed)}
        onClick={() => void run(() => api.retryRealPreview(project.id))}>
        {active ? t.waiting : testMode ? t.retryGeneric : t.retryRealPreview}
      </button>
    </section>;
  }
  return (
    <div className={`studio-master-flow${isPreviewReview ? " is-preview-review" : ""}`} data-testid="studio-master-flow">
      {p.book_design && isPreviewReview && <CatalogDesignSamples model={p.book_design} lang={lang} />}
      {expandedImage && <PreviewImageViewer src={expandedImage.url} title={expandedImage.label}
        lang={lang} onClose={() => setExpandedImage(null)} />}
      {testMode && <section className="master-adjustment-panel" data-testid="studio-test-mode">
        <h3>{t.testTitle}</h3><p className="master-title-hint">{t.testHint}</p>
        {!project.ai_generation_paused && <button type="button" className="kbtn kbtn-soft" disabled={active}
          onClick={() => void run(() => api.retryRealPreview(project.id))}>{t.exitTest}</button>}
      </section>}
      {error && <p className="studio-error" role="alert">{generationError(studioCopy, error)}</p>}
      {active && <p className="master-status" role="status">{t.waiting}</p>}
      {!active && failed?.error && <p className="studio-error" role="alert">{generationError(studioCopy, failed.error, failed)}</p>}
      {storyReview && (
        <section className="master-story-review" aria-labelledby="story-review-heading" data-testid="studio-story-review">
          <h3 id="story-review-heading">{t.reviewHeading}</h3>
          <p className="master-title-hint">{t.reviewLead}</p>
          <dl>
            <div>
              <dt>{t.reviewTitle}</dt>
              <dd>{savedTitle || "—"}</dd>
            </div>
            {(project.child_name || project.child_age != null) && (
              <div>
                <dt>{t.reviewChild}</dt>
                <dd>
                  {capitalizeChildName(project.child_name || "")}
                  {project.child_age != null && project.child_age !== 0 ? ` · ${project.child_age}` : ""}
                </dd>
              </div>
            )}
            {(project.purchase_flow?.theme_description || project.theme) && (
              <div>
                <dt>{t.reviewTheme}</dt>
                <dd>{project.purchase_flow?.theme_description || project.theme}</dd>
              </div>
            )}
          </dl>
          {gallery.length > 0 && (
            <div className="master-review-gallery">
              {gallery.map((shot) => {
                const label = shot.role === "01_CAPA" ? t.cover : shot.role === "02_LIVRO_ABERTO" ? t.open : t.reading;
                return (
                  <figure key={`${shot.language}-${shot.role}`}>
                    <img src={shot.url} alt={label} />
                    <figcaption>{label} <button type="button" className="master-image-expand"
                      aria-label={`${expandLabel} ${label}`} onClick={() => setExpandedImage({ url: shot.url, label })}>{expandLabel}</button></figcaption>
                  </figure>
                );
              })}
            </div>
          )}
          {p.stories && (
            <details className="master-review-story">
              <summary>{t.reviewStory}</summary>
              {storyView}
            </details>
          )}
        </section>
      )}
      {!storyReview && (
      <details className="master-child-edit" open={!isPreviewReview}>
      <summary>{t.childHeading}</summary>
      <form className="master-child-card" onSubmit={(event) => void saveChild(event)} data-testid="studio-child-profile">
        <p className="master-title-hint">{t.childHint}</p>
        <div className="studio-grid two">
          <label className="studio-field">
            {t.childName}
            <input
              value={childDraft.name}
              maxLength={80}
              onChange={(event) =>
                setChildDraft((current) => ({ ...current, name: capitalizeChildName(event.target.value) }))
              }
            />
          </label>
          <label className="studio-field">
            {t.childAge}
            <input
              type="number"
              inputMode="numeric"
              min={0}
              max={120}
              value={childDraft.age}
              onChange={(event) => setChildDraft((current) => ({ ...current, age: event.target.value }))}
            />
          </label>
        </div>
        <button type="submit" className="kbtn kbtn-soft" disabled={active}>{t.childSave}</button>
      </form>
      </details>
      )}
      {!storyReview && ["story_approved", "preview_approved", "avatar_ready", "avatar_approved", "page_ready", "book_ready"].includes(stage) && (
        <button
          type="button"
          className="kbtn kbtn-primary master-order-jump"
          onClick={() =>
            document.getElementById("pedido")?.scrollIntoView({ behavior: "smooth", block: "start" })
          }
        >
          {t.goToOrder}
        </button>
      )}
      {!storyReview && gallery.length > 0 && (
        <section className={isPreviewReview ? "master-preview-panel master-preview-images" : undefined}
          aria-labelledby="master-preview-images-heading">
          <div className="master-preview-panel-heading">
            <h3 id="master-preview-images-heading" className="master-section">
              {isPreviewReview && <span className="master-preview-number" aria-hidden="true">01</span>}{t.images}
            </h3>
            {isPreviewReview && stage !== "cover_ready" && <p className="master-title-hint">{t.previewImagesHint}</p>}
          </div>
      <div className={`master-gallery${gallery.length === 1 ? " has-single-preview" : ""}`}>
        {gallery.map((shot) => {
          const label =
            shot.role === "01_CAPA" ? t.cover : shot.role === "02_LIVRO_ABERTO" ? t.open : t.reading;
          const shotClass =
            shot.role === "01_CAPA" ? "is-cover" : shot.role === "02_LIVRO_ABERTO" ? "is-open" : "is-reading";
          return (
            <figure key={`${shot.language}-${shot.role}`} className={`master-shot ${shotClass}`}>
              <img src={shot.url} alt={severalLanguages ? `${shot.language.toUpperCase()} · ${label}` : label} />
              <figcaption>
                <span>{severalLanguages ? `${shot.language.toUpperCase()} · ${label}` : label}</span>
                <span className="master-shot-actions">
                  <button type="button" aria-label={`${expandLabel} ${label}`}
                    onClick={() => setExpandedImage({ url: shot.url, label })}>{expandLabel}</button>
                  {previews.length === 3 && shot === previews[0] && <button type="button" disabled={active} onClick={() => void runDownload(async () => {
                    const blob = await api.downloadPreviewPackage(project.id);
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url; link.download = "Storyrus-previa.zip"; link.click();
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                  })}>{lang === "en" ? "Download 3 PNGs" : lang === "es" ? "Descargar 3 PNGs" : "Baixar 3 PNGs"}</button>}
                  {["preview_ready", "cover_ready"].includes(stage) ? (
                    <button
                      type="button"
                      aria-expanded={suggesting === `${shot.language}:${shot.role}`}
                      disabled={active}
                      onClick={() => {
                        const key = `${shot.language}:${shot.role}`;
                        setSuggesting((current) => (current === key ? "" : key));
                      }}
                    >
                      {t.suggest}
                    </button>
                  ) : (
                    <button type="button" disabled={active} onClick={() => void runDownload(() => downloadImage(shot))}>
                      {t.save}
                    </button>
                  )}
                </span>
              </figcaption>
              {["preview_ready", "cover_ready"].includes(stage) && suggesting === `${shot.language}:${shot.role}` && (
                <div className="master-shot-suggestion">
                  <label className="studio-field">
                    {t.suggestField}
                    <textarea
                      ref={suggestionField}
                      value={suggestionText[`${shot.language}:${shot.role}`] || ""}
                      maxLength={500}
                      rows={3}
                      onChange={(event) => {
                        const key = `${shot.language}:${shot.role}`;
                        setSuggestionText((current) => ({ ...current, [key]: event.target.value }));
                      }}
                    />
                  </label>
                  <button
                    type="button"
                    className="kbtn kbtn-soft"
                    disabled={active || !(suggestionText[`${shot.language}:${shot.role}`] || "").trim()}
                    onClick={() => {
                      const key = `${shot.language}:${shot.role}`;
                      void run(() =>
                        api.startPreview(project.id, {
                          language: shot.language,
                          image: shot.role,
                          ...(stage === "cover_ready" ? { cover_only: true } : {}),
                          adjustment: (suggestionText[key] || "").trim(),
                        }),
                      );
                    }}
                  >
                    {t.suggestSend}
                  </button>
                </div>
              )}
            </figure>
          );
        })}
      </div>
        </section>
      )}
      {stage === "cover_ready" && (
        <section className="master-preview-panel master-cover-decision" data-testid="studio-cover-calibration">
          <h3>{lang === "en" ? "Review the cover first" : lang === "es" ? "Revisa primero la portada" : "Avalie primeiro a capa"}</h3>
          <p>{lang === "en" ? "Review the face, finish and layout. The other scenes will only be generated after your approval." : lang === "es" ? "Revisa el rostro, el acabado y la composición. Las otras escenas solo se generarán después de tu aprobación." : "Confira o rosto, o acabamento e a composição. As outras cenas só serão geradas depois da sua aprovação."}</p>
          <button type="button" className="kbtn kbtn-primary" disabled={active || !p.cover_calibration?.sha256}
            onClick={() => void run(() => api.startPreview(project.id, { approved_cover_sha256: p.cover_calibration!.sha256 }))}>
            {lang === "en" ? "Approve this cover and generate the preview" : lang === "es" ? "Aprobar esta portada y generar la vista previa" : "Aprovar esta capa e gerar o restante da prévia"}
          </button>
        </section>
      )}
      {!storyReview && canEditTitle && (
        <form className="master-title-card" onSubmit={(event) => void applyTitle(event)}>
          {isPreviewReview && stage !== "cover_ready" && (
            <div className="master-preview-panel-heading">
              <h3 className="master-section"><span className="master-preview-number" aria-hidden="true">02</span>{t.previewTitleHeading}</h3>
            </div>
          )}
          <div className="master-title-row">
            <label className="studio-field">
              {t.titleLabel}
              <input
                value={editTitle}
                maxLength={120}
                data-testid="studio-preview-title"
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </label>
            <button
              type="submit"
              className="kbtn kbtn-soft"
              disabled={active || !editTitle.trim() || editTitle.trim() === savedTitle}
            >
              {t.titleSave}
            </button>
          </div>
          <p className="master-title-hint">{t.titleHint}</p>
          {titleOptions.length > 0 && (
            <details className="master-title-alternatives" open={!isPreviewReview}>
              <summary>{t.titleOptions}</summary>
              <p className="master-title-hint">{t.titleOptionsHint}</p>
              <ul className="master-title-options" aria-label={t.titleOptions}>
                {titleOptions.map((option) => (
                  <li key={option}>
                    <button
                      type="button"
                      className={editTitle.trim() === option ? "is-selected" : ""}
                      aria-pressed={editTitle.trim() === option}
                      disabled={active}
                      onClick={() => setEditTitle(option)}
                    >
                      <span>{option}</span>
                      <span className="master-title-choice">{editTitle.trim() === option ? t.titleChosen : t.titleUse}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {!testMode && !project.ai_generation_paused && <TitleSuggestions key={project.id} projectId={project.id} currentTitle={savedTitle}
            selectedTitle={editTitle} disabled={active} onSelect={setEditTitle} />}
        </form>
      )}
      {!(["2026-11-05.1", "2026-11-05.2", "2026-11-05.3"].includes(p.editorial?.version || "")) && stage === "preview_ready" && !p.stories && !jobs.some((job) => job.type === "STORY" && (job.status === "PENDING" || job.status === "RUNNING")) && (
        <section className="master-preview-next" aria-labelledby="master-preview-next-heading">
          <div>
            <h3 id="master-preview-next-heading">{t.previewNextHeading}</h3>
            <p className="master-title-hint">{t.previewNextHint}</p>
          </div>
          <button
            className="kbtn kbtn-primary studio-create"
            disabled={active}
            data-testid="studio-write-story"
            onClick={() => void run(() => api.startStep(project.id, "story"))}
          >
            {testMode ? t.testContinue : t.writeStory}
          </button>
        </section>
      )}
      {reviewing && (
        <section className="master-pages" aria-labelledby="master-pages-heading">
          <h3 id="master-pages-heading" className="master-section">{t.pagesHeading}</h3>
          <div className="master-page-grid">
            {finishedPages.map((image) => {
              const page = image.page ?? 1;
              const note = pageNotes[page] || "";
              return (
                <article key={`${image.language}-${page}`} className="master-page-card">
                  <h4>{t.page} {page}</h4>
                  <img src={image.url} alt={`${t.page} ${page}`} />
                  <button type="button" disabled={active} onClick={() => void runDownload(() => downloadImage(image))}>
                    {t.save}
                  </button>
                  {!project.book_approved_at && (
                    <>
                      <label className="studio-field">
                        {t.improve}
                        <textarea
                          value={note}
                          maxLength={500}
                          onChange={(event) =>
                            setPageNotes((current) => ({ ...current, [page]: event.target.value }))
                          }
                        />
                      </label>
                      <button
                        type="button"
                        className="kbtn kbtn-soft"
                        disabled={active || !note.trim()}
                        onClick={() =>
                          void run(() =>
                            api.nextBookPage(project.id, { page, adjustment: note.trim() }),
                          )
                        }
                      >
                        {t.improveSend}
                      </button>
                    </>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}
      {((["2026-11-05.1", "2026-11-05.2", "2026-11-05.3"].includes(p.editorial?.version || "") && stage === "preview_ready") || ["story_approved", "preview_approved", "avatar_ready", "avatar_approved", "page_ready", "book_ready"].includes(stage)) && (
        <PostPreviewFlow
          showSteps={false}
          adjusting={editing}
          project={project}
          jobs={jobs}
          assets={assets}
          isDemo={testMode}
          dirty={editing}
          onProject={setProject}
          onJobs={setJobs}
          onAdjust={() => setEditing(true)}
          canConfirmPayment={canConfirmPayment}
        />
      )}
      {["preview_ready", "story_ready", "story_approved"].includes(stage) && editing && (
        <div className="studio-review-changes master-adjustment-panel" ref={adjustmentPanel}
          role="region" aria-labelledby="preview-adjust-heading">
          <StudioStageHeading id="preview-adjust-heading" title={t.previewAdjustTitle} illustration={0}>
            <p className="master-title-hint">{t.previewAdjustHint}</p>
          </StudioStageHeading>
          <label className="studio-field">
            {t.themeLabel}
            <textarea
              value={editTheme}
              maxLength={500}
              onChange={(e) => setEditTheme(e.target.value)}
            />
          </label>
          <label className="studio-field">
            {t.previewNotes}
            <textarea
              ref={adjustmentNotes}
              value={adjustment}
              maxLength={500}
              onChange={(e) => setAdjustment(e.target.value)}
            />
          </label>
          <button
            className="kbtn kbtn-soft"
            type="button"
            disabled={active || !editTitle.trim() || !editTheme.trim() ||
              (!adjustment.trim() && editTheme.trim() === (project.purchase_flow?.theme_description || project.theme || "").trim())}
            onClick={() =>
              void run(async () => {
                await api.savePreviewChanges(project.id, {
                  title: editTitle,
                  theme_description: editTheme,
                  photo_notes: adjustment,
                  story_text: "",
                });
                setEditing(false);
              })
            }
          >
            {t.send}
          </button>
          <button type="button" className="kbtn kbtn-soft" disabled={active} onClick={() => {
            setEditing(false);
            setEditTheme(project.purchase_flow?.theme_description || project.theme || "");
            setAdjustment("");
          }}>{t.cancelAdjust}</button>
        </div>
      )}
      {!storyReview && stage !== "cover_ready" && p.stories && (
        <div data-testid="studio-master-story">
          {reviewing ? (
            <details>
              <summary className="master-section">{t.storyHeading}</summary>
              {storyView}
            </details>
          ) : (
            <>
              <h3 className="master-section">{t.storyHeading}</h3>
              {storyView}
            </>
          )}
        </div>
      )}
      {stage === "story_ready" && (
        <section className="master-decision" aria-labelledby="master-story-decision">
          <StudioStageHeading id="master-story-decision" title={t.story} illustration={1} />
          <button type="button" className="kbtn kbtn-primary" disabled={active} onClick={() => void run(approveStory)}>
            {t.yes}
          </button>
          <label className="studio-field">
            {t.edit}
            <textarea
              value={adjustment}
              onChange={(e) => setAdjustment(e.target.value)}
              maxLength={2000}
            />
          </label>
          <p className="master-title-hint">{t.editHint}</p>
          <button
            type="button"
            className="kbtn kbtn-soft"
            disabled={active || !adjustment.trim()}
            onClick={() =>
              void run(() =>
                api.startStep(project.id, "story", { brief: adjustment }),
              )
            }
          >
            {t.send}
          </button>
        </section>
      )}
      {stage === "story_approved" && !!project.purchase_flow?.preview_approved_at && (
        <button
          className="kbtn kbtn-primary"
          disabled={active}
          onClick={() => void run(() => api.startStep(project.id, "avatar"))}
        >
          {t.continue}
        </button>
      )}
      {assets?.character_url && !reviewing && (
        <img className="master-character-preview"
          src={assets.character_url}
          alt={t.face}
        />
      )}
      {stage === "avatar_ready" && (
        <div className="master-decision">
          <StudioStageHeading title={t.face} illustration={2} />
          <button className="kbtn kbtn-primary" disabled={active} onClick={() => void run(approveFace)}>
            {t.yes}
          </button>
          <button
            className="kbtn kbtn-soft"
            disabled={active}
            onClick={() => void run(() => api.startStep(project.id, "avatar"))}
          >
            {t.redo}
          </button>
        </div>
      )}
      {!reviewing && versions.map((image) => (
        <figure className="master-version-card" key={`${image.language}-${image.page}-${image.role}`}>
          <figcaption>
            {t.page} {image.page} · {image.language.toUpperCase()} ·{" "}
            {image.role === "sem_texto" ? t.noText : t.withText}
          </figcaption>
          <img
            src={image.url}
            alt={image.filename}
            style={{ maxWidth: 480, width: "100%", display: "block" }}
          />
          <button type="button" disabled={active} onClick={() => void runDownload(() => downloadImage(image))}>
            {t.save}
          </button>
          {image.role === "com_texto" && (
            <button
              className="kbtn kbtn-soft"
              disabled={active || !!project.book_approved_at}
              onClick={() => setPageToAdjust(image.page ?? 1)}
            >
              {t.redo} · {t.page} {image.page}
            </button>
          )}
        </figure>
      ))}
      {!reviewing && p.current_page > 0 && p.stories && (
        <p style={{ whiteSpace: "pre-wrap" }}>
          {
            p.stories[project.language ?? "pt-BR"]?.split(
              /P[aá]gina\s+\d+:\s*/i,
            )[p.current_page]
          }
        </p>
      )}
      {["avatar_approved", "page_ready"].includes(stage) && (
        <button
          className="kbtn kbtn-primary"
          disabled={active}
          onClick={() => void run(() => api.nextBookPage(project.id))}
        >
          {t.next}
        </button>
      )}
      {!reviewing && ["page_ready", "book_ready"].includes(stage) && (
        <div className="master-adjustment-panel">
          <label className="studio-field">
            {t.adjust}
            <textarea
              value={adjustment}
              onChange={(e) => setAdjustment(e.target.value)}
              maxLength={500}
            />
          </label>
          <button
            className="kbtn kbtn-soft"
            disabled={active || !!project.book_approved_at || !adjustment.trim()}
            onClick={() =>
              void run(() =>
                api.nextBookPage(project.id, {
                  page: pageToAdjust ?? p.current_page,
                  adjustment,
                }),
              )
            }
          >
            {t.redo} · {t.page} {pageToAdjust ?? p.current_page}
          </button>
        </div>
      )}
      {stage === "book_ready" && !reviewing && (
        <div>
          <p>
            {t.finish} {t.summary}
          </p>
          {assets?.ebook_url && (
            <a href={assets.ebook_url} target="_blank" rel="noreferrer">
              {t.download}
            </a>
          )}
        </div>
      )}
    </div>
  );
}
