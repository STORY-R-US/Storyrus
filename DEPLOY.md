# Deploy — Story R Us

Guia para colocar o projeto no ar: **frontend na Vercel** e **backend no Render**.

## Arquitetura

```
Navegador
   │
   ▼
Vercel (frontend Vite/React)  ──/v1/* (proxy)──►  Render (API FastAPI)
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                     Postgres     Worker      Cloudflare R2
                                     (Render)   (jobs IA)      (storage)
```

- **Frontend**: `apps/web` (Vite + React). Vai na **Vercel**.
- **Backend**: `backend` (FastAPI). Vai no **Render** (Docker), com um **worker** que processa os jobs (personagem, história, e-book, vídeo) e um **Postgres**.
- **Mobile**: `apps/mobile` (Expo). Builds/submit via **EAS** — ver `apps/mobile/PUBLISH.md` (não bloqueia o deploy web/API).
- **Storage**: **Cloudflare R2** em produção (variáveis `STORAGE_*`). Localmente o
  compose **não** sobe MinIO — use as mesmas vars apontando para R2 (ou outro
  endpoint S3-compatible que você configure à parte).
- **Redis**: opcional. Sem ele, o worker faz *polling* do banco e tudo funciona.

> As chaves (OpenAI GPT Image, Anthropic, Kling, ElevenLabs, R2) **nunca** ficam no repositório — só em variáveis de ambiente. O `.env` está no `.gitignore`.
>
> O worker precisa de **ffmpeg** no PATH para o vídeo narrado (já instalado na imagem Docker do backend). Sem ffmpeg, o fallback gera um GIF slideshow.

---

## 1) Backend no Render

1. Acesse **render.com** → **New → Blueprint** → conecte o repositório `Storyrus`.
2. O Render lê o `render.yaml` e cria 3 recursos: **storyrus-api** (web), **storyrus-worker** (worker) e **storyrus-db** (Postgres).
3. Em cada serviço (api e worker), preencha as variáveis marcadas como *secret* em **Environment**:
   - `OPENAI_API_KEY` — GPT Image (`gpt-image-1`) + juiz de história; obrigatório (`IMAGE_PROVIDER=openai`)
   - `ANTHROPIC_API_KEY` — `sk-ant-...`
   - `KLING_API_KEY` — API Key Bearer do console Kling (só se for usar vídeo).
     Alternativa legada: `KLING_ACCESS_KEY` / `KLING_SECRET_KEY`.
   - `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` — TTS narrado (opcional; sem chave usa edge-tts)
   - `CREDIT_GRANT_SECRET` — só a API; vazio = `POST /v1/credits/grant` recusa. **Nunca** no frontend
   - `RESEND_API_KEY` — **obrigatório em prod** para confirmação de cadastro e esqueci-senha (ver **§ E-mail transacional**). Sem chave a UI ainda diz que enviou, mas **não sai e-mail**.
   - `TRANSACTIONAL_FROM_EMAIL` — Blueprint já define `Story R Us <noreply@storyrus.ai>`; só mude se o domínio verificado no Resend for outro.
   - `PUBLIC_WEB_ORIGIN` — Blueprint já define `https://storyrus.ai` (links nos e-mails).
   - `OPIK_API_KEY` / `OPIK_WORKSPACE` / `OPIK_PROJECT_NAME` — tracing Opik (opcional; sem chave o wrapper é no-op). Em prod a API e o worker chamam `opik.configure` no boot; traces de job carregam `request_id` + `job_id` para correlacionar com os logs JSON.
   - `LOG_FORMAT=json` — Blueprint já define; logs estruturados com `request_id` / `job_id` (STO-29). O header `X-Request-ID` é ecoado pela API e persistido no job.
   - `USAGE_DASHBOARD_PASSWORD` — senha compartilhada dos painéis `/gastos`, `/pedidos` e `/usuarios`. Só é aceita enquanto `OWNER_PASSWORD_FALLBACK=true` (default). Sem senha, sem admin e sem `OWNER_EMAILS`, os painéis respondem 503
   - `OWNER_PASSWORD_FALLBACK` — `true` (default) mantém a senha compartilhada como fallback. `false` exige conta com `users.is_admin` (ou e-mail em `OWNER_EMAILS`)
   - `USAGE_DASHBOARD_PASSWORD_PREVIOUS` — senha antiga durante rotação (opcional; ignorada se o fallback estiver desligado)
   - `OWNER_EMAILS` — e-mails (csv) que entram nos painéis com o JWT e são gravados como `is_admin` no primeiro acesso. Default de produção: `eng.andrevitor89@gmail.com`. A migration `0023_user_is_admin` também marca essa conta
   - `USAGE_LOCKOUT_MAX_ATTEMPTS` / `USAGE_LOCKOUT_WINDOW_S` — trava após falhas (default 5 / 900s); a senha correta sempre libera
   - `REDIS_URL` — opcional; sem Redis o worker faz polling do Postgres
   - `STORAGE_BUCKET` — ex.: `storyrus`
   - `STORAGE_ENDPOINT_URL` — `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
   - `STORAGE_PUBLIC_ENDPOINT_URL` — **mesma URL acima** (no R2 é o mesmo endpoint)
   - `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` — token S3 do R2
   - (`JWT_SECRET` e `WEBHOOK_SIGNING_SECRET` o Render gera sozinho.)
   - `DATABASE_URL` é injetada automaticamente pelo banco do Blueprint.
4. Aguarde o build. Quando a **storyrus-api** ficar *Live*, copie a URL (ex.: `https://storyrus-api.onrender.com`).

