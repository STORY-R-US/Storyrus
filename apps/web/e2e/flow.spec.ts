import { expect, test, type Page } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Fontes externas não devem bloquear a navegação nos testes de fluxo.
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
  await page.route("**/health", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }),
  }));
});

// Estado em memória que imita o backend; injetado via page.route (sem rede real).
type Job = {
  id: string;
  project_id: string;
  type: string;
  status: string;
  cost_credits: number;
  attempts: number;
  error: string | null;
  polls: number;
  result?: { payload?: { preview_chain?: boolean; brief?: string } };
};

function makeState() {
  return {
    credits: 10,
    project: null as any,
    jobs: [] as Job[],
    seq: 0,
    email: "e2e@storyrus.app",
    isGuest: false,
    emailVerified: true,
    fullName: "E2E User",
    phone: "11988887777",
    postalCode: "01310100",
    street: "Av Paulista",
    number: "1000",
    complement: "",
    district: "Bela Vista",
    city: "Sao Paulo",
    stateUf: "SP",
    country: "BR",
    termsAcceptedAt: "2026-01-01T00:00:00Z" as string | null,
    adultConfirmedAt: "2026-01-01T00:00:00Z" as string | null,
    pendingVerifyToken: null as string | null,
  };
}

async function mockApi(page: Page, state: ReturnType<typeof makeState>) {
  const json = (route: any, body: unknown, status = 200) =>
    route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  const id = () => `id-${++state.seq}`;

  // E2E assume PT/BR (labels e ViaCEP); sem isso o IP do runner cai em EN/US.
  await page.addInitScript(() => {
    try {
      localStorage.setItem("lang", "pt");
    } catch {
      /* ignore */
    }
  });
  await page.route(/https?:\/\/ipapi\.co\/country\/?/, (r) =>
    r.fulfill({ status: 200, contentType: "text/plain", body: "BR" }),
  );

  await page.route(/https?:\/\/viacep\.com\.br\/ws\//, (r) =>
    json(r, {
      cep: "01310-100",
      logradouro: "Avenida Paulista",
      bairro: "Bela Vista",
      localidade: "São Paulo",
      uf: "SP",
    }),
  );

  await page.route("**/v1/auth/guest", (r) => json(r, { access_token: "e2e-token" }, 201));
  await page.route("**/v1/auth/signup", async (r) => {
    let body: Record<string, string> = {};
    try {
      body = (r.request().postDataJSON() as Record<string, string>) || {};
    } catch {
      /* ignore */
    }
    state.isGuest = false;
    state.emailVerified = false;
    state.email = body.email || state.email;
    state.fullName = body.full_name || state.fullName;
    state.phone = body.phone || state.phone;
    state.postalCode = body.postal_code || state.postalCode;
    state.street = body.street || state.street;
    state.number = body.number || state.number;
    state.district = body.district || state.district;
    state.city = body.city || state.city;
    state.stateUf = body.state || state.stateUf;
    // ≥20 chars (mesmo mínimo do schema da API) para o mock e o backend real.
    state.pendingVerifyToken = "e2e-verify-token-ok!!";
    return json(
      r,
      {
        ok: true,
        message: "Cadastro recebido. Confirme seu e-mail pelo link que enviamos.",
        verify_token: state.pendingVerifyToken,
      },
      201,
    );
  });
  await page.route("**/v1/auth/verify-email", async (r) => {
    let token = "";
    try {
      token = String((r.request().postDataJSON() as { token?: string })?.token || "");
    } catch {
      /* ignore */
    }
    if (!token) {
      return json(r, { detail: "Link invalido ou expirado" }, 400);
    }
    // Aceita o token do mock de signup (ou qualquer token do fluxo e2e).
    if (state.pendingVerifyToken && token !== state.pendingVerifyToken) {
      return json(r, { detail: "Link invalido ou expirado" }, 400);
    }
    state.emailVerified = true;
    state.pendingVerifyToken = null;
    return json(r, { access_token: "e2e-token" });
  });
  await page.route("**/v1/auth/login", (r) => {
    if (!state.emailVerified) {
      return json(r, { detail: "Confirme seu e-mail antes de entrar" }, 403);
    }
    state.isGuest = false;
    return json(r, { access_token: "e2e-token" });
  });
  await page.route("**/v1/auth/refresh", (r) => json(r, { access_token: "e2e-token-refreshed" }));
  await page.route("**/v1/auth/resume", (r) => json(r, { access_token: "e2e-token-resumed" }));
  await page.route("**/v1/auth/me", (r) =>
    json(r, {
      id: "e2e-user",
      email: state.email,
      credits: state.credits,
      created_at: "now",
      is_guest: state.isGuest,
      email_verified: state.emailVerified,
      full_name: state.fullName,
      phone: state.phone,
      postal_code: state.postalCode,
      street: state.street,
      number: state.number,
      complement: state.complement,
      district: state.district,
      city: state.city,
      state: state.stateUf,
      country: state.country,
      terms_accepted_at: state.termsAcceptedAt,
      adult_confirmed_at: state.adultConfirmedAt,
    }),
  );
  await page.route("**/v1/auth/me", async (r) => {
    if (r.request().method() !== "PATCH") return r.fallback();
    let body: Record<string, string | boolean | null> = {};
    try {
      body = (r.request().postDataJSON() as Record<string, string | boolean | null>) || {};
    } catch {
      /* ignore */
    }
    if (body.full_name) state.fullName = String(body.full_name);
    if (body.phone) state.phone = String(body.phone);
    if (body.postal_code) state.postalCode = String(body.postal_code);
    if (body.street) state.street = String(body.street);
    if (body.number) state.number = String(body.number);
    if (body.city) state.city = String(body.city);
    if (body.state) state.stateUf = String(body.state);
    if (body.country) state.country = String(body.country);
    if (body.accept_terms) state.termsAcceptedAt = "2026-01-02T00:00:00Z";
    if (body.confirm_adult) state.adultConfirmedAt = "2026-01-02T00:00:00Z";
    return json(r, {
      id: "e2e-user",
      email: state.email,
      credits: state.credits,
      created_at: "now",
      is_guest: state.isGuest,
      email_verified: state.emailVerified,
      full_name: state.fullName,
      phone: state.phone,
      postal_code: state.postalCode,
      street: state.street,
      number: state.number,
      complement: state.complement,
      district: state.district,
      city: state.city,
      state: state.stateUf,
      country: state.country,
      terms_accepted_at: state.termsAcceptedAt,
      adult_confirmed_at: state.adultConfirmedAt,
    });
  });
  await page.route("**/v1/credits", (r) => json(r, { credits: state.credits }));
  await page.route("**/v1/voices", (r) => json(r, { items: [], custom_voice_available: false }));

  await page.route("**/v1/projects", (r) => {
    if (r.request().method() !== "POST") return r.continue();
    state.project = {
      id: id(),
      status: "CREATED",
      style: "cgi_3d",
      story_text: null,
      ebook_url: null,
      video_url: null,
      character_approved_at: null,
      created_at: "now",
    };
    state.jobs = [];
    return json(r, state.project, 201);
  });

  await page.route(/\/v1\/projects\/[^/]+\/jobs$/, (r) => {
    for (const j of state.jobs) {
      if (j.status === "DONE") continue;
      j.polls += 1;
      if (j.polls === 1) j.status = "RUNNING";
      else if (j.polls >= 2) {
        j.status = "DONE";
        if (j.type === "STORY") {
          state.project.story_text = "Pagina 1: ola.\nPagina 2: fim.";
          state.project.status = "STORY_READY";
        }
        if (j.type === "AVATAR") {
          state.project.status = "AVATAR_READY";
        }
      }
    }
    return json(r, state.jobs);
  });

  await page.route(/\/v1\/projects\/[^/]+\/photo$/, (r) =>
    json(r, { asset_id: id(), storage_key: "k", upload_url: "", expires_in: 0 }, 201),
  );

  await page.route(/\/v1\/projects\/[^/]+\/assets$/, (r) => {
    const avatarDone = state.jobs.some((j) => j.type === "AVATAR" && j.status === "DONE");
    return json(r, {
      character_url: avatarDone ? "https://cdn.test/character.png" : null,
      realistic_url: null,
      extra_characters: [],
      page_images: [],
      ebook_url: state.project?.ebook_url ?? null,
      video_url: null,
      narrated_video_url: null,
    });
  });

  await page.route(/\/v1\/projects\/[^/]+\/(avatar|story|ebook|video|narrated-video)$/, (r) => {
    const last = r.request().url().split("/").pop()!.split("?")[0];
    const type = last === "narrated-video" ? "NARRATED_VIDEO" : last.toUpperCase();
    const job: Job = {
      id: id(),
      project_id: state.project.id,
      type,
      status: "PENDING",
      cost_credits: 0,
      attempts: 1,
      error: null,
      polls: 0,
    };
    state.jobs.push(job);
    return json(r, { job_id: job.id, status: "PENDING", type, estimated_cost_credits: 0 }, 202);
  });

  // Cadeia automática do Studio (avatar → história → ebook → vídeo).
  await page.route(/\/v1\/projects\/[^/]+\/preview$/, (r) => {
    if (r.request().method() !== "POST") return r.continue();
    const active = state.jobs.some(
      (j) =>
        (j.status === "PENDING" || j.status === "RUNNING") &&
        Boolean(j.result?.payload?.preview_chain),
    );
    if (active) return json(r, { detail: "Já existe uma prévia em andamento para este projeto" }, 409);
    let brief: string | undefined;
    try {
      brief = String((r.request().postDataJSON() as { brief?: string })?.brief || "").trim() || undefined;
    } catch {
      /* body vazio */
    }
    const job: Job = {
      id: id(),
      project_id: state.project.id,
      type: "AVATAR",
      status: "PENDING",
      cost_credits: 0,
      attempts: 1,
      error: null,
      polls: 0,
      result: { payload: { preview_chain: true, ...(brief ? { brief } : {}) } },
    };
    state.jobs.push(job);
    return json(r, { job_id: job.id, status: "PENDING", type: "AVATAR", estimated_cost_credits: 0 }, 202);
  });

  await page.route(/\/v1\/projects\/[^/]+$/, (r) => {
    if (r.request().method() === "POST") return r.continue();
    return json(r, state.project);
  });
}

