import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// --------------------------------------------------------------------------- //
// Estado em memória que imita o backend (suficiente para os testes de fluxo).
// --------------------------------------------------------------------------- //
type Job = {
  id: string;
  project_id: string;
  type: string;
  status: string;
  provider: string | null;
  cost_credits: number;
  attempts: number;
  error: string | null;
  created_at: string;
  result?: {
    progress?: { stage?: string; done?: number; total?: number };
    payload?: { preview_chain?: boolean; brief?: string; duration_s?: number };
  } | null;
  _polls: number;
};
type Project = {
  id: string;
  status: string;
  style: string | null;
  story_text: string | null;
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url?: string | null;
  cover_url?: string | null;
  in_hand_url?: string | null;
  page_image_url?: string | null;
  character_approved_at?: string | null;
  book_approved_at?: string | null;
  print_requested_at?: string | null;
  print_status?: string | null;
  created_at: string;
};

type OwnerUserMock = {
  id: string;
  email: string;
  credits: number;
  created_at: string;
  project_count: number;
  full_name: string;
  phone: string;
  email_verified: boolean;
  postal_code: string;
  street: string;
  number: string;
  complement: string;
  district: string;
  city: string;
  state: string;
  country: string;
  terms_accepted_at: string;
};

export const state = {
  credits: 0,
  isGuest: true,
  isOwner: false,
  email: "guest-test@storyrus.app",
  emailVerified: true,
  fullName: "Ana Souza",
  phone: "11999999999",
  postalCode: "01310100",
  street: "Av Paulista",
  number: "1000",
  complement: "Sala 1",
  district: "Bela Vista",
  city: "Sao Paulo",
  stateUf: "SP",
  country: "BR",
  pendingVerifyToken: null as string | null,
  pendingResetToken: null as string | null,
  projects: new Map<string, Project>(),
  jobs: new Map<string, Job[]>(),
  ownerUsers: seedOwnerUsers(),
  reset() {
    this.credits = 0;
    this.isGuest = true;
    this.isOwner = false;
    this.email = "guest-test@storyrus.app";
    this.emailVerified = true;
    this.fullName = "Ana Souza";
    this.phone = "11999999999";
    this.postalCode = "01310100";
    this.street = "Av Paulista";
    this.number = "1000";
    this.complement = "Sala 1";
    this.district = "Bela Vista";
    this.city = "Sao Paulo";
    this.stateUf = "SP";
    this.country = "BR";
    this.pendingVerifyToken = null;
    this.pendingResetToken = null;
    this.projects.clear();
    this.jobs.clear();
    this.ownerUsers = seedOwnerUsers();
  },
};

function seedOwnerUsers(): OwnerUserMock[] {
  return [
    {
      id: "u1",
      email: "ana@example.com",
      credits: 12,
      created_at: "2026-03-01T15:30:00.000Z",
      project_count: 3,
      full_name: "Ana Souza",
      phone: "11999999999",
      email_verified: true,
      postal_code: "01310-100",
      street: "Avenida Paulista",
      number: "1000",
      complement: "Sala 1",
      district: "Bela Vista",
      city: "Sao Paulo",
      state: "SP",
      country: "BR",
      terms_accepted_at: "2026-03-01T15:30:00.000Z",
    },
    {
      id: "u2",
      email: "bruno@example.com",
      credits: 5,
      created_at: "2026-02-10T12:00:00.000Z",
      project_count: 1,
      full_name: "Bruno Lima",
      phone: "21988887777",
      email_verified: false,
      postal_code: "22041-080",
      street: "Av Atlantica",
      number: "500",
      complement: "",
      district: "Copacabana",
      city: "Rio de Janeiro",
      state: "RJ",
      country: "BR",
      terms_accepted_at: "2026-02-10T12:00:00.000Z",
    },
  ];
}

let seq = 0;
const id = () => `id-${++seq}`;

