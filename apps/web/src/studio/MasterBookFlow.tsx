import { useEffect, useRef, useState, type FormEvent } from "react";
import { PostPreviewFlow } from "./PostPreviewFlow";
import { TitleSuggestions } from "./TitleSuggestions";
import { StudioStageHeading } from "./StudioStageHeading";
import { api } from "../api";
import type { Job, Project } from "../types";
import type { StudioAssets } from "./assets";
import { useStudioI18n } from "./useStudioI18n";

const COPY = {
  pt: {
    preview: "Aprovo a prévia?",
    yes: "Sim, aprovo",
    story: "Aprovo a história?",
    face: "Este é o rosto?",
    next: "Próxima?",
    redo: "Gerar novamente",
    adjust: "Ajuste desta imagem",
    send: "Aplicar ajuste",
    waiting: "Gerando…",
    cover: "Capa",
    open: "Livro aberto",
    reading: "Leitura",
    noText: "Sem texto",
    withText: "Com texto",
    page: "Página",
    save: "Baixar imagem",
    finish: "As 16 páginas estão prontas.",
    download: "Abrir livro",
    approveBook: "Aprovar livro",
    retry: "Tentar novamente",
    writeStory: "Gerar a história",
    edit: "Ajuste da história",
    summary:
      "Cada página tem a versão sem texto e a versão com texto, nessa ordem. A prévia está no início.",
    continue: "Continuar",
    images: "As imagens",
    storyHeading: "A história",
    titleLabel: "Título do livro",
    titleSave: "Atualizar título",
    titleHint: "A capa é refeita com este título. O restante da história fica.",
    goToOrder: "Ir para o pedido",
    pagesHeading: "Páginas do livro",
    improve: "O que melhorar nesta página",
    improveSend: "Melhorar esta página",
    previewAdjustTitle: "Ajustar minha prévia",
    previewAdjustHint: "Descreva o que deseja melhorar. Ao aplicar, a IA refaz a prévia e a história para uma nova revisão.",
    themeLabel: "Tema da história",
    previewNotes: "O que você quer melhorar?",
    cancelAdjust: "Cancelar ajustes",
    retryPreviewTitle: "Sua prévia precisa de uma nova geração",
    retryPreviewHint: "Precisamos refazer esta prévia com IA antes da sua revisão. O livro só continuará depois da sua aprovação.",
    retryRealPreview: "Refazer prévia com IA",
  },
  en: {
    preview: "Approve the preview?",
    yes: "Yes, I approve",
    story: "Approve the story?",
    face: "Is this the face?",
    next: "Next?",
    redo: "Regenerate",
    adjust: "Adjustment to this image",
    send: "Apply adjustment",
    waiting: "Generating…",
    cover: "Cover",
    open: "Open book",
    reading: "Reading",
    noText: "Without text",
    withText: "With text",
    page: "Page",
    save: "Download image",
    finish: "All 16 pages are ready.",
    download: "Open book",
    approveBook: "Approve book",
    retry: "Try again",
    writeStory: "Write the story",
    edit: "Story adjustment",
    summary:
      "Each page has a version without text followed by a version with text. The preview is at the start.",
    continue: "Continue",
    images: "Images",
    storyHeading: "The story",
    titleLabel: "Book title",
    titleSave: "Update title",
    titleHint: "The cover is remade with this title. The rest of the story stays.",
    goToOrder: "Go to the order",
    pagesHeading: "Book pages",
    improve: "What to improve on this page",
    improveSend: "Improve this page",
    previewAdjustTitle: "Adjust my preview",
    previewAdjustHint: "Describe what you would like to improve. Applying changes asks AI to recreate the preview and story for a new review.",
    themeLabel: "Story theme",
    previewNotes: "What would you like to improve?",
    cancelAdjust: "Cancel adjustments",
    retryPreviewTitle: "Your preview needs to be generated again",
    retryPreviewHint: "We need to recreate this preview with AI before your review. The book will only continue after your approval.",
    retryRealPreview: "Recreate preview with AI",
  },
  es: {
    preview: "¿Apruebas la vista previa?",
    yes: "Sí, apruebo",
    story: "¿Apruebas la historia?",
    face: "¿Es este el rostro?",
    next: "¿Siguiente?",
    redo: "Generar de nuevo",
    adjust: "Ajuste de esta imagen",
    send: "Aplicar ajuste",
    waiting: "Generando…",
    cover: "Portada",
    open: "Libro abierto",
    reading: "Lectura",
    noText: "Sin texto",
    withText: "Con texto",
    page: "Página",
    save: "Descargar imagen",
    finish: "Las 16 páginas están listas.",
    download: "Abrir libro",
    approveBook: "Aprobar libro",
    retry: "Intentar de nuevo",
    writeStory: "Escribir la historia",
    edit: "Ajuste de la historia",
    summary:
      "Cada página tiene la versión sin texto y luego con texto. La vista previa está al inicio.",
    continue: "Continuar",
    images: "Las imágenes",
    storyHeading: "La historia",
    titleLabel: "Título del libro",
    titleSave: "Actualizar título",
    titleHint: "La portada se rehace con este título. El resto de la historia queda.",
    goToOrder: "Ir al pedido",
    pagesHeading: "Páginas del libro",
    improve: "Qué mejorar en esta página",
    improveSend: "Mejorar esta página",
    previewAdjustTitle: "Ajustar mi vista previa",
    previewAdjustHint: "Describe qué te gustaría mejorar. Al aplicar, la IA vuelve a crear la vista previa y la historia para una nueva revisión.",
    themeLabel: "Tema de la historia",
    previewNotes: "¿Qué quieres mejorar?",
    cancelAdjust: "Cancelar ajustes",
    retryPreviewTitle: "Tu vista previa necesita una nueva generación",
    retryPreviewHint: "Necesitamos volver a crear esta vista previa con IA antes de tu revisión. El libro solo continuará después de tu aprobación.",
    retryRealPreview: "Volver a crear la vista previa con IA",
  },
};

