import { useStudioI18n } from "./useStudioI18n";

type Props = {
  coverUrl: string | null;
  pageUrl: string | null;
  inHandUrl: string | null;
};

/** Strip capa / página / na mão — mesmo trio da landing. */
export function PreviewTrio({ coverUrl, pageUrl, inHandUrl }: Props) {
  const { t } = useStudioI18n();
  if (!coverUrl && !pageUrl && !inHandUrl) return null;

  const shots: { url: string | null; label: string; testId: string }[] = [
    { url: coverUrl, label: t.previewCover, testId: "studio-preview-cover" },
    { url: pageUrl, label: t.previewPage, testId: "studio-preview-page" },
    { url: inHandUrl, label: t.previewInHand, testId: "studio-preview-in-hand" },
  ];

  return (
    <div
      className="result-block"
      data-testid="studio-preview-trio"
      role="region"
      aria-labelledby="studio-preview-trio-heading"
    >
      <h3 className="field-label" id="studio-preview-trio-heading">
        {t.previewTrioTitle}
      </h3>
      <p className="muted">{t.previewTrioHint}</p>
      <div
        className="studio-preview-trio"
        role="list"
        aria-label={t.previewTrioTitle}
        style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 12 }}
      >
        {shots.map((shot) =>
          shot.url ? (
            <figure
              key={shot.testId}
              role="listitem"
              data-testid={shot.testId}
              style={{ margin: 0, width: 160, maxWidth: "100%" }}
            >
              <img
                src={shot.url}
                alt={shot.label}
                loading="lazy"
                style={{
                  width: "100%",
                  aspectRatio: shot.testId === "studio-preview-page" ? "2 / 1" : "1 / 1",
                  objectFit: "contain",
                  borderRadius: 10,
                  display: "block",
                }}
              />
              <figcaption className="muted" style={{ marginTop: 6, fontSize: "0.85rem" }}>
                {shot.label}
              </figcaption>
            </figure>
          ) : null,
        )}
      </div>
    </div>
  );
}
