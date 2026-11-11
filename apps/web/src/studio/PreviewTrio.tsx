import { useStudioI18n } from "./useStudioI18n";

type Props = {
  coverUrl: string | null;
  pageUrl: string | null;
  inHandUrl: string | null;
  inHandPresentation?: string | null;
};

/** Strip capa / página / na mão — mesmo trio da landing. */
export function PreviewTrio({ coverUrl, pageUrl, inHandUrl, inHandPresentation }: Props) {
  const { t } = useStudioI18n();
  if (!coverUrl && !pageUrl && !inHandUrl) return null;
  const bookOnly = inHandPresentation === "book_only_fallback";

  const shots: { url: string | null; label: string; testId: string }[] = [
    { url: coverUrl, label: t.previewCover, testId: "studio-preview-cover" },
    { url: pageUrl, label: t.previewPage, testId: "studio-preview-page" },
    {
      url: inHandUrl,
      label: bookOnly ? t.previewBookMockup : t.previewInHand,
      testId: "studio-preview-in-hand",
    },
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
      <p className="muted">
        {bookOnly ? t.previewTrioHintBookMockup : t.previewTrioHint}
      </p>
      <div
        className="studio-preview-trio"
        role="list"
        aria-label={t.previewTrioTitle}
      >
        {shots.map((shot) =>
          shot.url ? (
            <figure
              key={shot.testId}
              role="listitem"
              data-testid={shot.testId}
              className="studio-preview-shot"
            >
              <img
                src={shot.url}
                alt={shot.label}
                loading="lazy"
              />
              <figcaption className="muted">
                {shot.label}
              </figcaption>
            </figure>
          ) : null,
        )}
      </div>
    </div>
  );
}
