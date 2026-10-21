# Fluxo de impressão na base ativa

O pacote inclui o caminho da prévia até a autorização do livro completo para
impressão, integrado ao perfil mestre e à lista de pedidos do cliente.

## Etapas para a família

1. Revisar a prévia e escolher continuar ou solicitar ajustes. Os ajustes geram
   uma nova prévia e exigem uma nova aprovação.
2. Aprovar a prévia e conferir tamanho, acabamento, quantidade, endereço e frete.
3. Salvar a cotação e retomar o pedido em `/meus-pedidos`, inclusive após recarregar
   ou entrar novamente na conta.
4. Após uma confirmação real de pagamento, gerar o livro completo. A integração
   evita disparar duas gerações para a mesma confirmação de pagamento.
5. Revisar as páginas e o PDF. Solicitar ajustes quando necessário e autorizar
   explicitamente a impressão. A aprovação da prévia não substitui essa autorização.

## Etapas administrativas

Os arquivos de capa e miolo alimentam o pacote de produção do pedido. O painel
administrativo controla o envio para validação e o resultado da validação.
A etiqueta de envio depende das aprovações exigidas pelo fluxo e das credenciais
do serviço de frete configurado.

## Configuração pendente para operação real

O código mantém a cobrança desabilitada enquanto não houver um gateway de
pagamento implementado, registrado e selecionado em `PRINT_GATEWAY`. Preencher
somente o nome de um provedor não implementa uma integração de pagamento.

Também devem ser definidos os requisitos da gráfica em `PRINT_*`: sangria,
margem de segurança, lombada, vinco, padrão PDF, perfil de cor, nomes dos arquivos
e medidas da embalagem. O frete depende das configurações `MELHOR_ENVIO_*`.
Esses valores precisam corresponder aos serviços e à gráfica da empresa.

Até a configuração do pagamento, o cliente pode salvar e acompanhar uma cotação.
O pacote não confirma pagamentos nem envia livros para impressão automaticamente.

## Banco de dados

Antes de iniciar a aplicação com um banco existente, faça o backup apropriado e
execute `alembic upgrade head` em `backend/`, com `DATABASE_URL` apontando para o
ambiente desejado. A revisão `0027_purchase_flow` sucede `0026_book_profile` e
adiciona o campo persistente `projects.purchase_flow`.

## Exportar o código

Para verificar o aplicativo compilado antes de exportar, execute em `apps/web/`:

```sh
npm run build
npx playwright test --config=playwright.export.config.ts
```

Na raiz da base, execute:

```sh
python scripts/exportar_pacote.py --output ../output/Storyrus.zip --metadata-dir ../output/exportacao-storyrus
```

O repositório precisa estar registrado em commit e sem alterações pendentes.
O ZIP contém uma única pasta `Storyrus`, os arquivos versionados e os assets
reais. Dependências instaladas, builds, `.git`, arquivos `.env` reais e bancos
locais ficam fora do pacote. O manifesto SHA256 e os dados do commit são gravados
na pasta de metadados informada.
