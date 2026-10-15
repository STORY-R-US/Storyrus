import type { Dispatch, SetStateAction } from "react";
import { api } from "../api";
import type { Project } from "../types";

type Args = {
  project: Project | null;
  isDemo: boolean;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setProject: Dispatch<SetStateAction<Project | null>>;
};

/** Character/book approval and print request actions. */
export function useStudioApprovals({
  project,
  isDemo,
  setBusy,
  setError,
  setProject,
}: Args) {
  async function approveCharacter() {
    if (!project || isDemo) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.approveCharacter(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approveBook() {
    if (!project || isDemo) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.approveBook(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function requestPrint() {
    if (!project || isDemo) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.requestPrint(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const characterApproved = !!project?.character_approved_at;
  const bookApproved = !!project?.book_approved_at;
  const printRequested = !!project?.print_requested_at;

  return {
    approveCharacter,
    approveBook,
    requestPrint,
    characterApproved,
    bookApproved,
    printRequested,
  };
}
