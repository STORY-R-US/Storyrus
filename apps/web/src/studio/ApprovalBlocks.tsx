import { useStudioI18n } from "./useStudioI18n";
import { PrintCheckout } from "./PrintCheckout";

type CharacterProps = {
  characterUrl: string;
  characterApproved: boolean;
  locked: boolean;
  onApprove: () => void;
  onRegenerate: () => void;
};

export function CharacterApprovalBlock({
  characterUrl,
  characterApproved,
  locked,
  onApprove,
  onRegenerate,
}: CharacterProps) {
  const { t } = useStudioI18n();
  return (
    <div className="result-block" role="region" aria-labelledby="studio-character-heading">
      <h3 className="field-label" id="studio-character-heading">
        {t.character}
      </h3>
      <img
        src={characterUrl}
        alt={t.characterAlt}
        style={{ maxWidth: 280, width: "100%", borderRadius: 12 }}
      />
      <div
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}
        role="group"
        aria-label={t.ariaCharacterActions}
      >
        {characterApproved ? (
          <p className="muted" role="status">
            {t.characterApproved}
          </p>
        ) : (
          <button type="button" disabled={locked} onClick={onApprove}>
            {t.approveCharacter}
          </button>
        )}
        <button type="button" disabled={locked} onClick={onRegenerate}>
          {t.regenerateCharacter}
        </button>
      </div>
    </div>
  );
}

type BookProps = {
  pageImages: string[];
  ebookUrl: string | null;
  bookApproved: boolean;
  locked: boolean;
  canMountEbook: boolean;
  printRequested: boolean;
  projectId?: string | null;
  onApprove: () => void;
  onRegenerate: () => void;
  onRequestPrint: () => void;
};

export function BookApprovalBlock({
  pageImages,
  ebookUrl,
  bookApproved,
  locked,
  canMountEbook,
  printRequested,
  projectId,
  onApprove,
  onRegenerate,
  onRequestPrint,
}: BookProps) {
  const { t } = useStudioI18n();
  return (
    <div className="result-block" role="region" aria-labelledby="studio-ebook-heading">
      <h3 className="field-label" id="studio-ebook-heading">
        {t.ebook}
      </h3>
      {pageImages.length > 0 && (
        <div
          style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 10 }}
          role="list"
          aria-label={t.ariaEbookPages}
        >
          {pageImages.map((u, i) => (
            <img
              key={i}
              src={u}
              alt={t.pageAlt(i + 1)}
              loading="lazy"
              style={{ width: 120, height: 120, objectFit: "cover", borderRadius: 8 }}
            />
          ))}
        </div>
      )}
      {ebookUrl && (
        <a href={ebookUrl} target="_blank" rel="noreferrer" className="btn">
          {t.openEbook}
        </a>
      )}
      <div
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}
        role="group"
        aria-label={t.ariaBookActions}
      >
        {bookApproved ? (
          <p className="muted" role="status">
            {t.bookApproved}
          </p>
        ) : (
          <button type="button" disabled={locked || !ebookUrl} onClick={onApprove}>
            {t.approveBook}
          </button>
        )}
        <button type="button" disabled={locked || !canMountEbook} onClick={onRegenerate}>
          {t.regeneratePages}
        </button>
      </div>
      {bookApproved && (
        <div style={{ marginTop: 12 }} role="region" aria-labelledby="studio-print-heading">
          <h3 className="field-label" id="studio-print-heading">
            {t.printTitle}
          </h3>
          {printRequested ? (
            <>
              <p className="muted" role="status">
                {t.printRequested}
              </p>
              {projectId && <PrintCheckout projectId={projectId} />}
            </>
          ) : (
            <button type="button" disabled={locked} onClick={onRequestPrint}>
              {t.requestPrint}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
