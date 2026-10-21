import type { Job } from "../types";
import { useStudioI18n } from "./useStudioI18n";

export function ProgressList({ jobs }: { jobs: Job[] }) {
  const { t } = useStudioI18n();
  if (jobs.length === 0) return null;
  return (
    <div role="status" aria-live="polite" aria-label={t.ariaProgress}>
      <ul className="jobs">
        {jobs.map((j) => {
          const progress = j.result?.progress;
          const showPages =
            j.type === "EBOOK" &&
            (j.status === "RUNNING" || j.status === "PENDING") &&
            typeof progress?.done === "number" &&
            typeof progress?.total === "number";
          return (
            <li
              key={j.id}
              className={`job ${j.status.toLowerCase()}`}
              data-testid={`studio-job-${j.type}`}
              data-job-status={j.status}
            >
              <span className="dot" aria-hidden="true" />
              <span className="jtype" data-testid={`studio-job-type-${j.type}`}>
                {j.type}
              </span>
              <span className="jstatus" data-testid={`studio-job-status-${j.type}`}>
                {j.status}
              </span>
              {showPages && progress?.done != null && progress?.total != null && (
                <span className="muted">{t.illustrating(progress.done, progress.total)}</span>
              )}
              {j.attempts > 1 && (
                <span className="muted">
                  {t.attempt} {j.attempts}
                </span>
              )}
              {j.error && (
                <span className="error" role="alert">
                  {j.error}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
