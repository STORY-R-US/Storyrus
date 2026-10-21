import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setToken } from "./api";
import { ProgressList, Studio } from "./Studio";
import type { Job } from "./types";
import { LANG_STORAGE_KEY } from "./i18n/lang";
import { state } from "./test/server";

beforeEach(() => {
  state.isGuest = false;
  state.email = "ana@email.com";
  state.credits = 10;
  setToken("test-token");
});

afterEach(() => {
  localStorage.removeItem(LANG_STORAGE_KEY);
  window.history.replaceState({}, "", "/");
});

function ebookJob(): Job {
  return {
    id: "job-1",
    project_id: "p1",
    type: "EBOOK",
    status: "RUNNING",
    provider: null,
    cost_credits: 1,
    attempts: 1,
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    result: { progress: { stage: "pages", done: 4, total: 11 } },
  };
}

describe("Studio i18n", () => {
  it("carrega inglês a partir do lang da landing (localStorage)", async () => {
    localStorage.setItem(LANG_STORAGE_KEY, "en");
    render(<Studio />);

    expect(await screen.findByRole("heading", { name: /create your story/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/protagonist's name/i)).toBeInTheDocument();
    expect(screen.queryByText(/credits:/i)).not.toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });

  it("alterna PT → ES e persiste em localStorage", async () => {
    localStorage.setItem(LANG_STORAGE_KEY, "pt");
    const user = userEvent.setup();
    render(<Studio />);

    expect(await screen.findByRole("heading", { name: /crie a sua história/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^ES$/i }));

    expect(await screen.findByRole("heading", { name: /crea tu historia/i })).toBeInTheDocument();
    expect(localStorage.getItem(LANG_STORAGE_KEY)).toBe("es");
    expect(document.documentElement.lang).toBe("es");
  });

  it("ProgressList traduz Ilustrando conforme o lang salvo", () => {
    localStorage.setItem(LANG_STORAGE_KEY, "en");
    render(<ProgressList jobs={[ebookJob()]} />);
    expect(screen.getByText("Illustrating 4/11")).toBeInTheDocument();
  });
});