### Painéis admin (passo manual)

A migration `0023_user_is_admin` cria `users.is_admin` (default false) e marca `eng.andrevitor89@gmail.com`. O boot da API aplica o Alembic.

1. Confirme que essa conta (e-mail verificado) abre `/gastos` logada, sem digitar a senha do painel.
2. Para outra conta admin, rode no Postgres `UPDATE users SET is_admin = true WHERE lower(email) = 'pessoa@exemplo.com';` **ou** acrescente o e-mail em `OWNER_EMAILS` e abra o painel logado — o primeiro acesso grava `is_admin`.
3. Só depois disso, se quiser aposentar a senha compartilhada, defina `OWNER_PASSWORD_FALLBACK=false` na API do Render. Enquanto estiver `true` (default), o header `X-Usage-Password` continua válido.

> Free tier do Render hiberna após inatividade e o Postgres free expira em ~90 dias — ok para testes. Para produção/demos estáveis, veja **§ Beyond free (recomendado)**.

### Beyond free (recomendado)

O Blueprint (`render.yaml`) continua em `plan: free` de propósito — **não** força upgrade pago no git. Em produção (ou demos que não podem “acordar frias”), suba os planos **no painel** do Render:

| Recurso | Free (demo) | Recomendado além do free |
|---------|-------------|---------------------------|
| **storyrus-api** | Hiberna após ~15 min sem tráfego | Plano **Starter** (ou superior) — API always-on |
| **storyrus-worker** | Também hiberna; jobs param enquanto dorme | Mesmo plano always-on — worker precisa ficar acordado |
| **storyrus-db** | Expira em ~90 dias | Postgres **pago** (Starter+) — sem expiração do free |

**Cold start (free):** o primeiro request depois da hibernação demora (imagem Docker pesada: InsightFace/ONNX/ffmpeg). Enquanto a API/worker dormem, o estúdio parece “morto” e jobs enfileirados não avançam. Postgres free somado a isso torna demos instáveis.

**Mitigação temporária (só free):** um health-check externo periódico em `GET /health` (ex.: UptimeRobot) pode reduzir hibernação da **web** service. Isso **não** substitui always-on: o worker free ainda pode dormir, o banco free ainda expira, e pings abusivos podem violar o fair-use do free. Trate como paliativo até migrar API+worker+DB.

Passos no Render (painel, sem mudar o Blueprint):

1. **API** → Settings → Instance Type → Starter (ou acima).
2. **Worker** → o mesmo (always-on).
3. **Postgres** → upgrade para plano pago **antes** dos ~90 dias do free, ou crie um DB pago e aponte `DATABASE_URL` (Blueprint `fromDatabase` ou var manual).

### Cloudflare R2 (storage)
- Painel Cloudflare → **R2** → crie um bucket (ex.: `storyrus`).
- **Manage R2 API Tokens** → crie um token com permissão *Object Read & Write* → use o **Access Key ID** e **Secret Access Key**.
- Endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (use o ID da conta, não o nome do bucket).

