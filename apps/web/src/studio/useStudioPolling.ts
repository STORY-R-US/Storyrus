import { useEffect, useRef, type Dispatch, type SetStateAction } from "react";
import { api } from "../api";
import type { Job, Project } from "../types";
import { mergeStudioAssets, type StudioAssets } from "./assets";

type Args = {
  project: Project | null;
  jobs: Job[];
  setProject: Dispatch<SetStateAction<Project | null>>;
  setJobs: Dispatch<SetStateAction<Job[]>>;
  setAssets: Dispatch<SetStateAction<StudioAssets | null>>;
  isDemo: boolean;
  /** Continua buscando jobs enquanto a prévia ainda não está pronta. */
  keepWatching?: boolean;
};

/** Polls project/jobs/assets while an active job exists (interval 2500ms). */
export function useStudioPolling({
  project,
  jobs,
  setProject,
  setJobs,
  setAssets,
  isDemo,
  keepWatching = false,
}: Args) {
  const pollRef = useRef<number | null>(null);
  const pollInFlightRef = useRef(false);
  const hasActiveJob = jobs.some((j) => j.status === "PENDING" || j.status === "RUNNING");
  const shouldPoll = hasActiveJob || keepWatching;

  useEffect(() => {
    if (!project || isDemo) return;
    const projectId = project.id;

    const tick = async () => {
      if (pollInFlightRef.current) return;
      pollInFlightRef.current = true;
      try {
        const js = await api.listJobs(projectId);
        const p = await api.getProject(projectId);
        setProject(p);
        setJobs(js);
        const stillActive = js.some((j) => j.status === "PENDING" || j.status === "RUNNING");
        api
          .getAssets(projectId)
          .then((next) => {
            setAssets((prev) => (stillActive ? mergeStudioAssets(prev, next) : next));
          })
          .catch(() => {});
      } catch {
        /* ignore */
      } finally {
        pollInFlightRef.current = false;
      }
    };

    if (!shouldPoll) {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
      api.getAssets(projectId).then(setAssets).catch(() => {});
      return;
    }

    void tick();
    pollRef.current = window.setInterval(() => {
      void tick();
    }, 2500);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
    };
    // Deps match the former inline effect (project identity via project?.id).
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setters are stable; poll on project id + active job only
  }, [project?.id, shouldPoll, isDemo]);
}
