# Story R Us — Web (frontend)

Vite + React + TypeScript. Fluxo **conta obrigatória**: landing com Entrar/Criar
conta → JWT via `POST /v1/auth/login` ou `/signup` → estúdio (`/app`) → criar
projeto → upload de foto → disparar etapas (avatar/história/ebook/vídeo) com
**progresso ao vivo** via polling dos jobs.

## Rotas

`react-router-dom` separa marketing de produto (`Root.tsx`):

- `/` — **Landing** de marketing (PT/EN/ES). CTAs levam a `/cadastro` ou `/entrar`.
- `/entrar`, `/cadastro` — login e signup (`Auth.tsx`).
- `/app` — **Estúdio** (`App` → `Studio`); exige conta registrada.
- `/gastos` — painel privado de custos USD.
- `/privacidade`, `/termos` (+ aliases EN) — páginas legais.

## Rodar

Na raiz do monorepo (com a API já no ar via `make up`):

```bash
make web           # npm install + vite em apps/web
```

Ou neste diretório:

```bash
npm install
npm run dev        # http://localhost:5173 (proxy /v1 e /health → :8000)
```

A API precisa estar de pé (`make up` na raiz, ou
`docker compose -f backend/docker-compose.yml up --build`). O Vite faz proxy de
`/v1` e `/health` para `VITE_API_PROXY` (default `http://localhost:8000`).

## Testes

Vitest + Testing Library + MSW (a API é mockada em memória — não chama o backend real).

```bash
npm test           # watch
npm run test:run   # uma passada (CI)
```

Cobertura dos testes:

- `Auth.test.tsx` — signup/login e redirect `next`.
- `App.test.tsx` — gate sem sessão → cadastro; com conta → criar livro.
- `Studio.test.tsx` — presets do catálogo e progresso do estúdio.
- `Landing.test.tsx` — CTAs de auth e links Personalizar.
- `Usage.test.tsx` — painel `/gastos`.

Os mocks ficam em `src/test/server.ts` (handlers MSW com estado em memória que imita
projetos, jobs, auth e o avanço de status a cada polling).

## Estrutura

Ver `src/` — `Landing.tsx` + `landing.css` (marketing), `Auth.tsx` (conta),
`Studio.tsx` + `studio/` (produto), `api.ts` (cliente HTTP + sessão).
