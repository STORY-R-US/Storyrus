# Story R Us

Transforma uma foto em um personagem ilustrado, gera uma história, monta um ebook
e (opcional) um vídeo animado. Pipeline assíncrono de IA com jobs
idempotentes, moderação/segurança e provedores reais (Nano Banana Pro, Claude, Kling).
A cobrança é a ordem de serviço do livro impresso.

## Monorepo

```
backend/      # API (FastAPI) + workers + clients de IA   → backend/README.md
apps/web/     # Frontend (Vite + React + TS) + testes (Vitest/MSW) + E2E (Playwright)
apps/mobile/  # App Expo (React Native): mesmo fluxo no celular → apps/mobile/README.md
.github/      # CI: ruff+pytest (backend), tsc+vitest+build (web), Playwright (e2e)
```

## CI

`.github/workflows/ci.yml` roda em push/PR:

- **backend** — `ruff check` + `pytest`.
- **frontend** — `tsc --noEmit` + `vitest run` + `vite build`.
- **e2e** — `playwright test` (navegador real, API mockada), com relatório anexado.

## Rodar local

Na raiz, o `Makefile` orquestra o stack real em `backend/docker-compose.yml`
(**Postgres + Redis + API + worker**). Não sobe frontend nem MinIO.

```bash
make init          # copia backend/.env.example → backend/.env (se faltar)
make up            # docker compose -f backend/docker-compose.yml up --build -d
#  API: http://localhost:8000/docs
make web           # Vite em apps/web — proxy /v1 e /health → :8000
#  Web: http://localhost:5173
make down          # para o stack do backend
```

Popular dados e validar o fluxo da API (com o stack no ar):

```bash
make seed          # demo@storyrus.app / demo12345 (50 créditos)
make demo          # signup → projeto → upload → etapas → jobs
```

Sem `make`, os equivalentes são:

```bash
cp backend/.env.example backend/.env
docker compose -f backend/docker-compose.yml up --build -d
docker compose -f backend/docker-compose.yml run --rm api python scripts/seed.py
cd apps/web && npm install && npm run dev   # VITE_API_PROXY default → localhost:8000
```

`make help` lista os alvos. Deploy em produção: `DEPLOY.md` (Vercel + Render).
Detalhes da API: `backend/README.md`.

## Chaves a preencher (`backend/.env`)

Tudo funciona offline para desenvolvimento, mas o pipeline real precisa de:

| Variável | Para quê |
|---|---|
| `OPENAI_API_KEY` | GPT Image (avatar, cenas, ebook) + juiz de história |
| `ANTHROPIC_API_KEY` | Claude (geração da história) |
| `KLING_API_KEY` (ou `KLING_ACCESS_KEY`/`KLING_SECRET_KEY` legado) | Kling (único provedor de vídeo) |
| `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` / `STORAGE_BUCKET` / `STORAGE_ENDPOINT_URL` | R2/S3 (uploads e entregáveis) |
| `JWT_SECRET` / `WEBHOOK_SIGNING_SECRET` | segredos da aplicação |

Sem as chaves de IA/storage, a API e os workers sobem e o fluxo de
jobs/idempotência roda; as chamadas de geração falham de forma controlada
(estado `FAILED`).

Storage local: configure `STORAGE_*` apontando para **Cloudflare R2** (ou outro
S3-compatible). O compose **não** sobe MinIO — veja `DEPLOY.md`.

## Fluxo

1. Na landing, **Entrar** (`/entrar`) ou **Criar conta** (`/cadastro`) — JWT de conta
   via `POST /v1/auth/login` ou `/signup`.
2. Só com conta registrada abre o estúdio (`/app`). Mutações de livro no backend
   rejeitam convidados (`403 Cadastro necessario`).
3. Cria projeto e escolhe o estilo.
4. Envia a foto (URL assinada).
5. Dispara as etapas (avatar → história → ebook → vídeo). Cada uma enfileira um
   job e responde **202**; o worker processa e o front acompanha o progresso ao
   vivo. Gerar o livro não gasta créditos. O impresso se fatura na OS do pedido.

Guest (`POST /v1/auth/guest`) e upgrade (`/upgrade`) permanecem na API para
compatibilidade, mas não liberam criação de livros.
