import { useRef, useState } from "react";
import { api } from "../api";
import type { Job, Project } from "../types";
import type { StudioAssets } from "./assets";
import { useStudioI18n } from "./useStudioI18n";
import { PrintCheckout } from "./PrintCheckout";
import { purchaseCopy } from "./purchaseCopy";

export function PostPreviewFlow({
  project,
  assets,
  jobs,
  isDemo,
  dirty,
  onProject,
  onJobs,
  onAdjust,
  canConfirmPayment = false,
}: {
  project: Project;
  assets: StudioAssets | null;
  jobs: Job[];
  isDemo: boolean;
  dirty: boolean;
  onProject: (project: Project) => void;
  onJobs: (jobs: Job[]) => void;
  onAdjust: () => void;
  canConfirmPayment?: boolean;
}) {
  const { lang } = useStudioI18n();
  const t = purchaseCopy(lang);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [notes, setNotes] = useState("");
  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const flow = project.purchase_flow;
  const approved = !!flow?.preview_approved_at && !dirty;
  const fullReady = !!flow?.full_book_ready_at;
  const fullJob = [...jobs]
    .reverse()
    .find((j) => j.result?.payload?.purchase_full_book);
  const language = project.language || "pt-BR";
  const coverUrl =
    assets?.book_cover_url ||
    assets?.previews?.find((shot) => shot.role === "01_CAPA" && shot.language === language)?.url ||
    assets?.previews?.find((shot) => shot.role === "01_CAPA")?.url ||
    assets?.cover_url ||
    null;
  const dedication =
    project.dedication?.trim() ||
    (project.child_name ? t.dedicationFor.replace("{name}", project.child_name) : "");
  const readyPages = (assets?.page_versions || [])
    .filter((item) => item.role === "com_texto" && item.language === language && item.page)
    .sort((a, b) => (a.page || 0) - (b.page || 0))
    .slice(0, 6);
  const active = jobs.some(
    (j) => j.status === "PENDING" || j.status === "RUNNING",
  );
  const step =
    project.book_approved_at && fullReady
      ? 4
      : fullReady || flow?.stage === "generating_book"
        ? 3
        : flow?.stage === "awaiting_payment_confirmation"
          ? 2
          : approved
            ? 1
            : 0;
  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function refresh() {
    onProject(await api.getProject(project.id));
    onJobs(await api.listJobs(project.id));
  }
  return (
    <section
      className="purchase-flow"
      id="pedido"
      aria-labelledby="purchase-heading"
      data-testid="purchase-flow"
    >
      <ol className="purchase-steps" aria-label={t.summary}>
        {t.steps.map((label, i) => (
          <li
            key={label}
            aria-current={i === step ? "step" : undefined}
            className={i <= step ? "is-reached" : ""}
          >
            <span>{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      {!approved ? (
        <>
          <h3 id="purchase-heading">{t.next}</h3>
          <p>{t.intro}</p>
          {dirty && <p role="status">{t.unsaved}</p>}
          <div className="studio-actions">
            <button
              type="button"
              className="kbtn kbtn-primary"
              disabled={isDemo || busy || active || dirty}
              onClick={() =>
                void run(async () =>
                  onProject(await api.approvePreview(project.id)),
                )
              }
            >
              {t.approve}
            </button>
            <button type="button" className="kbtn" disabled={isDemo || busy || active} onClick={onAdjust}>
              {t.adjust}
            </button>
          </div>
        </>
      ) : (
        <>
          <h3 id="purchase-heading">
            {project.book_approved_at && fullReady
              ? t.approved
              : fullReady
                ? t.full
                : flow?.stage === "generating_book"
                  ? t.generating
                  : t.steps[step]}
          </h3>
          {flow?.stage === "generating_book" && (
            <>
              <p role="status">
                {t.generatingHint}
                {fullJob?.result?.progress?.total
                  ? ` (${fullJob.result.progress.done || 0}/${fullJob.result.progress.total})`
                  : ""}
              </p>
              {(coverUrl || dedication || readyPages.length > 0) && (
                <div className="purchase-sample" data-testid="purchase-sample">
                  {coverUrl && (
                    <figure className="is-cover">
                      <img src={coverUrl} alt={t.readyCover} />
                      <figcaption>{t.readyCover}</figcaption>
                    </figure>
                  )}
                  {dedication && (
                    <article className="purchase-dedication">
                      <h4>{t.readyDedication}</h4>
                      <p>{dedication}</p>
                    </article>
                  )}
                  {readyPages.map((page) => (
                    <figure key={`${page.language}-${page.page}`}>
                      <img src={page.url} alt={`${t.readyPage} ${page.page}`} />
                      <figcaption>
                        {t.readyPage} {page.page}
                      </figcaption>
                    </figure>
                  ))}
                </div>
              )}
              {fullJob?.status === "FAILED" && (
                <>
                  <p role="alert">{t.failed}</p>
                  <button
                    type="button"
                    className="kbtn"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api.generatePurchasedBook(project.id);
                        await refresh();
                      })
                    }
                  >
                    {t.retry}
                  </button>
                </>
              )}
            </>
          )}
          {fullReady && (
            <>
              <p>{project.book_approved_at ? t.approvedHint : t.fullHint}</p>
              <div className="purchase-pages">
                {(project.book_profile
                  ? assets?.page_versions
                      ?.filter(
                        (item) =>
                          item.role === "com_texto" &&
                          item.language === project.language,
                      )
                      .sort((a, b) => (a.page || 0) - (b.page || 0))
                      .map((item) => item.url)
                  : assets?.page_images
                )?.map((url, i) => (
                  <a href={url} key={url} target="_blank" rel="noreferrer">
                    <img
                      src={url}
                      alt={`${t.steps[3]} ${i + 1}`}
                      loading="lazy"
                    />
                    <span>{i + 1}</span>
                  </a>
                ))}
              </div>
              {assets?.ebook_url && (
                <a
                  className="kbtn"
                  href={assets.ebook_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t.pdf}
                </a>
              )}
              {!project.book_approved_at && (
                <>
                  <label className="purchase-confirm">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(e) => setConfirmed(e.target.checked)}
                    />
                    {t.confirm}
                  </label>
                  <button
                    className="kbtn kbtn-primary"
                    type="button"
                    disabled={busy || active || !confirmed}
                    onClick={() =>
                      void run(async () =>
                        onProject(await api.approveBook(project.id)),
                      )
                    }
                  >
                    {t.final}
                  </button>
                  {!project.book_profile && (
                    <details>
                      <summary>{t.adjust}</summary>
                      <label className="studio-field">
                        {t.notes}
                        <textarea
                          value={notes}
                          maxLength={500}
                          onChange={(e) => setNotes(e.target.value)}
                        />
                      </label>
                      <button
                        className="kbtn"
                        type="button"
                        disabled={busy || active || notes.trim().length < 3}
                        onClick={() =>
                          void run(async () => {
                            await api.requestBookChanges(project.id, notes);
                            setConfirmed(false);
                            await refresh();
                          })
                        }
                      >
                        {t.sendNotes}
                      </button>
                    </details>
                  )}
                </>
              )}
            </>
          )}
          <button
            type="button"
            className="kbtn"
            onClick={() => {
              setDeliveryOpen(true);
              window.setTimeout(
                () =>
                  document.getElementById("entrega")?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  }),
                0,
              );
            }}
          >
            {t.editDelivery}
          </button>
          <details
            open={(flow?.stage !== "generating_book" && !fullReady) || deliveryOpen}
            onToggle={(event) => setDeliveryOpen(event.currentTarget.open)}
          >
            <summary>{t.summary}</summary>
            <PrintCheckout
              projectId={project.id}
              onProject={onProject}
              canConfirmPayment={canConfirmPayment}
            />
          </details>
        </>
      )}
      <a className="purchase-orders-link" href="/meus-pedidos">
        {t.myOrders} →
      </a>
      {error && (
        <p className="studio-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
