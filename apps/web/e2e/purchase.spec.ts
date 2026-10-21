import { expect, test } from "@playwright/test";

for (const master of [false, true]) {
  test(`prévia ${master ? "mestre" : "anterior"} → cotação → meus pedidos`, async ({
    page,
  }) => {
    const project = {
      book_profile: master
        ? {
            version: 1,
            stage: "preview_ready",
            title: "Lila e as estrelas",
            gender: "f",
            languages: ["pt-BR"],
            current_page: 0,
          }
        : null,
      id: "purchase-test",
      status: "EBOOK_READY",
      style: "realistic",
      child_name: "Lila",
      child_age: 5,
      theme: "espaco",
      book_size: "M",
      cover_type: "soft",
      story_text:
        "Título: Lila e as estrelas\n\nPágina 1: A estrela brilhou e Lila sorriu.",
      ebook_url: "preview.pdf",
      video_url: null,
      created_at: "2026-10-15T12:00:00Z",
      book_approved_at: null,
      purchase_flow: {
        title: "Lila e as estrelas",
        theme_description: "Amizade no espaço",
        stage: "preview_ready",
        preview_ready_at: "2026-10-15",
        preview_approved_at: null as string | null,
        quoted_at: null as string | null,
      },
    };
    const order = {
      id: "o1",
      project_id: project.id,
      code: "SR-1234",
      book_size: "M",
      cover_type: "soft",
      quantity: 1,
      status: "awaiting_payment",
      book_price_cents: 17700,
      freight_options: [],
      freight_service_id: null,
      freight_price_cents: null,
      payment_status: "unpaid",
      amount_cents: null,
      checkout_available: false,
      checkout_url: null,
      recipient_name: "Ana Souza",
      postal_code: "01310100",
      street: "Av Paulista",
      number: "1000",
      complement: "",
      district: "Bela Vista",
      city: "São Paulo",
      state: "SP",
    };
    await page.addInitScript(() => {
      localStorage.setItem("lang", "pt");
      localStorage.setItem("theme", "light");
      localStorage.setItem("storyrus_token", "e2e-purchase-token");
    });
    await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (r) =>
      r.abort(),
    );
    await page.route("**/health", (r) => r.fulfill({ json: { status: "ok" } }));
    await page.route("https://ipapi.co/**", (r) => r.fulfill({ body: "BR" }));
    await page.route("**/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const json = (body: unknown) => route.fulfill({ json: body });
      if (path.endsWith("/auth/me"))
        return json({
          email: "ana@example.com",
          full_name: "Ana Souza",
          is_guest: false,
          email_verified: true,
          is_owner: false,
        });
      if (path.endsWith("/preview/approve")) {
        project.purchase_flow.preview_approved_at = "2026-10-15";
        project.purchase_flow.stage = "awaiting_payment";
        if (project.book_profile)
          project.book_profile.stage = "preview_approved";
        return json(project);
      }
      if (path.endsWith("/quotation")) {
        project.purchase_flow.quoted_at = "2026-10-15";
        return json(project);
      }
      if (path.endsWith("/print-order")) return json(order);
      if (path.endsWith("/assets"))
        return json({
          previews: master
            ? ["01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"].map((role) => ({
                role,
                language: "pt-BR",
                filename: role + ".jpg",
                url: "/exemplos/ebook-1.jpg",
              }))
            : [],
          character_url: null,
          realistic_url: null,
          extra_characters: [],
          page_images: ["/exemplos/ebook-2.jpg"],
          cover_url: "/exemplos/ebook-1.jpg",
          in_hand_url: "/exemplos/livro-1.jpg",
          ebook_url: "/preview.pdf",
          video_url: null,
          narrated_video_url: null,
        });
      if (path.endsWith("/jobs")) return json([]);
      if (path === "/v1/projects") return json([project]);
      if (path === `/v1/projects/${project.id}`) return json(project);
      return route.fulfill({
        status: 404,
        json: { detail: "Unexpected test route" },
      });
    });
    await page.goto(`/app?projeto=${project.id}`);
    await expect(
      page.getByRole("button", { name: "Gostei, continuar com meu livro" }),
    ).toBeVisible();
    await page
      .getByTestId("purchase-flow")
      .screenshot({
        path: `test-results/purchase-${master ? "master" : "legacy"}-preview.png`,
      });
    await page
      .getByRole("button", { name: "Gostei, continuar com meu livro" })
      .click();
    await expect(
      page.getByText("Pedido em cotação", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Continuar para pagamento" }),
    ).toHaveCount(0);
    await page
      .getByRole("button", { name: "Salvar cotação e acompanhar" })
      .click();
    await expect(page.getByText(/Cotação salva/)).toBeVisible();
    await page.getByTestId("purchase-flow").screenshot({
      path: `test-results/purchase-${master ? "master" : "legacy"}-quotation.png`,
      style: ".studio-app > header { visibility: hidden !important; }",
    });
    await page.reload();
    await expect(
      page.getByText("Pedido em cotação", { exact: true }),
    ).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByTestId("purchase-flow").screenshot({
      path: `test-results/purchase-${master ? "master" : "legacy"}-mobile.png`,
      style: ".studio-app > header { visibility: hidden !important; }",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page.goto("/meus-pedidos");
    await expect(
      page.getByRole("heading", { name: "Lila e as estrelas" }),
    ).toBeVisible();
    await expect(
      page.getByText("Pedido em cotação", { exact: true }),
    ).toBeVisible();
  });
}