### E-mail transacional (Resend)

Dois fluxos usam a mesma chave Resend no backend (`storyrus-api` no Render):

1. **Confirmação de cadastro** — `POST /v1/auth/signup` e `POST /v1/auth/resend-verify` → e-mail “Confirme seu e-mail” com link `/verificar-email?token=…`
2. **Esqueci a senha** — `POST /v1/auth/forgot-password` → e-mail “Redefinir senha” com link `/redefinir-senha?token=…`

O front na Vercel **não** envia e-mail — só o Render precisa de `RESEND_API_KEY`.

**Por que a UI diz “enviamos um link” sem chegar nada?** Signup e reenvio mostram a tela “Verifique seu e-mail”; forgot-password sempre responde OK genérico (não revela se o e-mail existe). Sem `RESEND_API_KEY`, o envio é no-op e o link só aparece nos logs da API (em dev o JSON ainda traz `verify_token` / `reset_token`).

#### Passo a passo

1. Crie conta em [resend.com](https://resend.com) → **API Keys** → crie `re_...`.
2. **Domains** → adicione `storyrus.ai` (ou um subdomínio tipo `send.storyrus.ai`).
3. No DNS da **GoDaddy** (`storyrus.ai`), adicione **só** os registros que o Resend mostrar (DKIM TXT/CNAME, SPF/MX no host `send`, etc.).
   - **Não apague** o MX do Microsoft 365 em `@` (`storyrus-ai.mail.protection.outlook.com`).
   - O MX do Resend fica em **`send`** (subdomínio), não no apex — não conflita com o Outlook.
4. No Resend, clique **Verify**. Confira em [dns.email](https://dns.email) se os registros propagaram.
5. No **Render** → **storyrus-api** → **Environment**:
   - `RESEND_API_KEY` = `re_...`
   - `TRANSACTIONAL_FROM_EMAIL` = `Story R Us <noreply@storyrus.ai>` (ou o domínio verificado)
   - `PUBLIC_WEB_ORIGIN` = `https://storyrus.ai` (já no Blueprint)
6. Salve e aguarde o redeploy (ou Manual Deploy). Nos logs do boot deve aparecer `transactional_email_ready` (não o warning `RESEND_API_KEY ausente`).
7. Confira: `GET https://storyrus-api-ul8u.onrender.com/health` → `"email_configured": true`.
8. Teste **esqueci a senha**: https://storyrus.ai/esqueci-senha com um e-mail cadastrado. Cheque spam.

**Cold start (free):** o primeiro request após hibernação pode demorar. Mitigação: plano Starter ou ping periódico em `/health` (§ Beyond free).

---

## 2) Frontend na Vercel

1. Acesse **vercel.com** → **Add New → Project** → importe o repositório `Storyrus`.
2. **Root Directory**: deixe na **raiz** do repo (o `vercel.json` da raiz já manda construir `apps/web`).
3. Framework/Build/Output já vêm do `vercel.json`. Clique em **Deploy**.
4. Confirme que o `/v1` aponta para a sua API do Render:
   - Há **dois** `vercel.json`: na **raiz** (usado quando o Root Directory da Vercel
     é a raiz do repo — o fluxo oficial) e em `apps/web/` (espelho se o root
     directory for `apps/web`). As `destination` de `/v1` e `/health` devem
     permanecer **iguais** nos dois arquivos (hoje: `https://storyrus-api-ul8u.onrender.com`).
     Se a URL do Render mudar, atualize **ambos** e dê `git push`.

### Como ver o site
- URL canônica: **https://storyrus.ai**
- `https://www.storyrus.ai` redireciona para a raiz.
- `https://storyrus.vercel.app` redireciona para `https://storyrus.ai` (regra nos `vercel.json`).
- A cada `git push` no `main`, a Vercel atualiza a produção automaticamente.

---

## 3) Domínio da GoDaddy no Vercel

A **GoDaddy só guarda o DNS**. O site continua hospedado na Vercel. Não use hospedagem, construtor de sites nem encaminhamento da GoDaddy.

O projeto **storyrus** já tem `storyrus.ai` e `www.storyrus.ai`. O `www` e o `storyrus.vercel.app` redirecionam para `https://storyrus.ai` via `vercel.json`.

Há e-mail Microsoft 365 no domínio (`storyrus-ai.mail.protection.outlook.com`). **Não apague MX** e **não troque nameservers**.

### Na Vercel

Já feito: Settings → Domains no projeto **storyrus**. HTTPS a Vercel emite sozinha depois do DNS.

### Na GoDaddy (DNS)

Painel GoDaddy → **Domínios** → `storyrus.ai` → **DNS** / **Gerenciar DNS**.

**Criar/atualizar** (TTL 600):

| Tipo  | Nome | Valor |
|-------|------|-------|
| **A** | `@` | `216.198.79.1` |
| **A** | `@` | `64.29.17.1` |
| **CNAME** | `www` | `b1f150d36b8308d7.vercel-dns-017.com` |

Fallback se a GoDaddy só aceitar um A: `@` → `76.76.21.21`. Alternativa de CNAME: `cname.vercel-dns.com`.

**Remover só o parking do site** (hoje em `3.33.130.190` e `15.197.148.33`):

- Registros **A** antigos em `@` com esses IPs.
- **CNAME** de `www` apontando para `storyrus.ai` / parking / `secureserver`.
- **Encaminhamento de domínio** (Domain Forwarding) — desligar.
- Website Builder / hospedagem GoDaddy nesse domínio — desconectar.

**Manter:**

- Nameservers `ns09.domaincontrol.com` / `ns10.domaincontrol.com`
- MX `storyrus-ai.mail.protection.outlook.com` (e TXT/CNAME de Outlook, se existirem)

### Conferir

1. Vercel: `storyrus.ai` e `www` em **Valid Configuration**.
2. `https://storyrus.ai` e `https://www.storyrus.ai` — landing e `/app`.
3. `https://storyrus.vercel.app` deve redirecionar para `https://storyrus.ai`.
4. O front chama `/v1` no **mesmo domínio**; a Vercel faz proxy para o Render. Não precisa CORS extra.

Propagação: minutos na maioria dos casos; até 24–48 h se havia parking. Reverificar com `vercel domains verify storyrus.ai`.

---

## 4) Ligar frontend ↔ backend

1. Backend no ar no Render → copie a URL da api.
2. Ajuste a `destination` nos `vercel.json` para essa URL (se ainda não estiver).
3. `git push` → a Vercel redeploya. Agora o estúdio (`/app`) chama o backend e gera de verdade.

---

## Desenvolvimento local (opcional)

Na raiz do repo:

```bash
make init    # backend/.env a partir do .env.example
make up      # Postgres + Redis + API + worker (backend/docker-compose.yml)
make web     # Vite em apps/web (host); proxy /v1 → :8000
make down
```

- API: http://localhost:8000/docs
- Web: http://localhost:5173 (`make web` ou `cd apps/web && npm run dev`)
- Storage: configure `STORAGE_*` em `backend/.env` (R2 ou S3-compatible). O compose
  **não** inclui MinIO nem o frontend.

Detalhes: `README.md` (raiz), `Makefile`, `backend/README.md`.

---

## Resumo rápido

| Camada    | Plataforma | Observação |
|-----------|------------|------------|
| Frontend  | Vercel     | Root = raiz; `vercel.json` constrói `apps/web` |
| Domínio   | GoDaddy → Vercel | `storyrus.ai`; DNS na GoDaddy; site na Vercel |
| API       | Render     | Docker; free hiberna — Starter+ always-on em prod (§ Beyond free) |
| Worker    | Render     | Jobs de IA; same always-on em prod |
| Banco     | Render Postgres | Free ~90 dias; pago em prod |
| Storage   | Cloudflare R2 | Variáveis `STORAGE_*` |
| E-mail    | Resend (via Render) | `RESEND_API_KEY` na API; DNS DKIM sem mexer no MX M365 (§ E-mail) |
| Redis     | — (opcional) | Sem ele, worker faz polling do banco |
| Mobile    | EAS (Expo) | `apps/mobile/eas.json` + [PUBLISH.md](apps/mobile/PUBLISH.md); segredos fora do git |
