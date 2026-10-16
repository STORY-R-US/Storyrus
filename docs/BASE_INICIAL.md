# Base inicial do Story R Us

Data de consolidação: 15/10/2026.

Esta é a base única para iniciar o próximo ciclo de desenvolvimento. O histórico
local começa em um commit inicial; novas mudanças devem partir desta estrutura.

## Conteúdo consolidado

- Aplicação publicada com as correções de sessão, retomada do backend, geração
  OpenAI e fluxo mobile.
- Perfil mestre do livro, etapas de aprovação e renderização associada.
- Catálogo com navegação entre imagens na página do livro.
- API, workers, migrações de banco, site, aplicativo mobile, testes e assets usados pelo projeto.

## Limites desta base

O fluxo pós-prévia foi integrado: aprovação explícita, resumo do pedido, cotação,
entrega, acompanhamento e aprovação final antes da impressão. O pagamento permanece
indisponível até a escolha e configuração de um provedor.
Os dados de produção, contas externas, chaves, dependências instaladas, builds e
materiais avulsos de criação não fazem parte deste repositório.

O conteúdo do banco e os objetos armazenados precisam dos backups próprios dos
serviços. Ter o código não comprova titularidade nem migração dessas contas.

## Trabalhar a partir daqui

Use somente `backend/`, `apps/web/` e `apps/mobile/` para as novas alterações.
Instale dependências pelos arquivos de configuração e lockfiles incluídos.
Configure os segredos no ambiente e execute os testes antes de publicar.

O ZIP distribuído contém uma única pasta Storyrus e os arquivos reais dos assets.
O repositório Git local conserva o ponto de partida e as alterações posteriores;
o ZIP não carrega o histórico `.git`.
