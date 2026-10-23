import { useEffect, useState, type FormEvent } from "react";
import { PostPreviewFlow } from "./PostPreviewFlow";
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
};

export function MasterBookFlow({
  project,
  jobs,
  assets,
  setProject,
  setJobs,
  setAssets,
}: Props) {
  const { lang } = useStudioI18n();
  const t = COPY[lang];
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [adjustment, setAdjustment] = useState("");
  const [selected, setSelected] = useState("");
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(project.book_profile?.title || "");
  useEffect(() => {
    setEditTitle(project.book_profile?.title || "");
  }, [project.book_profile?.title]);
  const [editTheme, setEditTheme] = useState(
    project.purchase_flow?.theme_description || project.theme || "",
  );
  const [pageToAdjust, setPageToAdjust] = useState<number | null>(null);
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
  async function applyTitle(event: FormEvent) {
    event.preventDefault();
    const title = editTitle.trim();
    if (!title || title === savedTitle) return;
    await run(() => api.updatePreviewTitle(project.id, title));
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
      {previews.length > 0 && <h3 className="master-section">{t.images}</h3>}
      <div className="master-gallery">
        {previews.map((shot) => {
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
        </form>
      )}
      {selected && (
        <div>
          <label>
            {t.adjust}
            <textarea
              value={adjustment}
              onChange={(e) => setAdjustment(e.target.value)}
              maxLength={500}
            />
          </label>
          <button
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
      {["story_approved", "preview_approved", "avatar_ready", "avatar_approved", "page_ready", "book_ready"].includes(stage) && (
        <PostPreviewFlow
          project={project}
          jobs={jobs}
          assets={assets}
          isDemo={false}
          dirty={false}
          onProject={setProject}
          onJobs={setJobs}
          onAdjust={() => setEditing(true)}
        />
      )}
      {stage === "preview_ready" && editing && (
        <div className="studio-review-changes">
          <label className="studio-field">
            {lang === "en" ? "Theme" : "Tema"}
            <textarea
              value={editTheme}
              maxLength={500}
              onChange={(e) => setEditTheme(e.target.value)}
            />
          </label>
          <label className="studio-field">
            {t.adjust}
            <textarea
              value={adjustment}
              maxLength={500}
              onChange={(e) => setAdjustment(e.target.value)}
            />
          </label>
          <button
            disabled={active || !editTitle.trim() || !editTheme.trim()}
            onClick={() =>
              void run(() =>
                api.savePreviewChanges(project.id, {
                  title: editTitle,
                  theme_description: editTheme,
                  photo_notes: adjustment,
                  story_text: "",
                }),
              )
            }
          >
            {t.send}
          </button>
        </div>
      )}
      {stage === "preview_ready" && !p.stories && !jobs.some((job) => job.type === "STORY" && (job.status === "PENDING" || job.status === "RUNNING")) && (
        <button
          disabled={active}
          onClick={() => void run(() => api.startStep(project.id, "story"))}
        >
          {t.writeStory}
        </button>
      )}
      {p.stories && (
        <div data-testid="studio-master-story">
          <h3 className="master-section">{t.storyHeading}</h3>
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
        </div>
      )}
      {stage === "story_ready" && (
        <section className="master-decision" aria-labelledby="master-story-decision">
          <h3 id="master-story-decision">{t.story}</h3>
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
          disabled={active}
          onClick={() => void run(() => api.startStep(project.id, "avatar"))}
        >
          {t.continue}
        </button>
      )}
      {assets?.character_url && (
        <img
          src={assets.character_url}
          alt={t.face}
          style={{ maxWidth: 300, width: "100%" }}
        />
      )}
      {stage === "avatar_ready" && (
        <div>
          <p>{t.face}</p>
          <button disabled={active} onClick={() => void run(approveFace)}>
            {t.yes}
          </button>
          <button
            disabled={active}
            onClick={() => void run(() => api.startStep(project.id, "avatar"))}
          >
            {t.redo}
          </button>
        </div>
      )}
      {versions.map((image) => (
        <figure key={`${image.language}-${image.page}-${image.role}`}>
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
              disabled={active || !!project.book_approved_at}
              onClick={() => setPageToAdjust(image.page ?? 1)}
            >
              {t.redo} · {t.page} {image.page}
            </button>
          )}
        </figure>
      ))}
      {p.current_page > 0 && p.stories && (
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
          disabled={active}
          onClick={() => void run(() => api.nextBookPage(project.id))}
        >
          {t.next}
        </button>
      )}
      {["page_ready", "book_ready"].includes(stage) && (
        <div>
          <label>
            {t.adjust}
            <textarea
              value={adjustment}
              onChange={(e) => setAdjustment(e.target.value)}
              maxLength={500}
            />
          </label>
          <button
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
      {stage === "book_ready" && (
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
