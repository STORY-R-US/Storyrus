import { InternalReviewNotice } from "./InternalReviewNotice";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { PreviewImageViewer } from "./PreviewImageViewer";
import { PostPreviewFlow } from "./PostPreviewFlow";
import { TitleSuggestions } from "./TitleSuggestions";
import { StudioStageHeading } from "./StudioStageHeading";
import { api } from "../api";
import type { Job, Project } from "../types";
import type { StudioAssets } from "./assets";
import { useStudioI18n } from "./useStudioI18n";
import { tidyTitleCase } from "./titleCase";
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
    writingStory: "Escrevendo a sua história… Leva cerca de 1 minuto e a tela atualiza sozinha.",
    showImages: "Ver as imagens da prévia",
    showStory: "Ler a história",
    cover: "Capa",
    open: "Livro Aberto",
    reading: "Segurando o livro",
    noText: "Sem texto",
    withText: "Com texto",
    page: "Página",
    save: "Baixar imagem",
    suggest: "Mudar esta imagem",
    suggestField: "O que você quer mudar?",
    suggestPh: "Ex.: deixar o rosto mais parecido com a foto",
    suggestSend: "Refazer esta imagem",
    changeTitle: "Mudar",
    changeCancel: "Cancelar",
    photosTitle: "Fotos do herói",
    photosHint: "Tire as fotos ruins e envie fotos nítidas do rosto. Assim o personagem fica mais parecido.",
    photoRemove: "Remover",
    photoAdd: "Adicionar fotos",
    photoKeepOne: "Fica pelo menos 1 foto.",
    photoConsent: "Sou o responsável e autorizo o uso destas fotos.",
    photoSending: "Enviando…",
    photoFail: "Não foi possível usar esta foto. Envie JPG ou PNG.",
    photoRetry: "Não deu para enviar agora. Tente de novo em instantes.",
    photosChanged: "Refaça o personagem usando as fotos atualizadas.",
    download3: "Baixar as 3 imagens",
    finish: "As {pages} páginas estão prontas.",
    download: "Abrir livro",
    approveBook: "Aprovar livro",
    retry: "Tentar novamente",
    writeStory: "Gostei, ver a história completa",
    adjustPreview: "Quero ajustar a prévia",
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
    previewImagesHint: "Gostou? Desça e siga para o próximo passo. Quer mudar alguma imagem? Toque em Mudar esta imagem.",
    previewTitleHeading: "Revise O Título",
    previewNextHeading: "Tudo Certo Com A Prévia?",
    previewNextHint: "No próximo passo você lê a história completa antes de fazer o pedido.",
    titleEditSummary: "Quer mudar o título?",
    editSummary: "Quero ajustar a história toda",
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
    childHint: "Corrigir o nome ou a idade não refaz as imagens.",
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
    writingStory: "Writing your story… It takes about 1 minute and this screen updates by itself.",
    showImages: "See the preview images",
    showStory: "Read the story",
    cover: "Cover",
    open: "Open Book",
    reading: "Holding the book",
    noText: "Without text",
    withText: "With text",
    page: "Page",
    save: "Download image",
    suggest: "Change this image",
    suggestField: "What do you want to change?",
    suggestPh: "E.g. make the face look more like the photo",
    suggestSend: "Redo this image",
    changeTitle: "Change",
    changeCancel: "Cancel",
    photosTitle: "Photos of the hero",
    photosHint: "Remove bad photos and add clear photos of the face. This makes the character look more alike.",
    photoRemove: "Remove",
    photoAdd: "Add photos",
    photoKeepOne: "At least 1 photo stays.",
    photoConsent: "I am the guardian and I authorize the use of these photos.",
    photoSending: "Sending…",
    photoFail: "This photo could not be used. Send JPG or PNG.",
    photoRetry: "We couldn't send it right now. Please try again in a moment.",
    photosChanged: "Redo the character using the updated photos.",
    download3: "Download the 3 images",
    finish: "All {pages} pages are ready.",
    download: "Open book",
    approveBook: "Approve book",
    retry: "Try again",
    writeStory: "I like it, show me the full story",
    adjustPreview: "Adjust the preview",
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
    previewImagesHint: "Like it? Scroll down to the next step. Want to change an image? Tap Change this image.",
    previewTitleHeading: "Review The Title",
    previewNextHeading: "Happy With The Preview?",
    previewNextHint: "Next you read the full story before placing the order.",
    titleEditSummary: "Want to change the title?",
    editSummary: "I want to adjust the whole story",
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
    childHint: "Fixing the name or age does not remake the images.",
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
    writingStory: "Escribiendo tu historia… Tarda cerca de 1 minuto y la pantalla se actualiza sola.",
    showImages: "Ver las imágenes de la vista previa",
    showStory: "Leer la historia",
    cover: "Portada",
    open: "Libro Abierto",
    reading: "Sosteniendo el libro",
    noText: "Sin texto",
    withText: "Con texto",
    page: "Página",
    save: "Descargar imagen",
    suggest: "Cambiar esta imagen",
    suggestField: "¿Qué quieres cambiar?",
    suggestPh: "Ej.: que la cara se parezca más a la foto",
    suggestSend: "Rehacer esta imagen",
    changeTitle: "Cambiar",
    changeCancel: "Cancelar",
    photosTitle: "Fotos del héroe",
    photosHint: "Quita las fotos malas y envía fotos nítidas de la cara. Así el personaje se parece más.",
    photoRemove: "Quitar",
    photoAdd: "Añadir fotos",
    photoKeepOne: "Queda al menos 1 foto.",
    photoConsent: "Soy el responsable y autorizo el uso de estas fotos.",
    photoSending: "Enviando…",
    photoFail: "No se pudo usar esta foto. Envía JPG o PNG.",
    photoRetry: "No se pudo enviar ahora. Inténtalo de nuevo en unos instantes.",
    photosChanged: "Rehaz el personaje con las fotos actualizadas.",
    download3: "Descargar las 3 imágenes",
    finish: "Las {pages} páginas están listas.",
    download: "Abrir libro",
    approveBook: "Aprobar libro",
    retry: "Intentar de nuevo",
    writeStory: "Me gusta, ver la historia completa",
    adjustPreview: "Ajustar la vista previa",
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
    previewImagesHint: "¿Te gusta? Baja y sigue al próximo paso. ¿Quieres cambiar una imagen? Toca Cambiar esta imagen.",
    previewTitleHeading: "Revisa El Título",
    previewNextHeading: "¿Todo Bien Con La Vista Previa?",
    previewNextHint: "En el siguiente paso lees la historia completa antes de hacer el pedido.",
    titleEditSummary: "¿Quieres cambiar el título?",
    editSummary: "Quiero ajustar toda la historia",
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
    childHint: "Corregir el nombre o la edad no rehace las imágenes.",
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
  const fallback = lang === "en" ? `A New Adventure with ${name}`
    : lang === "es" ? `Una nueva aventura con ${name}` : `${name}: Uma Nova Aventura`;
  const candidate = topicMentions ? topic
    : lang === "en" ? `${name} and ${topic}` : lang === "es" ? `${name} y ${topic}` : `${name} e ${topic}`;
  const themedTitle = topic ? (topicMentions > 1 || comparable(candidate) === comparable(title) ? fallback : candidate) : "";
  // As opções acompanham o assunto do livro (tema ou título atual, sem o nome),
  // para não oferecer títulos genéricos que não condizem com o livro.
  const nameWords = comparable(name).split(" ");
  const titleHasName = new RegExp(`(?:^| )${comparable(name)}(?= |$)`).test(comparable(title));
  const subjectWords = (topic || (titleHasName ? title : "")).replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  const kept: string[] = [];
  for (let i = 0; i < subjectWords.length; i++) {
    if (nameWords.every((word, j) => comparable(subjectWords[i + j] || "") === word)) i += nameWords.length - 1;
    else kept.push(subjectWords[i]);
  }
  const connectors = new Set(["e", "and", "y", "com", "with", "con", "de", "do", "da", "of", "del"]);
  while (kept.length && (connectors.has(kept[0].toLocaleLowerCase()) || !comparable(kept[0]))) kept.shift();
  while (kept.length && (connectors.has(kept[kept.length - 1].toLocaleLowerCase()) || !comparable(kept[kept.length - 1]))) kept.pop();
  const subject = kept.join(" ").replace(/^[\s,:;.\-–—]+|[\s,:;\-–—]+$/g, "");
  const Subject = subject.charAt(0).toLocaleUpperCase() + subject.slice(1);
  const themed = subject.length < 3 ? [] : lang === "en"
    ? [
        `${name}: ${Subject}`,
        `${Subject} with ${name}`,
        `The Story of ${name}: ${Subject}`,
        `${name}'s Book: ${Subject}`,
        `${Subject}: A Story About ${name}`,
        `${Subject}: A Book for ${name}`,
      ]
    : lang === "es"
      ? [
          `${name}: ${Subject}`,
          `${Subject} con ${name}`,
          `La historia de ${name}: ${Subject}`,
          `El libro de ${name}: ${Subject}`,
          `${Subject}: una historia de ${name}`,
          `${Subject}: un libro para ${name}`,
        ]
      : [
          `${name}: ${Subject}`,
          `${Subject} com ${name}`,
          `A História de ${name}: ${Subject}`,
          `O Livro de ${name}: ${Subject}`,
          `${Subject}: Uma História de ${name}`,
          `${Subject}: Um Livro para ${name}`,
        ];
  const current = comparable(title);
  const seen = new Set<string>([current, comparable(themedTitle)]);
  const unique = (items: string[]) => items.map((item) => item.trim()).filter((item) => {
    const key = comparable(item);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const last = themedTitle && comparable(themedTitle) !== current ? [themedTitle] : [];
  // Sem assunto do livro não há opção pronta: os títulos genéricos ("A História de X")
  // não combinam com o tema. Nesse caso ficam só as sugestões da IA.
  if (!themed.length) return [];
  return [...unique(themed).slice(0, 6 - last.length), ...last].map(tidyTitleCase);
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
  const [heroPhotos, setHeroPhotos] = useState(assets?.photos ?? []);
  const [photosChanged, setPhotosChanged] = useState(false);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const [photoConsent, setPhotoConsent] = useState(false);
  useEffect(() => {
    if (assets?.photos) setHeroPhotos(assets.photos);
  }, [assets?.photos]);
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
  const [editTitle, setEditTitle] = useState(tidyTitleCase(project.book_profile?.title || ""));
  const [childDraft, setChildDraft] = useState(() => childDraftFrom(project));
  useEffect(() => {
    setChildDraft(childDraftFrom(project));
  }, [project]);
  useEffect(() => {
    setEditTitle(tidyTitleCase(project.book_profile?.title || ""));
  }, [project.book_profile?.title]);
  const [editTheme, setEditTheme] = useState(
    project.purchase_flow?.theme_description || project.theme || "",
  );
  const [pageToAdjust, setPageToAdjust] = useState<number | null>(null);
  const [pageNotes, setPageNotes] = useState<Record<number, string>>({});
  const p = project.book_profile!;
  const pageCount = p.page_count === 20 ? 20 : 16;
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
      setPhotosChanged(false);
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
  async function refreshPhotos() {
    const next = (await api.getAssets(project.id)) as StudioAssets;
    setHeroPhotos(next.photos ?? []);
    if (setAssets) setAssets(next);
  }
  async function changePhotos(action: () => Promise<unknown>) {
    if (active || photoBusy) return;
    setPhotoBusy(true);
    setPhotoError("");
    try {
      await action();
      setPhotosChanged(true);
    } catch (err) {
      // Queda da API (502/503/504) ou da rede não é problema da foto: pede para tentar de novo.
      const code = (err as { status?: number } | null)?.status
        ?? Number(/^(\d{3}):/.exec(String((err as Error | null)?.message ?? ""))?.[1]);
      setPhotoError(code > 0 && code < 500 ? t.photoFail : t.photoRetry);
    } finally {
      try {
        await refreshPhotos();
      } catch {
        /* Mantém a lista atual. */
      }
      setPhotoBusy(false);
    }
  }
  // Um clique só: aprovar a história já aprova a prévia e leva ao pedido.
  const approveStory = async () => {
    await api.approveStory(project.id);
    await api.approvePreview(project.id);
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
  // No pedido, imagens e história ficam recolhidas para o pagamento aparecer logo.
  const ordering = !!project.purchase_flow?.preview_approved_at && !reviewing;
  const foldWhenOrdering = (label: string, content: ReactNode) => ordering
    ? <details className="master-child-edit master-ordering-fold"><summary>{label}</summary>{content}</details>
    : content;
  const gallery = previews.flatMap((shot) => {
    const cleanCover = reviewing && shot.role === "01_CAPA" ? assets?.book_cover_url : null;
    const url = cleanCover || shot.url;
    if (reviewing && url.includes("preview-mark")) return [];
    return [{ ...shot, url }];
  });
  // Só conta como história quando há texto de verdade num idioma do livro.
  // Um objeto vazio deixava a prévia sem o botão de seguir (cliente preso).
  const hasStory = p.languages.some((language) => storyBlocks(p.stories?.[language] || "").length > 0);
  const storyView = hasStory ? (
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
                  page >= 1 && page <= pageCount && Boolean(p.page_revisions?.[language]?.[String(page)]);
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
                  {stage === "story_ready" && block.kind === "page" && page >= 1 && page <= pageCount && (
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
    const title = tidyTitleCase(editTitle);
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
      {expandedImage && <PreviewImageViewer src={expandedImage.url} title={expandedImage.label}
        lang={lang} onClose={() => setExpandedImage(null)} />}
      {testMode && <section className="master-adjustment-panel" data-testid="studio-test-mode">
        <h3>{t.testTitle}</h3><p className="master-title-hint">{t.testHint}</p>
        {!project.ai_generation_paused && <button type="button" className="kbtn kbtn-soft" disabled={active}
          onClick={() => void run(() => api.retryRealPreview(project.id))}>{t.exitTest}</button>}
      </section>}
      {error && <p className="studio-error" role="alert">{generationError(studioCopy, error)}</p>}
      {active && <p className="master-status" role="status">
        {jobs.some((job) => job.type === "STORY" && (job.status === "PENDING" || job.status === "RUNNING")) ? t.writingStory : t.waiting}
      </p>}
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
          {hasStory && (
            <details className="master-review-story">
              <summary>{t.reviewStory}</summary>
              {storyView}
            </details>
          )}
        </section>
      )}
      {!storyReview && gallery.length > 0 && foldWhenOrdering(t.showImages,
        <section className={isPreviewReview ? "master-preview-panel master-preview-images" : undefined}
          aria-labelledby="master-preview-images-heading">
          <div className="master-preview-panel-heading">
            <h3 id="master-preview-images-heading" className="master-section">
              {isPreviewReview && <span className="master-preview-number" aria-hidden="true">01</span>}{t.images}
            </h3>
            {["preview_ready", "cover_ready"].includes(stage) && <p className="master-title-hint">{t.previewImagesHint}</p>}
          </div>
      <div className={`master-gallery${gallery.length === 1 ? " has-single-preview" : ""}`}>
        {gallery.map((shot) => {
          const label =
            shot.role === "01_CAPA" ? t.cover : shot.role === "02_LIVRO_ABERTO" ? t.open : t.reading;
          const shotClass =
            shot.role === "01_CAPA" ? "is-cover" : shot.role === "02_LIVRO_ABERTO" ? "is-open" : "is-reading";
          return (
            <figure key={`${shot.language}-${shot.role}`} className={`master-shot ${shotClass}`}>
              <img src={shot.url} alt={severalLanguages ? `${shot.language.toUpperCase()} · ${label}` : label}
                onClick={() => setExpandedImage({ url: shot.url, label })} />
              <figcaption>
                <span>{severalLanguages ? `${shot.language.toUpperCase()} · ${label}` : label}</span>
                <span className="master-shot-actions">
                  <button type="button" aria-label={`${expandLabel} ${label}`}
                    onClick={() => setExpandedImage({ url: shot.url, label })}>{expandLabel}</button>
                  {["preview_ready", "cover_ready"].includes(stage) ? (
                    <button
                      type="button"
                      className={`master-change-button${suggesting === `${shot.language}:${shot.role}` ? " is-open" : ""}`}
                      aria-expanded={suggesting === `${shot.language}:${shot.role}`}
                      aria-controls="master-change-panel"
                      disabled={active}
                      onClick={() => {
                        const key = `${shot.language}:${shot.role}`;
                        setSuggesting((current) => (current === key ? "" : key));
                        setPhotoError("");
                      }}
                    >
                      <span aria-hidden="true">✏️ </span>{t.suggest}
                    </button>
                  ) : (
                    <a href={shot.url} download={shot.filename} target="_blank" rel="noreferrer">
                      {t.save}
                    </a>
                  )}
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>
      {(() => {
        if (!["preview_ready", "cover_ready"].includes(stage)) return null;
        const shot = gallery.find((item) => `${item.language}:${item.role}` === suggesting);
        if (!shot) return null;
        const key = `${shot.language}:${shot.role}`;
        const label = shot.role === "01_CAPA" ? t.cover : shot.role === "02_LIVRO_ABERTO" ? t.open : t.reading;
        const note = (suggestionText[key] || "").trim();
        const canSend = !active && !photoBusy && (Boolean(note) || photosChanged);
        return (
          <div className="master-change-panel" id="master-change-panel" role="region"
            aria-labelledby="master-change-heading" data-testid="studio-change-image">
            <div className="master-change-head">
              <img src={shot.url} alt="" />
              <h4 id="master-change-heading">{t.changeTitle}: {label}</h4>
            </div>
            <label className="studio-field master-change-step">
              <span className="master-change-label"><b aria-hidden="true">1</b>{t.suggestField}</span>
              <textarea
                ref={suggestionField}
                value={suggestionText[key] || ""}
                maxLength={500}
                rows={3}
                placeholder={t.suggestPh}
                onChange={(event) => setSuggestionText((current) => ({ ...current, [key]: event.target.value }))}
              />
            </label>
            {heroPhotos.length > 0 && (
              <div className="master-change-step" data-testid="studio-hero-photos">
                <p className="master-change-label"><b aria-hidden="true">2</b>{t.photosTitle}</p>
                <p className="master-title-hint">{t.photosHint}</p>
                <ul className="master-hero-photos" aria-label={t.photosTitle}>
                  {heroPhotos.map((photo, index) => (
                    <li key={photo.id}>
                      <img src={photo.url} alt={`${t.photosTitle} ${index + 1}`} />
                      <button type="button" disabled={active || photoBusy || heroPhotos.length <= 1}
                        aria-label={`${t.photoRemove} ${index + 1}`}
                        onClick={() => void changePhotos(() => api.deletePhoto(project.id, photo.id))}>
                        {t.photoRemove}
                      </button>
                    </li>
                  ))}
                  <li className="master-hero-photo-add">
                    <label className={photoConsent && !active && !photoBusy ? "" : "is-disabled"}>
                      <span aria-hidden="true">＋</span>
                      <span>{photoBusy ? t.photoSending : t.photoAdd}</span>
                      <input type="file" accept="image/*" multiple data-testid="studio-hero-photo-input"
                        disabled={!photoConsent || active || photoBusy}
                        onChange={(event) => {
                          const files = Array.from(event.target.files ?? []);
                          event.target.value = "";
                          if (!files.length) return;
                          void changePhotos(async () => {
                            for (const file of files) {
                              await api.uploadPhoto(project.id, file, {
                                language: project.language || "pt-BR",
                                finalize: true,
                                guardianConsent: true,
                              });
                            }
                          });
                        }} />
                    </label>
                  </li>
                </ul>
                {heroPhotos.length <= 1 && <p className="master-title-hint">{t.photoKeepOne}</p>}
                <label className="studio-consent master-hero-consent">
                  <input type="checkbox" checked={photoConsent} onChange={(event) => setPhotoConsent(event.target.checked)} />
                  <span>{t.photoConsent}</span>
                </label>
                {photoError && <p className="studio-error" role="alert">{photoError}</p>}
              </div>
            )}
            <div className="master-change-actions">
              <button
                type="button"
                className="kbtn kbtn-primary"
                disabled={!canSend}
                onClick={() => {
                  void run(() =>
                    api.startPreview(project.id, {
                      language: shot.language,
                      image: shot.role,
                      ...(stage === "cover_ready" ? { cover_only: true } : {}),
                      adjustment: note || t.photosChanged,
                    }),
                  );
                }}
              >
                {t.suggestSend}
              </button>
              <button type="button" className="kbtn kbtn-soft" disabled={active} onClick={() => setSuggesting("")}>
                {t.changeCancel}
              </button>
            </div>
          </div>
        );
      })()}
      {previews.length === 3 && (
        <p className="master-preview-download">
          <button type="button" className="master-link-button" disabled={active} onClick={() => void run(async () => {
            const blob = await api.downloadPreviewPackage(project.id);
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url; link.download = "Storyrus-previa.zip"; link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          })}>{t.download3}</button>
        </p>
      )}
        </section>,
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
      {!storyReview && canEditTitle && (() => {
        const titleForm = (
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
                onBlur={() => setEditTitle(tidyTitleCase(editTitle))}
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
          {editTitle.trim() !== savedTitle && editTitle.trim() && <p className="master-title-hint">{t.titleHint}</p>}
          {(titleOptions.length > 0 || (!testMode && !project.ai_generation_paused)) && (
            <details className="master-title-alternatives">
              <summary>{t.titleOptions}</summary>
              {titleOptions.length > 0 && (
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
              )}
              {!testMode && !project.ai_generation_paused && <TitleSuggestions key={project.id} projectId={project.id} currentTitle={savedTitle}
                selectedTitle={editTitle} disabled={active} onSelect={setEditTitle} />}
            </details>
          )}
        </form>
        );
        return isPreviewReview ? titleForm : (
          <details className="master-child-edit master-title-edit">
            <summary>{t.titleEditSummary}</summary>
            {titleForm}
          </details>
        );
      })()}
      {stage === "preview_ready" && !hasStory && !jobs.some((job) => job.type === "STORY" && (job.status === "PENDING" || job.status === "RUNNING")) && (
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
          {!editing && (
            <button type="button" className="kbtn kbtn-soft" disabled={active}
              data-testid="studio-adjust-preview" onClick={() => setEditing(true)}>
              {t.adjustPreview}
            </button>
          )}
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
                  <a href={image.url} download={image.filename} target="_blank" rel="noreferrer">
                    {t.save}
                  </a>
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
      {["story_approved", "preview_approved", "avatar_ready", "avatar_approved", "page_ready", "book_ready"].includes(stage) && (
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
      {!storyReview && stage !== "cover_ready" && hasStory && (
        <div data-testid="studio-master-story">
          {reviewing || ordering ? (
            <details>
              <summary className="master-section">{reviewing ? t.storyHeading : t.showStory}</summary>
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
          <details className="master-child-edit master-story-adjust">
            <summary>{t.editSummary}</summary>
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
          </details>
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
          <a
            href={image.url}
            download={image.filename}
            target="_blank"
            rel="noreferrer"
          >
            {t.save}
          </a>
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
            {t.finish.replace("{pages}", String(pageCount))} {t.summary}
          </p>
          {assets?.ebook_url && (
            <a href={assets.ebook_url} target="_blank" rel="noreferrer">
              {t.download}
            </a>
          )}
        </div>
      )}
      {!storyReview && (
      <details className="master-child-edit">
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
    </div>
  );
}