async function fillSignupForm(page: Page) {
  await page.getByTestId("auth-full-name").fill("E2E User");
  await page.getByTestId("auth-phone").fill("11988887777");
  await page.getByTestId("auth-postal-code").fill("01310100");
  await expect(page.getByTestId("auth-street")).toHaveValue(/Paulista/i);
  await expect(page.getByTestId("auth-district")).toHaveValue("Bela Vista");
  await expect(page.getByTestId("auth-city")).toHaveValue("São Paulo");
  await expect(page.getByTestId("auth-state")).toHaveValue("SP");
  await page.getByTestId("auth-number").fill("1000");
  await page.getByTestId("auth-confirm-adult").check();
  await page.getByTestId("auth-accept-terms").check();
}

async function loginViaEntrar(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("storyrus_token", "e2e-token");
  });
  await page.goto("/app");
}

test("perfil aguarda o despertar sem erro nem envio duplicado", async ({ page }, testInfo) => {
  const state = makeState();
  state.street = "";
  state.city = "";
  state.fullName = "";
  state.phone = "";
  state.termsAcceptedAt = null;
  state.adultConfirmedAt = null;
  await mockApi(page, state);
  await page.addInitScript(() => {
    localStorage.setItem("storyrus_token", "e2e-token");
  });
  let ready = false;
  let saves = 0;
  await page.route("**/health", (route) => route.fulfill({
    status: ready ? 200 : 503,
    contentType: ready ? "application/json" : "text/html",
    body: ready ? JSON.stringify({ status: "ok" }) : "<html>Waking up</html>",
  }));
  await page.route("**/v1/auth/me", async (route) => {
    if (route.request().method() !== "PATCH") return route.fallback();
    saves += 1;
    state.termsAcceptedAt = "2026-01-02T00:00:00Z";
    state.adultConfirmedAt = "2026-01-02T00:00:00Z";
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "e2e-user",
        email: state.email,
        is_guest: false,
        email_verified: true,
        full_name: "E2E User",
        phone: "11988887777",
        street: "Avenida Paulista",
        city: "São Paulo",
        country: "BR",
        terms_accepted_at: state.termsAcceptedAt,
        adult_confirmed_at: state.adultConfirmedAt,
      }),
    });
  });
  await page.goto("/cadastro", { waitUntil: "domcontentloaded" });
  await fillSignupForm(page);
  await page.getByTestId("auth-submit").click();
  await expect(page.getByRole("status")).toContainText("preparando sua conexão");
  await expect(page.getByTestId("auth-submit")).toBeDisabled();
  await expect(page.getByTestId("auth-error")).toHaveCount(0);
  expect(saves).toBe(0);
  await page.screenshot({ path: testInfo.outputPath("cold-start.png") });
  ready = true;
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("status")).toHaveCount(0);
  expect(saves).toBe(1);
});

