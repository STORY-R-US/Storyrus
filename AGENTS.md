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