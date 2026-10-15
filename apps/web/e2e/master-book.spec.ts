import { test, expect } from "@playwright/test";

test("Studio requires preview, story and face approvals in the browser", async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  const image = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="#edf4fa"/><circle cx="200" cy="180" r="85" fill="#e9c9a8"/><text x="200" y="330" text-anchor="middle" font-size="24" fill="#172A3A">Story R Us</text></svg>')}`;
  const p = { id: "master-browser", status: "EBOOK_READY", style: "cartoon", language: "pt-BR",
    child_name: "Lia", child_age: 4, story_text: null as string | null, ebook_url: null, video_url: null,
    created_at: "2026-10-15", book_profile: { version: 1, stage: "preview_ready", title: "Lia e as estrelas",
      gender: "f", languages: ["pt-BR"], current_page: 0, costume: "Macacão azul", trait: "Curiosidade",
      interest: "Estrelas", stories: undefined as Record<string, string> | undefined } };
  const calls: string[] = [];
  let character: string | null = null;
  const versions: object[] = [];
  await page.addInitScript(() => { localStorage.setItem("lang", "pt"); localStorage.setItem("storyrus_token", "browser-test-session"); });
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (value: unknown, status = 200) => route.fulfill({ status, json: value });
    if (path.endsWith("/auth/me")) return json({ id: "user", email: "test@example.com", is_guest: false,
      email_verified: true, full_name: "Ana", phone: "11999999999", street: "Rua", number: "1", city: "São Paulo", state: "SP", country: "BR", credits: 10 });
    if (path.endsWith("/credits")) return json({ credits: 10 });
    if (path.endsWith("/jobs")) return json([]);
    if (path.endsWith("/assets")) return json({ character_url: character, page_images: [], extra_characters: [],
      realistic_url: null, ebook_url: null, video_url: null, narrated_video_url: null, page_versions: versions,
      previews: ["01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"].map((role) => ({ role, language: "pt-BR", filename: `${role}.png`, url: image })) });
    if (route.request().method() === "GET" && path.endsWith("/master-browser")) return json(p);
    if (route.request().method() === "POST") {
      calls.push(path);
      if (path.endsWith("/preview/approve")) { p.book_profile.stage = "preview_approved"; return json(p); }
      if (path.endsWith("/story/approve")) { p.book_profile.stage = "story_approved"; return json(p); }
      if (path.endsWith("/avatar/approve")) { p.book_profile.stage = "avatar_approved"; return json(p); }
      let type = "EBOOK";
      if (path.endsWith("/story")) {
        type = "STORY"; p.book_profile.stage = "story_ready";
        p.story_text = "Título: Lia e as estrelas\nPágina 1:\nLia olhou o céu.\nUma estrela sorriu.";
        p.book_profile.stories = { "pt-BR": p.story_text };
      } else if (path.endsWith("/avatar")) {
        type = "AVATAR"; p.book_profile.stage = "avatar_ready"; character = image;
      } else if (path.endsWith("/pages/next")) {
        p.book_profile.stage = "page_ready"; p.book_profile.current_page = 1;
        versions.push(...["sem_texto", "com_texto"].map((role) => ({ role, page: 1, language: "pt-BR", url: image, filename: `${role}.png` })));
      }
      return json({ job_id: `job-${calls.length}`, status: "PENDING", type, estimated_cost_credits: 0 }, 202);
    }
    return json({ detail: "Unexpected test endpoint" }, 404);
  });
  await page.goto("/app?project=master-browser", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("Aprovo a prévia?", { exact: true })).toBeVisible({ timeout: 20_000 });
  expect(calls).toHaveLength(0);
  await page.screenshot({ path: testInfo.outputPath("studio-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("studio-mobile.png"), fullPage: true });
  await page.getByRole("button", { name: "Sim, aprovo", exact: true }).click();
  await expect(page.getByText("Aprovo a história?", { exact: true })).toBeVisible();
  expect(calls.some((call) => call.endsWith("/avatar"))).toBe(false);
  await page.getByRole("button", { name: "Sim, aprovo", exact: true }).click();
  await expect(page.getByText("Este é o rosto?", { exact: true })).toBeVisible();
  expect(calls.some((call) => call.endsWith("/pages/next"))).toBe(false);
  await page.getByRole("button", { name: "Sim, aprovo", exact: true }).click();
  await expect(page.getByText("Próxima?", { exact: true })).toBeVisible();
  await expect(page.getByText("Página 1 · PT-BR · Sem texto", { exact: true })).toBeVisible();
  await expect(page.getByText("Página 1 · PT-BR · Com texto", { exact: true })).toBeVisible();
});
