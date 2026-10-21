import { studioSteps } from "./constants";
import type { StudioStep } from "./useStudioSteps";
import { useStudioI18n } from "./useStudioI18n";

type EbookStepsProps = {
  locked: boolean;
  canMountEbook: boolean;
  runStep: (step: StudioStep) => void;
};

export function EbookStepButtons({ locked, canMountEbook, runStep }: EbookStepsProps) {
  const { t } = useStudioI18n();
  const steps = studioSteps(t);
  return (
    <div className="steps" role="group" aria-label={t.ariaEbookStep}>
      {steps
        .filter((s) => s.key === "ebook")
        .map((s) => (
          <button
            key={s.key}
            type="button"
            title={s.hint}
            aria-label={`${s.label}. ${s.hint}`}
            disabled={locked || !canMountEbook}
            onClick={() => runStep(s.key)}
            data-testid="studio-mount-ebook"
          >
            {s.label}
          </button>
        ))}
    </div>
  );
}

type VideoStepsProps = {
  locked: boolean;
  canMakeVideo: boolean;
  runStep: (step: StudioStep) => void;
};

export function VideoStepButtons({ locked, canMakeVideo, runStep }: VideoStepsProps) {
  const { t } = useStudioI18n();
  const steps = studioSteps(t);
  return (
    <div className="steps" role="group" aria-label={t.ariaVideoSteps}>
      {steps
        .filter((s) => s.key !== "ebook")
        .map((s) => (
          <button
            key={s.key}
            type="button"
            title={s.hint}
            aria-label={`${s.label}. ${s.hint}`}
            disabled={locked || !canMakeVideo}
            onClick={() => runStep(s.key)}
            data-testid={`studio-step-${s.key}`}
          >
            {s.label}
          </button>
        ))}
    </div>
  );
}
