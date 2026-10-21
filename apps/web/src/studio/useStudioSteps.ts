import type { Dispatch, SetStateAction } from "react";
import { api } from "../api";
import type { Job, Project } from "../types";

export type StudioStep = "avatar" | "story" | "ebook" | "video" | "narrated-video";

type Args = {
  project: Project | null;
  isDemo: boolean;
  selectedVoiceId: string;
  getStoryBrief?: () => string;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setJobs: Dispatch<SetStateAction<Job[]>>;
};

/** Starts generation steps (avatar/story/ebook/video/narrated-video). */
export function useStudioSteps({
  project,
  isDemo,
  selectedVoiceId,
  getStoryBrief,
  setBusy,
  setError,
  setJobs,
}: Args) {
  async function runStep(step: StudioStep) {
    if (!project || isDemo) return;
    setBusy(true);
    setError(null);
    try {
      let body: Record<string, unknown> = {};
      if (step === "story" && getStoryBrief) {
        const brief = getStoryBrief().trim();
        if (brief) body = { brief: brief.slice(0, 2000) };
      }
      if (step === "video") body = { duration_s: 5 };
      if (step === "narrated-video" && selectedVoiceId) body = { voice_id: selectedVoiceId };
      await api.startStep(project.id, step, body);
      const js = await api.listJobs(project.id);
      setJobs(js);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return { runStep };
}
