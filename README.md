# Story R Us

Base inicial única do aplicativo Story R Us, consolidada em 15/10/2026.
Esta pasta é o ponto de partida para o desenvolvimento a partir de agora.

## Estrutura

- `backend/`: API FastAPI, workers, integrações de IA, banco e migrações.
- `apps/web/`: site e estúdio em React, Vite e TypeScript.
- `apps/mobile/`: aplicativo Expo e configuração EAS.
- `.github/workflows/`: verificações automáticas do projeto.
- `docs/`: arquitetura e definição da base inicial.

Há apenas uma cópia de cada aplicação neste pacote. Assets utilizados pelo código
estão incluídos como arquivos reais; o pacote não depende de ponteiros Git LFS.

## Começar em desenvolvimento

Requisitos: Python 3.11 ou superior, Node.js 20 ou superior e Docker Compose.

1. Copie `backend/.env.example` para `backend/.env` e preencha as configurações do ambiente.
2. Execute `docker compose -f backend/docker-compose.yml up --build -d`.
3. Em `apps/web`, execute `npm ci` e `npm run dev`.
4. Para o mobile, entre em `apps/mobile`, execute `npm ci` e `npm start`.

A API local usa `http://localhost:8000` e o site usa `http://localhost:5173`.
O mobile precisa apontar para uma API acessível pelo aparelho; confira seu README.
O Makefile também reúne os comandos do ambiente local.

## Configurações da empresa

Use contas da Story R Us e mantenha as chaves somente nas variáveis do servidor.
O pacote inclui modelos de configuração, sem arquivos `.env` reais ou backups de banco.
Configure explicitamente os emails de administração, destinatários de avisos,
armazenamento, cobrança e limites de gasto antes de habilitar o ambiente de produção.
Cadastro em plataformas e transferência de contas são etapas externas ao pacote.

## Verificações

Backend, dentro de `backend/`:

```sh
pip install -e ".[dev]"
ruff check app tests
ruff format --check app tests
pytest -q
```

Web, dentro de `apps/web/`:

```sh
npm ci
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
npm run e2e
```

Para executar o navegador em uma porta exclusiva desta base, use
`npx playwright test --config=playwright.baseline.config.ts`.

Mobile, dentro de `apps/mobile/`:

```sh
npm ci
npm run typecheck
npm test
```

## Documentação

- [Definição do ponto de partida](docs/BASE_INICIAL.md)
- [Validação da base inicial](docs/VALIDACAO.md)
- [Arquitetura e fluxo da aplicação](docs/ARQUITETURA.md)
- [Configuração e implantação](DEPLOY.md)
- [API e workers](backend/README.md)
- [Mobile](apps/mobile/README.md)

O repositório local começa em um único commit na branch `main`. Os diretórios de
trabalhos anteriores permanecem fora desta base. Publicar o código ou alterar
o ambiente em produção exige configurar o destino e executar o procedimento de deploy.

## Depois da prévia

A família escolhe **Gostei, continuar com meu livro** ou **Quero ajustar**.
Os ajustes salvam título, tema, história e orientações visuais e geram uma nova
prévia para revisão. Aprovar a prévia abre o resumo com tamanho, acabamento,
quantidade, endereço e frete. **Salvar cotação e acompanhar** mantém o pedido
acessível em `/meus-pedidos`, inclusive após recarregar a página.

Enquanto não houver provedor de pagamento configurado, o pedido permanece como
cotação, sem cobrança. A confirmação real de pagamento enfileira uma única
geração do livro completo. A família revisa todas as páginas e o PDF, pode pedir
ajustes e precisa autorizar expressamente a impressão. A aprovação da prévia
nunca vale como aprovação do livro completo. Pedidos antigos continuam legíveis.

Antes de executar esta versão em um banco existente, rode `alembic upgrade head`
na pasta `backend` para criar o campo persistente `projects.purchase_flow`.
Validação sem credenciais de produção: `python backend/scripts/validate_purchase.py tests`.