function enqueuePreviewNext(project: Project, fromType: string, payload: Job["result"]) {
  const chain = Boolean(payload?.payload?.preview_chain);
  if (!chain) return;
  if (fromType === "EBOOK") {
    project.book_approved_at = new Date().toISOString();
    project.cover_url = `https://cdn.test/${project.id}/cover.png`;
    project.page_image_url = `https://cdn.test/${project.id}/page1.png`;
    project.in_hand_url = `https://cdn.test/${project.id}/in-hand.png`;
    return;
  }
  const nextType = fromType === "AVATAR" ? "STORY" : fromType === "STORY" ? "EBOOK" : null;
  if (!nextType) return;
  if (fromType === "AVATAR") project.character_approved_at = new Date().toISOString();
  const nextPayload: Job["result"] = {
    payload: {
      preview_chain: true,
      ...(payload?.payload?.brief && nextType === "STORY" ? { brief: payload.payload.brief } : {}),
    },
  };
  const job: Job = {
    id: id(),
    project_id: project.id,
    type: nextType,
    status: "PENDING",
    provider: null,
    cost_credits: 0,
    attempts: 1,
    error: null,
    created_at: new Date().toISOString(),
    result: nextPayload,
    _polls: 0,
  };
  state.jobs.get(project.id)?.push(job);
}

function advance(job: Job, project: Project) {
  job._polls += 1;
  if (job._polls === 1) job.status = "RUNNING";
  else if (job._polls >= 2) {
    job.status = "DONE";
    if (job.type === "STORY") {
      project.story_text = "Pagina 1: ola.\nPagina 2: fim.";
      project.status = "STORY_READY";
    }
    if (job.type === "AVATAR") {
      project.status = "AVATAR_READY";
      project.character_approved_at = null;
      project.book_approved_at = null;
    }
    if (job.type === "EBOOK") {
      project.ebook_url = `projects/${project.id}/ebook/x.pdf`;
      project.status = "EBOOK_READY";
      project.book_approved_at = null;
      project.print_requested_at = null;
      project.print_status = null;
    }
    if (job.type === "VIDEO") {
      project.video_url = `projects/${project.id}/video/x.mp4`;
      project.status = "VIDEO_READY";
    }
    if (job.type === "NARRATED_VIDEO") {
      project.narrated_video_url = `projects/${project.id}/narrated/x.mp4`;
      project.status = "VIDEO_READY";
    }
    enqueuePreviewNext(project, job.type, job.result);
  }
}

