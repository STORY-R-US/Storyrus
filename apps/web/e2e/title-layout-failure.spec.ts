import { TEST_SESSION_TOKEN } from "./session";
import { test, expect } from "./fixtures";

test("A saved unsafe title layout explains the problem without automatically generating again", async ({ page }) => {
  const calls: string[] = [];
  const project = {
    id: "protected-title", status: "CREATED", style: "realistic", language: "pt-BR",
    child_name: "André", child_age: 30, created_at: "2026-11-11",
    story_text: null, ebook_url: null, video_url: null,
    purchase_flow: { stage: "preview_failed", preview_approved_at: null },
    book_profile: { version: 1, stage: "ficha_ready", gender: "m", title: "André no Computador",
      languages: ["pt-BR"], costume: "Camisa azul", characters: "",
      locales: { "pt-BR": { title: "André no Computador", left: "André aprende.", right: "Uma descoberta." } } },
  };
  await page.addInitScript((token) => {
    localStorage.setItem("lang", "pt");
    localStorage.setItem("storyrus_token", token);
  }, TEST_SESSION_TOKEN);
  await page.route("**/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (value: unknown, status = 200) => route.fulfill({ status, json: value });
    if (route.request().method() !== "GET") {
      calls.push(path);
      return json({ detail: "Generation is forbidden in this test" }, 422);
    }
    if (path.endsWith("/auth/me")) return json({ id: "user", email: "test@example.com", is_guest: false,
      email_verified: true, terms_accepted_at: "2026-10-30", adult_confirmed_at: "2026-10-30",
      full_name: "Ana", phone: "11999999999", street: "Rua", number: "1", city: "São Paulo", state: "SP", country: "BR", credits: 10 });
    if (path.endsWith("/credits")) return json({ credits: 10 });
    if (path.endsWith("/jobs")) return json([{ id: "saved-layout-failure", project_id: project.id,
      type: "EBOOK", status: "FAILED", provider: "openai", attempts: 1, cost_credits: 0,
      created_at: "2026-11-11T20:00:00Z",
      error: "Etapa editorial cover:art: BOOK_LAYOUT_UNSAFE: face and blue knit cap",
      result: { payload: { cover_only: true }, last_provider_error: { outcome_unknown: false } } }]);
    if (path.endsWith("/assets")) return json({ previews: [], photo_count: 1, character_url: null,
      realistic_url: null, page_images: [], page_versions: [], extra_characters: [], ebook_url: null,
      video_url: null, narrated_video_url: null });
    if (path.endsWith("/print-order")) return json({ id: "order", project_id: project.id, quantity: 1,
      book_size: "M", cover_type: "soft", payment_status: "unpaid", checkout_available: false, freight_options: [] });
    if (path.endsWith("/protected-title")) return json(project);
    return json({ detail: "Unexpected test endpoint" }, 404);
  });
  await page.goto("/app?project=protected-title", { waitUntil: "domcontentloaded" });
  const message = page.getByText(/Não foi possível encaixar o texto sem cobrir rosto, cabelo, gorro/).first();
  await expect(message).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("face and blue knit cap", { exact: true })).toHaveCount(0);
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(message).toBeVisible();
  expect(calls).toEqual([]);
});