type StoryBlock = { kind: "title" | "page" | "body"; label: string; lines: string[] };

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
  const { lang } = useStudioI18n();
  const t = COPY[lang];
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [adjustment, setAdjustment] = useState("");
  const [selected, setSelected] = useState("");
  const [editing, setEditing] = useState(false);
  const adjustmentPanel = useRef<HTMLDivElement>(null);
  const adjustmentNotes = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (!editing) return;
    adjustmentPanel.current?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    adjustmentNotes.current?.focus({ preventScroll: true });
  }, [editing]);
  const [editTitle, setEditTitle] = useState(project.book_profile?.title || "");
  useEffect(() => {
    setEditTitle(project.book_profile?.title || "");
  }, [project.book_profile?.title]);
  const [editTheme, setEditTheme] = useState(
    project.purchase_flow?.theme_description || project.theme || "",
  );
  const [pageToAdjust, setPageToAdjust] = useState<number | null>(null);
  const [pageNotes, setPageNotes] = useState<Record<number, string>>({});
  const p = project.book_profile!;
  const active =
    sending ||
    jobs.some((j) => j.status === "RUNNING" || j.status === "PENDING");
  const lastJob = jobs[jobs.length - 1];
  const failed = lastJob?.status === "FAILED" ? lastJob : null;
  const stage = p.stage;
  const previews = [...(assets?.previews ?? [])].sort(
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
      setSelected("");
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
  const approveStory = async () => {
    await api.approveStory(project.id);
  };
  const approveFace = async () => {
    await api.approveCharacter(project.id);
    await api.nextBookPage(project.id);
  };
  const savedTitle = (p.title || "").trim();
  const canEditTitle =
    p.current_page === 0 &&
    ["preview_ready", "story_ready", "story_approved", "preview_approved"].includes(stage);
  const chips = [p.costume, p.trait, p.interest].filter((item): item is string => Boolean(item));
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
              {blocks.map((block, index) => (
                <article
                  key={`${language}-${index}`}
                  className={block.kind === "title" ? "studio-story-page is-title" : "studio-story-page"}
                >
                  {block.label ? (
                    <header className="studio-story-page-head">
                      <span className="studio-story-page-num">{block.label}</span>
                    </header>
                  ) : null}
                  <div className="studio-story-verse">
                    {block.lines.map((line, lineIndex) => (
                      <p key={`${language}-${index}-${lineIndex}`}>{line}</p>
                    ))}
                  </div>
                </article>
              ))}
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
  if (p.credits_fallback) {
    return <section className="master-adjustment-panel" data-testid="studio-preview-recovery">
      <StudioStageHeading title={t.retryPreviewTitle} illustration={0}>
        <p>{t.retryPreviewHint}</p>
      </StudioStageHeading>
      {error && <p className="studio-error" role="alert">{error}</p>}
      <button type="button" className="kbtn kbtn-primary" disabled={active}
        onClick={() => void run(() => api.retryRealPreview(project.id))}>
        {active ? t.waiting : t.retryRealPreview}
      </button>
    </section>;
  }
  return (
    <div className="studio-master-flow" data-testid="studio-master-flow">
      {error && <p className="studio-error" role="alert">{error}</p>}
      {active && <p className="master-status" role="status">{t.waiting}</p>}
      {!active && failed?.error && <p className="studio-error" role="alert">{failed.error}</p>}
      {(project.child_name || chips.length > 0) && (
        <ul className="master-chips">
          {project.child_name && (
            <li>
              {project.child_name}
              {project.child_age ? ` · ${project.child_age}` : ""}
            </li>
          )}
          {chips.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {["story_approved", "preview_approved", "avatar_ready", "avatar_approved", "page_ready", "book_ready"].includes(stage) && (
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
      {gallery.length > 0 && <h3 className="master-section">{t.images}</h3>}
      <div className="master-gallery">
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
                  <a href={shot.url} download={shot.filename} target="_blank" rel="noreferrer">
                    {t.save}
                  </a>
                  {stage === "preview_ready" && (
                    <button
                      type="button"
                      disabled={active}
                      onClick={() => setSelected(`${shot.language}:${shot.role}`)}
                    >
                      {t.redo}
                    </button>
                  )}
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>
      {canEditTitle && (
        <form className="master-title-card" onSubmit={(event) => void applyTitle(event)}>
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
          <TitleSuggestions key={project.id} projectId={project.id} currentTitle={savedTitle}
            selectedTitle={editTitle} disabled={active} onSelect={setEditTitle} />
        </form>
      )}
      {selected && (
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
            disabled={active}
            onClick={() =>
              void run(() =>
                api.startPreview(project.id, {
                  language: selected.split(":")[0],
                  image: selected.split(":")[1],
                  adjustment,
                }),
              )
            }
          >
            {t.send}
          </button>
        </div>
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
          project={project}
          jobs={jobs}
          assets={assets}
          isDemo={false}
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
      {stage === "preview_ready" && !p.stories && !jobs.some((job) => job.type === "STORY" && (job.status === "PENDING" || job.status === "RUNNING")) && (
        <button
          className="kbtn kbtn-primary"
          disabled={active}
          onClick={() => void run(() => api.startStep(project.id, "story"))}
        >
          {t.writeStory}
        </button>
      )}
      {p.stories && (
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
            disabled={active || !!project.book_approved_at}
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