export const handlers = [
  http.get(/https?:\/\/viacep\.com\.br\/ws\/(\d{8})\/json\/?/, ({ request }) => {
    const cep = request.url.match(/ws\/(\d{8})/)?.[1] ?? "";
    if (cep === "00000000" || cep === "99999999") {
      return HttpResponse.json({ erro: true });
    }
    if (cep === "01310100") {
      return HttpResponse.json({
        cep: "01310-100",
        logradouro: "Avenida Paulista",
        complemento: "",
        bairro: "Bela Vista",
        localidade: "São Paulo",
        uf: "SP",
      });
    }
    return HttpResponse.json({
      cep: `${cep.slice(0, 5)}-${cep.slice(5)}`,
      logradouro: "Rua Teste",
      bairro: "Centro",
      localidade: "Sao Paulo",
      uf: "SP",
    });
  }),
  http.get(/https?:\/\/ipapi\.co\/country\/?/, () => {
    return new HttpResponse("BR", {
      status: 200,
      headers: { "Content-Type": "text/plain" },
    });
  }),
  http.get(/https?:\/\/api\.zippopotam\.us\/us\/(\d{5})\/?/, ({ request }) => {
    const zip = request.url.match(/\/us\/(\d{5})/)?.[1] ?? "";
    if (zip === "00000" || zip === "99999") {
      return new HttpResponse(null, { status: 404 });
    }
    if (zip === "90210") {
      return HttpResponse.json({
        "post code": "90210",
        country: "United States",
        "country abbreviation": "US",
        places: [
          {
            "place name": "Beverly Hills",
            longitude: "-118.4065",
            state: "California",
            "state abbreviation": "CA",
            latitude: "34.0901",
          },
        ],
      });
    }
    return HttpResponse.json({
      "post code": zip,
      country: "United States",
      "country abbreviation": "US",
      places: [
        {
          "place name": "Testville",
          state: "California",
          "state abbreviation": "CA",
        },
      ],
    });
  }),
  http.post("*/v1/auth/guest", async () => {
    if (state.credits === 0) state.credits = 10;
    state.isGuest = true;
    state.email = "guest-test@storyrus.app";
    return HttpResponse.json({ access_token: "test-token" }, { status: 201 });
  }),
  http.post("*/v1/auth/refresh", async () => {
    return HttpResponse.json({ access_token: "test-token-refreshed" });
  }),
  http.post("*/v1/auth/resume", async () => {
    return HttpResponse.json({ access_token: "test-token-resumed" });
  }),
  http.post("*/v1/auth/upgrade", async ({ request }) => {
    const body = (await request.json()) as {
      email: string;
      password: string;
      password_confirm?: string;
      accept_terms?: boolean;
      full_name?: string;
    };
    if (!body.email || (body.password?.length ?? 0) < 8 || !body.accept_terms) {
      return HttpResponse.json({ detail: "Dados invalidos" }, { status: 422 });
    }
    state.isGuest = false;
    state.email = body.email;
    state.emailVerified = false;
    state.fullName = body.full_name || state.fullName;
    state.pendingVerifyToken = "test-verify-token";
    return HttpResponse.json({
      ok: true,
      message: "Cadastro recebido. Confirme seu e-mail pelo link que enviamos.",
      verify_token: state.pendingVerifyToken,
    });
  }),
  http.get("*/v1/auth/me", () =>
    HttpResponse.json({
      id: "user-1",
      email: state.email,
      credits: state.credits,
      created_at: "2026-01-01T00:00:00Z",
      is_guest: state.isGuest,
      email_verified: state.isGuest || state.emailVerified,
      is_admin: state.isOwner,
      is_owner: state.isOwner,
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
    }),
  ),
  http.patch("*/v1/auth/me", async ({ request }) => {
    const body = (await request.json()) as Record<string, string | null | undefined>;
    if (body.full_name != null) state.fullName = body.full_name;
    if (body.phone != null) state.phone = body.phone;
    if (body.postal_code != null) state.postalCode = body.postal_code;
    if (body.street != null) state.street = body.street;
    if (body.number != null) state.number = body.number;
    if (body.complement !== undefined) state.complement = body.complement || "";
    if (body.district != null) state.district = body.district;
    if (body.city != null) state.city = body.city;
    if (body.state != null) state.stateUf = body.state;
    if (body.country != null) state.country = body.country;
    return HttpResponse.json({
      id: "user-1",
      email: state.email,
      credits: state.credits,
      created_at: "2026-01-01T00:00:00Z",
      is_guest: state.isGuest,
      email_verified: state.emailVerified,
      is_admin: state.isOwner,
      is_owner: state.isOwner,
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
    });
  }),
  http.post("*/v1/auth/signup", async ({ request }) => {
    const body = (await request.json()) as {
      email: string;
      password: string;
      password_confirm?: string;
      full_name?: string;
      phone?: string;
      postal_code?: string;
      street?: string;
      number?: string;
      complement?: string | null;
      district?: string | null;
      city?: string;
      state?: string;
      country?: string;
      accept_terms?: boolean;
    };
    if (
      !body.email ||
      (body.password?.length ?? 0) < 8 ||
      body.password !== body.password_confirm ||
      !body.accept_terms ||
      !body.full_name ||
      !body.phone ||
      !body.country ||
      !body.postal_code ||
      !body.city ||
      !body.state
    ) {
      return HttpResponse.json({ detail: "Dados invalidos" }, { status: 422 });
    }
    state.credits = 10;
    state.isGuest = false;
    state.email = body.email;
    state.emailVerified = false;
    state.fullName = body.full_name;
    state.phone = body.phone;
    state.postalCode = body.postal_code || state.postalCode;
    state.street = body.street || state.street;
    state.number = body.number || state.number;
    state.complement = body.complement || "";
    state.district = body.district || "";
    state.city = body.city || state.city;
    state.stateUf = body.state || state.stateUf;
    state.country = body.country.toUpperCase();
    state.pendingVerifyToken = "test-verify-token";
    return HttpResponse.json(
      {
        ok: true,
        message: "Cadastro recebido. Confirme seu e-mail pelo link que enviamos.",
        verify_token: state.pendingVerifyToken,
      },
      { status: 201 },
    );
  }),
  http.post("*/v1/auth/verify-email", async ({ request }) => {
    const body = (await request.json()) as { token?: string };
    if (!body.token || body.token !== state.pendingVerifyToken) {
      return HttpResponse.json({ detail: "Link invalido ou expirado" }, { status: 400 });
    }
    state.emailVerified = true;
    state.pendingVerifyToken = null;
    return HttpResponse.json({ access_token: "test-token" });
  }),
  http.post("*/v1/auth/resend-verify", async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    if (!body.email) {
      return HttpResponse.json({ detail: "Dados invalidos" }, { status: 422 });
    }
    if (!state.isGuest && state.email === body.email && !state.emailVerified) {
      state.pendingVerifyToken = "test-verify-token";
      return HttpResponse.json({
        ok: true,
        message: "Se este e-mail estiver cadastrado e pendente, enviamos um novo link de confirmação.",
        verify_token: state.pendingVerifyToken,
      });
    }
    return HttpResponse.json({
      ok: true,
      message: "Se este e-mail estiver cadastrado e pendente, enviamos um novo link de confirmação.",
      verify_token: null,
    });
  }),
  http.post("*/v1/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.password === "wrongpass") {
      return HttpResponse.json({ detail: "Credenciais invalidas" }, { status: 401 });
    }
    if (!state.emailVerified && !state.isGuest) {
      return HttpResponse.json({ detail: "Confirme seu e-mail antes de entrar" }, { status: 403 });
    }
    state.credits = 10;
    state.isGuest = false;
    state.email = body.email;
    state.emailVerified = true;
    return HttpResponse.json({ access_token: "test-token" });
  }),
  http.post("*/v1/auth/forgot-password", async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    if (!body.email) {
      return HttpResponse.json({ detail: "Dados invalidos" }, { status: 422 });
    }
    const known = !state.isGuest && state.email === body.email;
    if (known) {
      state.pendingResetToken = "test-reset-token";
    }
    return HttpResponse.json({
      ok: true,
      message: "Se este e-mail estiver cadastrado, enviamos um link para redefinir a senha.",
      reset_token: known ? state.pendingResetToken : null,
    });
  }),
  http.post("*/v1/auth/reset-password", async ({ request }) => {
    const body = (await request.json()) as {
      token?: string;
      password?: string;
      password_confirm?: string;
    };
    if (
      !body.token ||
      body.token !== state.pendingResetToken ||
      (body.password?.length ?? 0) < 8 ||
      body.password !== body.password_confirm
    ) {
      return HttpResponse.json({ detail: "Link invalido ou expirado" }, { status: 400 });
    }
    state.pendingResetToken = null;
    state.emailVerified = true;
    state.isGuest = false;
    state.credits = 10;
    return HttpResponse.json({ access_token: "test-token" });
  }),
  http.get("*/v1/credits", () => HttpResponse.json({ credits: state.credits })),
  http.get("*/v1/voices", () =>
    HttpResponse.json({ items: [], custom_voice_available: false }),
  ),
  http.get("*/v1/usage/orders/mine", ({ request }) => {
    const auth = request.headers.get("Authorization") || "";
    if (!auth.startsWith("Bearer ")) {
      return HttpResponse.json({ detail: "Nao autenticado" }, { status: 401 });
    }
    return HttpResponse.json([
      {
        id: "my-order-1",
        project_id: "p9",
        summary: "NOVO LIVRO STORY R US CARTOON\nNome: Lia",
        created_at: new Date().toISOString(),
        child_age: 7,
        book_size: "P",
        cover_type: "soft",
        style: "cartoon",
        photo_urls: [],
        has_story: true,
        book_files: [{ label: "PDF do livro", url: "https://arquivos.test/lia.pdf" }],
        print_status: "files_ready",
        payment_status: "pending",
      },
    ]);
  }),
  http.get("*/v1/usage", ({ request }) => {
    const password = request.headers.get("X-Usage-Password");
    const auth = request.headers.get("Authorization") || "";
    if (password !== "segredo" && !(state.isOwner && auth.startsWith("Bearer "))) {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    return HttpResponse.json({
      timezone: "America/Sao_Paulo",
      from_at: new Date().toISOString(),
      to_at: new Date().toISOString(),
      today_usd: 1.25,
      month_usd: 3.5,
      range_usd: 3.5,
      books_count: 2,
      avg_book_usd: 1.75,
      by_type: [{ key: "EBOOK", usd: 2.5, jobs: 2 }],
      by_provider: [{ key: "nano-banana", usd: 2.5, jobs: 2 }],
      books: [
        {
          project_id: "p1",
          child_name: "Matteo",
          status: "EBOOK_READY",
          usd: 1.75,
          unmeasured_jobs: 0,
          updated_at: new Date().toISOString(),
        },
      ],
      recent_jobs: [],
      events: [
        {
          id: "e1",
          job_id: "j1",
          project_id: "p1",
          child_name: "Matteo",
          kind: "image",
          provider: "gemini",
          action: "generate_scene",
          label: "Página 3 — geração",
          cost_usd: 0.039,
          created_at: new Date().toISOString(),
        },
      ],
      events_count: 1,
      daily_spend_usd_ceiling: null,
      daily_credits_ceiling: null,
      today_credits: 2,
      reserved_usd: 0,
      anomalies: [],
      orders: [
        {
          id: "order-1",
          project_id: "p1",
          summary: [
            "NOVO LIVRO STORY R US REALISTA",
            "Nome: Matteo",
            "Idioma: Português",
            "Tema: Matteo e o vale dos dinossauros",
            "Personagens: Matteo",
            "Fotos anexadas: 1 (arquivo recebido)",
          ].join("\n"),
          created_at: new Date().toISOString(),
          child_age: 6,
          book_size: "M",
          cover_type: "hard",
          style: "realistic",
          photo_urls: ["https://fotos.test/crianca.jpg"],
          print_order_id: "print-1",
          print_code: "SR-TESTE001",
          print_status: "files_ready",
          tracking_code: "AA123BR",
          payment_status: "paid",
        },
      ],
    });
  }),
  http.delete("*/v1/usage/orders/:id", ({ request }) => {
    const password = request.headers.get("X-Usage-Password");
    const auth = request.headers.get("Authorization") || "";
    if (password !== "segredo" && !(state.isOwner && auth.startsWith("Bearer "))) {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("*/v1/users/:id", ({ params, request }) => {
    const password = request.headers.get("X-Usage-Password");
    if (password !== "segredo") {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    const found = state.ownerUsers.find((item) => item.id === String(params.id));
    if (!found) {
      return HttpResponse.json({ detail: "Usuario nao encontrado" }, { status: 404 });
    }
    return HttpResponse.json(found);
  }),
  http.patch("*/v1/users/:id", async ({ params, request }) => {
    const password = request.headers.get("X-Usage-Password");
    if (password !== "segredo") {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    const found = state.ownerUsers.find((item) => item.id === String(params.id));
    if (!found) {
      return HttpResponse.json({ detail: "Usuario nao encontrado" }, { status: 404 });
    }
    const body = (await request.json()) as Record<string, unknown>;
    Object.assign(found, body);
    return HttpResponse.json(found);
  }),
  http.delete("*/v1/users/:id", ({ params, request }) => {
    const password = request.headers.get("X-Usage-Password");
    if (password !== "segredo") {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    const idx = state.ownerUsers.findIndex((item) => item.id === String(params.id));
    if (idx < 0) {
      return HttpResponse.json({ detail: "Usuario nao encontrado" }, { status: 404 });
    }
    state.ownerUsers.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("*/v1/users", ({ request }) => {
    const password = request.headers.get("X-Usage-Password");
    if (password !== "segredo") {
      return HttpResponse.json({ detail: "Senha invalida" }, { status: 401 });
    }
    return HttpResponse.json({
      total: state.ownerUsers.length,
      users: state.ownerUsers,
    });
  }),

  http.post("*/v1/projects", async ({ request }) => {
    const body = (await request.json()) as { style?: string };
    const p: Project = {
      id: id(),
      status: "CREATED",
      style: body.style ?? "cgi_3d",
      story_text: null,
      ebook_url: null,
      video_url: null,
      narrated_video_url: null,
      character_approved_at: null,
      book_approved_at: null,
      print_requested_at: null,
      print_status: null,
      created_at: new Date().toISOString(),
    };
    state.projects.set(p.id, p);
    state.jobs.set(p.id, []);
    return HttpResponse.json(p, { status: 201 });
  }),
  http.get("*/v1/projects/:pid", ({ params }) => {
    const p = state.projects.get(params.pid as string);
    return p ? HttpResponse.json(p) : new HttpResponse(null, { status: 404 });
  }),
  http.post("*/v1/projects/:pid/story/text", async ({ params, request }) => {
    const p = state.projects.get(params.pid as string);
    if (!p) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as { story_text?: string };
    p.story_text = (body.story_text ?? "").trim() || null;
    if (p.story_text) p.status = "STORY_READY";
    return HttpResponse.json(p);
  }),
  http.get("*/v1/projects/:pid/assets", ({ params }) => {
    const pid = params.pid as string;
    const p = state.projects.get(pid);
    const jobs = state.jobs.get(pid) ?? [];
    const avatarDone = jobs.some((j) => j.type === "AVATAR" && j.status === "DONE");
    return HttpResponse.json({
      character_url: avatarDone ? "https://cdn.test/character.png" : null,
      realistic_url: null,
      extra_characters: [],
      page_images: p?.page_image_url
        ? [p.page_image_url]
        : p?.ebook_url
          ? ["https://cdn.test/page1.png"]
          : [],
      cover_url: p?.cover_url ?? null,
      in_hand_url: p?.in_hand_url ?? null,
      ebook_url: p?.ebook_url ?? null,
      video_url: p?.video_url ?? null,
      narrated_video_url: p?.narrated_video_url ?? null,
    });
  }),
  http.get("*/v1/projects/:pid/jobs", ({ params }) => {
    const pid = params.pid as string;
    const project = state.projects.get(pid);
    const jobs = state.jobs.get(pid) ?? [];
    if (project) jobs.forEach((j) => j.status !== "DONE" && advance(j, project));
    return HttpResponse.json(jobs.map(({ _polls, ...j }) => ({ ...j, _polls })));
  }),
  http.post("*/v1/projects/:pid/photos", async ({ params }) => {
    const pid = params.pid as string;
    return HttpResponse.json(
      {
        asset_id: id(),
        storage_key: `projects/${pid}/photo/x.jpg`,
        upload_url: "https://storage.local/bucket/x.jpg?op=put",
        expires_in: 600,
      },
      { status: 201 },
    );
  }),
  http.put("https://storage.local/*", () => new HttpResponse(null, { status: 200 })),

  // Upload da foto via API (servidor grava no storage).
  http.post("*/v1/projects/:pid/photo", ({ params }) => {
    const pid = params.pid as string;
    return HttpResponse.json(
      { asset_id: id(), storage_key: `projects/${pid}/photo/x.jpg`, upload_url: "", expires_in: 0 },
      { status: 201 },
    );
  }),

  ...["avatar", "realistic", "story", "ebook", "video", "narrated-video"].map((step) =>
    http.post(`*/v1/projects/:pid/${step}`, async ({ params, request }) => {
      const pid = params.pid as string;
      const type = step === "narrated-video" ? "NARRATED_VIDEO" : step.toUpperCase();
      let payload: Job["result"] = null;
      try {
        const body = (await request.json()) as { brief?: string; duration_s?: number };
        if (body?.brief || body?.duration_s) {
          payload = { payload: { ...(body.brief ? { brief: body.brief } : {}), ...(body.duration_s ? { duration_s: body.duration_s } : {}) } };
        }
      } catch {
        /* body vazio */
      }
      const job: Job = {
        id: id(),
        project_id: pid,
        type,
        status: "PENDING",
        provider: null,
        cost_credits: 0,
        attempts: 1,
        error: null,
        created_at: new Date().toISOString(),
        result: payload,
        _polls: 0,
      };
      state.jobs.get(pid)?.push(job);
      return HttpResponse.json(
        { job_id: job.id, status: "PENDING", type, estimated_cost_credits: 0 },
        { status: 202 },
      );
    }),
  ),
  http.post("*/v1/projects/:pid/preview", async ({ params, request }) => {
    const pid = params.pid as string;
    const project = state.projects.get(pid);
    if (!project) return new HttpResponse(null, { status: 404 });
    const active = (state.jobs.get(pid) ?? []).some(
      (j) =>
        (j.status === "PENDING" || j.status === "RUNNING") &&
        Boolean(j.result?.payload?.preview_chain),
    );
    if (active) {
      return HttpResponse.json(
        { detail: "Já existe uma prévia em andamento para este projeto" },
        { status: 409 },
      );
    }
    let brief: string | undefined;
    try {
      const body = (await request.json()) as { brief?: string };
      brief = body?.brief?.trim() || undefined;
    } catch {
      /* body vazio */
    }
    const type = "AVATAR";
    project.character_approved_at = null;
    project.book_approved_at = null;
    const job: Job = {
      id: id(),
      project_id: pid,
      type,
      status: "PENDING",
      provider: null,
      cost_credits: 0,
      attempts: 1,
      error: null,
      created_at: new Date().toISOString(),
      result: { payload: { preview_chain: true, ...(brief ? { brief } : {}) } },
      _polls: 0,
    };
    state.jobs.get(pid)?.push(job);
    return HttpResponse.json(
      { job_id: job.id, status: "PENDING", type, estimated_cost_credits: 0 },
      { status: 202 },
    );
  }),
  http.post("*/v1/projects/:pid/avatar/approve", ({ params }) => {
    const p = state.projects.get(params.pid as string);
    if (!p) return new HttpResponse(null, { status: 404 });
    const jobs = state.jobs.get(p.id) ?? [];
    const avatarDone = jobs.some((j) => j.type === "AVATAR" && j.status === "DONE");
    if (!avatarDone) {
      return HttpResponse.json({ detail: "Gere o personagem antes de aprovar" }, { status: 400 });
    }
    p.character_approved_at = new Date().toISOString();
    return HttpResponse.json(p);
  }),
  http.post("*/v1/projects/:pid/book/approve", ({ params }) => {
    const p = state.projects.get(params.pid as string);
    if (!p) return new HttpResponse(null, { status: 404 });
    if (!p.character_approved_at || !p.ebook_url) {
      return HttpResponse.json({ detail: "Aprove o personagem e monte o e-book antes" }, { status: 400 });
    }
    p.book_approved_at = new Date().toISOString();
    return HttpResponse.json(p);
  }),
  http.post("*/v1/projects/:pid/print-request", ({ params }) => {
    const p = state.projects.get(params.pid as string);
    if (!p) return new HttpResponse(null, { status: 404 });
    if (!p.book_approved_at || !p.ebook_url) {
      return HttpResponse.json({ detail: "Aprove o livro antes de pedir o impresso" }, { status: 400 });
    }
    p.print_requested_at = p.print_requested_at ?? new Date().toISOString();
    p.print_status = "requested";
    return HttpResponse.json(p);
  }),
];

export const server = setupServer(...handlers);