test("landing leva ao cadastro", async ({ page }) => {
  const state = makeState();
  await mockApi(page, state);
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const heroCta = page.getByTestId("landing-hero-cta");
  await expect(heroCta).toBeVisible();
  await expect(heroCta).toHaveAttribute("href", "/cadastro");
  await expect(page.getByTestId("landing-header-login")).toHaveAttribute("href", "/entrar");
  await heroCta.click();
  await expect(page).toHaveURL(/\/cadastro/);
  await expect(page.getByTestId("auth-page")).toBeVisible();
  await expect(page.locator(".cl-rootBox, [data-testid='auth-clerk-missing']").first()).toBeVisible();
});

test("avisos ficam nos campos e titulo opcional permite criar a previa", async ({ page }) => {
  const state = makeState();
  await mockApi(page, state);
  await loginViaEntrar(page);

  await page.getByTestId("studio-generate-book").click();
  await expect(page.getByTestId("studio-error-name")).toHaveText("Preencha o nome.");
  await expect(page.getByTestId("studio-error-age")).toHaveText("Preencha a idade.");
  await expect(page.getByTestId("studio-error-title")).toHaveCount(0);
  await expect(page.getByLabel("Título do livro")).toHaveValue("");
  await expect(page.getByText("Se deixar em branco, sugerimos um título.")).toBeVisible();
  await expect(page.getByTestId("studio-error-theme")).toHaveText("Preencha o tema.");
  await expect(page.getByTestId("studio-error-photo")).toBeVisible();
  await expect(page.getByTestId("studio-error-consent")).toBeVisible();
  await expect(page.getByText("Preencha nome, título, tema e idade antes de continuar.")).toHaveCount(0);
  await expect(page.getByTestId("studio-order-sent")).toHaveCount(0);

  await page.getByLabel("Nome do protagonista").fill("Lila");
  await page.getByRole("spinbutton", { name: "Idade" }).fill("5");
  await page.getByLabel("Insira o tema desejado").fill("Aventura no espaço");
  await page.getByTestId("studio-photo-input").setInputFiles({
    name: "foto.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("x"),
  });
  await page.getByTestId("studio-media-consent").check();
  await expect(page.getByTestId("studio-error-name")).toHaveCount(0);
  await page.getByTestId("studio-generate-book").click();
  await expect(page.getByTestId("studio-order-sent")).toBeVisible();
  await expect(page.getByTestId("studio-preview-building")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Projeto criado" })).toBeVisible();
});

test("estúdio → projeto → foto gera personagem → história", async ({ page }) => {
  const state = makeState();
  await mockApi(page, state);
  await loginViaEntrar(page);

  await expect(page.getByLabel("Nome do protagonista")).toBeVisible();
  await page.getByLabel("Nome do protagonista").fill("Lila");
  await page.getByRole("spinbutton", { name: "Idade" }).fill("5");
  await page.getByLabel("Título do livro").fill("Lila e as estrelas");
  await page.getByLabel("Insira o tema desejado").fill("Aventura no espaço");
  await page.getByRole("button", { name: "Feminino" }).click();
  await page.getByTestId("studio-photo-input").setInputFiles({
    name: "foto.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("x"),
  });
  await page.getByTestId("studio-media-consent").check();
  await page.getByTestId("studio-generate-book").click();
  await expect(page.getByTestId("studio-order-sent")).toBeVisible();
});

test("após gerar o livro mostra Projeto criado sem botões de crédito", async ({ page }) => {
  const state = makeState();
  await mockApi(page, state);
  await loginViaEntrar(page);

  await page.getByLabel("Nome do protagonista").fill("Lila");
  await page.getByRole("spinbutton", { name: "Idade" }).fill("5");
  await page.getByLabel("Título do livro").fill("Lila e as estrelas");
  await page.getByLabel("Insira o tema desejado").fill("Aventura no espaço");
  await page.getByRole("button", { name: "Feminino" }).click();
  await page.getByTestId("studio-photo-input").setInputFiles({
    name: "foto.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("x"),
  });
  await page.getByTestId("studio-media-consent").check();
  await page.getByTestId("studio-generate-book").click();
  await expect(page.getByTestId("studio-order-sent")).toBeVisible();
  await expect(page.getByTestId("studio-preview-building")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Projeto criado" })).toBeVisible();
  await expect(page.getByTestId("studio-preview-eta")).toContainText("Previsão: cerca de");
  await expect(page.getByTestId("studio-preview-must-move")).toContainText("Não fica parado");
  await expect(page.getByText("Fique nesta tela. Ela atualiza sozinha.")).toBeVisible();
  await expect(page.getByText(/título mudar para Prévia pronta/)).toBeVisible();
  await expect(page.getByTestId("studio-preview-step-AVATAR")).toBeVisible();
  await expect(page.getByTestId("studio-generate-preview")).toHaveCount(0);
});

test("exemplo pronto mostra Prévia pronta", async ({ page }) => {
  await page.addInitScript(() => {
    try {
      localStorage.setItem("lang", "pt");
    } catch {
      /* ignore */
    }
  });
  await page.goto("/app?exemplo=dinosaurs");
  await expect(page.getByRole("heading", { name: "Prévia pronta" })).toBeVisible();
  await expect(page.getByTestId("studio-preview-building")).toHaveCount(0);
  await expect(page.getByTestId("studio-story-result")).toBeVisible();
  await expect(page.getByTestId("studio-preview-trio")).toBeVisible();
  await expect(page).toHaveTitle("Story R Us - Prévia pronta");
});

test("path inexistente mostra 404", async ({ page }) => {
  await page.goto("/pagina-que-nao-existe");
  await expect(page.getByTestId("not-found-title")).toBeVisible();
  await expect(page.getByTestId("not-found-home")).toBeVisible();
});

test("landing sem preço e EN atualiza lang", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("landing-personalize").first()).toBeVisible();
  await expect(page.locator("body")).not.toContainText("US$ 39,99");
  await expect(page.locator("body")).not.toContainText("$39.99");
  await expect(page.locator("body")).not.toContainText("ECONOMIZE 33%");
  await page.getByTestId("landing-lang-en").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByTestId("landing-lang-es").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
});

test("menu mobile abre abaixo da logo", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("landing-header-login")).toBeVisible();
  await expect(page.getByTestId("landing-header-cta")).toBeVisible();
  const menuBtn = page.getByTestId("landing-menu");
  await expect(menuBtn).toBeInViewport();
  await menuBtn.click();
  await expect(menuBtn).toHaveAttribute("aria-expanded", "true");
  const logo = page.getByTestId("landing-brand").locator("img");
  const panel = page.getByTestId("landing-site-menu");
  await expect(panel).toBeVisible();
  const logoBox = await logo.boundingBox();
  const panelBox = await panel.boundingBox();
  expect(logoBox).toBeTruthy();
  expect(panelBox).toBeTruthy();
  expect(panelBox!.y).toBeGreaterThanOrEqual((logoBox!.y + logoBox!.height) - 8);
});
