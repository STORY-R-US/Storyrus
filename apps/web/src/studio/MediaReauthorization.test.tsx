import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "../api";
import { MediaReauthorization } from "./MediaReauthorization";

afterEach(() => vi.restoreAllMocks());

it("requires a fresh explicit choice before authorizing existing photos", async () => {
  const authorize = vi.spyOn(api, "authorizeBookMedia").mockResolvedValue(undefined);
  const complete = vi.fn();
  render(<MediaReauthorization projectId="existing" lang="pt" onAuthorized={complete} />);
  const button = screen.getByRole("button", { name: "Confirmar autorização" });
  expect(button).toBeDisabled();
  expect(authorize).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(button);
  await waitFor(() => expect(authorize).toHaveBeenCalledWith("existing", true));
  expect(complete).toHaveBeenCalledOnce();
});

it("keeps the authorization notice when saving fails", async () => {
  vi.spyOn(api, "authorizeBookMedia").mockRejectedValue(new Error("503: Tente novamente"));
  const complete = vi.fn();
  render(<MediaReauthorization projectId="existing" lang="pt" onAuthorized={complete} />);
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: "Confirmar autorização" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Tente novamente");
  expect(complete).not.toHaveBeenCalled();
});
