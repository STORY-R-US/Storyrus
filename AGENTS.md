# Base oficial Story R Us

O usuário aprovou em 29/10/2026 a versão publicada em https://storyrus.ai.
O ponto de restauração é a tag `producao-aprovada-2026-10-29`, commit
`ff091d2199c78fd209bd8414f0d86cd815abed52`.

## Toda atualização

- Parta do `main` atual de `STORY-R-US/Storyrus`, que contém a base aprovada e as atualizações posteriores. Confira o remoto antes de editar e novamente antes de publicar.
- Nunca publique uma cópia local antiga por cima da produção. Não restaure arquivos inteiros de outras pastas, commits antigos ou backups para aplicar uma mudança pontual.
- Preserve Estúdio, Catálogo, capas, títulos, botões, idiomas, navegação, autenticação e pedidos fora do escopo solicitado.
- Revise o diff completo antes de publicar; toda exclusão ou alteração fora do pedido deve ser investigada. Não use force push no main.
- Valide com os testes existentes adequados à mudança. Se tocar no Estúdio ou Catálogo, confira também os dois fluxos e a apresentação das capas antes da publicação.
- A tag é um ponto de recuperação: não faça rollback de produção sem pedido explícito. Um commit não impede regressões sozinho.

Mantenha `backend/`, `apps/web/` e `apps/mobile/`. Leia `README.md` e
`docs/BASE_INICIAL.md`. Use a CI existente. Segredos permanecem nas variáveis
de ambiente; não versione arquivos `.env` reais nem dados de produção.

## Hospedagem de produção desde 30/10/2026

- O workspace Render autorizado é **STORYRUS** (`tea-db7pf867bikc73bmv7eg`).
- API: `storyrus-producao-api`, serviço `srv-dbi8ip0ae00c73bh8fq0`, em
  `https://storyrus-producao-api.onrender.com`.
- Postgres: instância `dpg-db7qm2ij9qps73ddfptg-a`, base lógica de produção
  `storyrus_producao_20261030`. Preserve o DATABASE_URL privado configurado.
- Não use os serviços de My Workspace nem a API gratuita antiga do STORYRUS
  para publicar versões. Eles são anteriores à migração.
- Mantenha os proxies de `vercel.json` e `apps/web/vercel.json` iguais.
- A produção usa IA real: preserve `SKIP_OPENAI=false` e `OFFLINE_FALLBACK=false`.
  Não substitua falhas de provedor ou falta de saldo por textos ou imagens de ensaio.
- Erros da IA devem falhar a geração, sem aprovar etapas nem enfileirar conteúdo simulado.
  Pedido, pagamento e livro completo exigem a aprovação explícita da prévia no servidor.
- Testes sem créditos usam apenas `book_profile.test_mode=true` no projeto autorizado,
  com aviso visível e aprovações manuais. Não ative ensaio global na produção.
- O `render.yaml` é um modelo de provisionamento anterior à migração, não o
  estado atual a sincronizar. Não o aplique sobre os recursos existentes nem
  substitua DATABASE_URL por uma referência à base lógica antiga da instância.
- Detalhes operacionais: `docs/MIGRACAO_STORYRUS_2026-10-30.txt`.
