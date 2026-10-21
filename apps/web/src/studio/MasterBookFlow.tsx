import { useState } from "react";
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
  },
};

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
  return (
    <div className="studio-master-flow" data-testid="studio-master-flow">
      {error && <p role="alert">{error}</p>}
      {active && <p role="status">{t.waiting}</p>}
      {!active && failed && <p role="alert">{failed.error}</p>}
      {p.costume && (
        <p>
          {project.child_name} · {project.child_age} · {p.costume} · {p.trait} ·{" "}
          {p.interest}
        </p>
      )}
      <div className="studio-master-previews">
        {previews.map((shot) => (
          <figure
            key={`${shot.language}-${shot.role}`}
            style={{ margin: "12px 0" }}
          >
            <figcaption>
              {shot.language.toUpperCase()} ·{" "}
              {shot.role === "01_CAPA"
                ? t.cover
                : shot.role === "02_LIVRO_ABERTO"
                  ? t.open
                  : t.reading}
            </figcaption>
            <img
              src={shot.url}
              alt={shot.filename}
              style={{
                width: "100%",
                maxWidth: shot.role === "02_LIVRO_ABERTO" ? 640 : 320,
                height: "auto",
                display: "block",
              }}
            />
            <a
              href={shot.url}
              download={shot.filename}
              target="_blank"
              rel="noreferrer"
            >
              {t.save}
            </a>
            {stage === "preview_ready" && (
              <button
                disabled={active}
                onClick={() => setSelected(`${shot.language}:${shot.role}`)}
              >
                {t.redo}
              </button>
            )}
          </figure>
        ))}
      </div>
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
            {lang === "en"
              ? "Book title"
              : lang === "es"
                ? "Título del libro"
                : "Título do livro"}
            <input
              value={editTitle}
              maxLength={120}
              onChange={(e) => setEditTitle(e.target.value)}
            />
          </label>
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
          {p.languages.map((language) => (
            <div key={language}>
              <h3>{language.toUpperCase()}</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>{p.stories?.[language]}</p>
            </div>
          ))}
        </div>
      )}
      {stage === "story_ready" && (
        <div>
          <p>{t.story}</p>
          <button disabled={active} onClick={() => void run(approveStory)}>
            {t.yes}
          </button>
          <label>
            {t.edit}
            <textarea
              value={adjustment}
              onChange={(e) => setAdjustment(e.target.value)}
              maxLength={2000}
            />
          </label>
          <button
            disabled={active || !adjustment.trim()}
            onClick={() =>
              void run(() =>
                api.startStep(project.id, "story", { brief: adjustment }),
              )
            }
          >
            {t.send}
          </button>
        </div>
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
