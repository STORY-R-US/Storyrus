# Story R Us — API (núcleo)

MVP do backend: **foto → personagem → ebook → vídeo animado**. Pipeline assíncrono com
jobs idempotentes, moderação/segurança e clients reais de IA (OpenAI GPT Image, Claude, Kling). A geração não debita créditos; o impresso se fatura na OS. FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL.

## Estrutura

```
backend/
  app/
    config.py            # settings via ambiente (12-factor)
    database.py          # engine/sessão SQLAlchemy
    models.py            # users, projects, jobs, assets (UUID/JSON portáveis)
    schemas.py           # DTOs Pydantic v2
    security.py          # hash de senha + JWT
    deps.py              # usuário autenticado
    storage.py           # URLs assinadas S3/R2
    services/
      credits.py         # débito/estorno com lock de linha
      jobs.py            # enfileiramento idempotente + backpressure + custo
    routers/
      auth.py credits.py projects.py jobs.py webhooks.py
    ai_clients/
      base.py            # interfaces ImageProvider/TextProvider/VideoProvider
      image_openai.py  text_anthropic.py  video_kling.py  factory.py
    workers/
      runner.py          # loop: claim + retry/backoff + estorno
      handlers.py        # AVATAR/STORY/EBOOK/STORYBOARD/VIDEO
      ebook.py           # montagem HTML -> PDF
  alembic/               # migrations
  tests/                 # pytest (SQLite em memória)
  Dockerfile  docker-compose.yml  pyproject.toml  .env.example
```

## Rodar local (Docker)

Na raiz do monorepo (preferido):

```bash
make init && make up          # Postgres + Redis + API + worker
# Swagger: http://localhost:8000/docs
# Frontend: make web  (apps/web; proxy /v1 → :8000)
```

Ou só neste diretório:

```bash
cp .env.example .env          # preencha as chaves de IA
docker compose up --build     # sobe Postgres + Redis + API + worker (migra automático)
# Swagger: http://localhost:8000/docs
```

Dentro do compose, `DATABASE_URL` / `REDIS_URL` apontam para os serviços `db` e
`redis` (o `.env.example` usa `localhost` para quem roda a API no host).

## Rodar local (sem Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Testes

```bash
pytest            # usa SQLite em memória; não chama provedores externos
```

## Fluxo da API (resumo)

1. `POST /v1/auth/signup` → token JWT.
   Convidado: `POST /v1/auth/guest`; `refresh` / `resume` / `upgrade` (STO-26).
2. `POST /v1/projects` → cria projeto (`style`: realistic|cartoon|anime).
3. `POST /v1/projects/{id}/photos` → URL assinada para upload da foto.
4. `POST /v1/projects/{id}/avatar|story|ebook|video` → **202 Accepted** com `job_id`.
   Envie `Idempotency-Key` para evitar duplicar custo.
5. `GET /v1/jobs/{id}` → polling do estado. Vídeo conclui via `POST /v1/webhooks/video`
   (callback assinado por HMAC com anti-replay: `X-Timestamp` + `X-Nonce` +
   `X-Signature` sobre `{timestamp}.{nonce}.{body}`; janela `WEBHOOK_MAX_AGE_S`).

## Decisões de engenharia

- **Geração sem débito de créditos** (`CREDITS_ENABLED=false`). Com o flag ligado, o débito volta a ocorrer antes da etapa e a falha definitiva estorna.
- **Idempotência** por `Idempotency-Key` única em `jobs`.
- **Backpressure**: `MAX_CONCURRENT_JOBS_PER_USER` (default 4) conta todos os tipos
  PENDING/RUNNING, inclusive VIDEO e NARRATED_VIDEO.
- **Envelope de erros**: respostas de erro usam `{detail, error:{code,message,status}}`
  (handlers em `app/errors.py`).
- **Consistência de personagem**: `character_ref` é reutilizada em todas as cenas.
- **Segurança/LGPD**: convidados recebem JWT isolado (`POST /v1/auth/guest`); refresh/resume
  evitam órfãos; upgrade mantém o mesmo `user_id`. Chaves só no
  backend, entregáveis via URL assinada de curta duração, callbacks HMAC com janela de
  tempo e nonce (anti-replay).
- **Troca de provedor** sem reescrever o fluxo: tudo atrás de `ai_clients` (factory).

## Workers (pipeline)

Os endpoints registram jobs `PENDING`; o worker os consome e executa as etapas.

```bash
python -m app.workers.runner     # local
# ou: docker compose up worker
```

Runner (`app/workers/runner.py`):

- **claim** do próximo `PENDING` com `FOR UPDATE SKIP LOCKED` (vários workers em paralelo).
- **retry** com backoff exponencial em erro transitório (`ProviderError(transient=True)`
  e Exceptions de rede/timeout/429/5xx — STO-36).
- ao esgotar `JOB_MAX_ATTEMPTS` → `FAILED` (estorna o custo só se o job tiver sido debitado).

Handlers (`app/workers/handlers.py`):

- `AVATAR` gera o personagem e grava `character_ref` (reusado em todas as cenas).
- `STORY` gera o texto (Claude).
- `EBOOK` ilustra cada página reusando o personagem e monta o PDF.
- `STORYBOARD` gera keyframes; `VIDEO` dispara o Kling (único provedor de vídeo)
  e faz polling até concluir (ou conclui via webhook), republicando o arquivo no
  storage próprio. Não há integração Veo — `VIDEO_PROVIDER` deve ser `kling`.

## Demo: vídeo Kling do livro Meu Pai, Meu Herói

Com `KLING_API_KEY` (console moderno) — ou o par legado AK/SK — preenchido:

```bash
# na raiz
make kling-meupai
# smoke test (1 página):
make kling-meupai ARGS='--limit 1'
# ou direto:
cd backend && .venv/bin/python scripts/gen_meupai_kling.py
```

Saída: `apps/web/public/exemplos/video-meupai-heroi-kling.mp4` (17 clips de 5s concatenados).
A API Key única do console (`kling.ai/dev/api-key`) vai em `KLING_API_KEY`.
