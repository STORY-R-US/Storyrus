# Perfil editorial do Estúdio — 2026-11-04.4

Revisão 2026-11-04.4 do perfil editorial já integrado ao fluxo oficial do
Estúdio. A revisão anterior permanece disponível para leitura de projetos
existentes; um pedido de nova prévia migra o projeto às regras atuais.

## Ligação com o produto

O formulário existente chama `POST /v1/projects`, que usa
`services/book_profile.initial_profile` para fixar versão e SHA-256 do pacote.
`POST /v1/projects/{id}/preview` continua enfileirando EBOOK;
`workers/handlers/ebook.handle_ebook` chama `master_book.preview`.
Este passa a carregar o perfil e prompts consolidados por
`services/editorial_profile`, sem um segundo Estúdio ou provedor novo.

Conforme a solicitação atual, a prévia gera somente capa, livro aberto e pessoa
segurando o livro, no idioma escolhido. O pacote de instruções contém um padrão
antigo de nove saídas; ele não se aplica a este fluxo. Os pacotes editoriais são
versionados em `backend/app/assets/editorial/`.

## Comportamento

- Três cenas independentes; textos localizados são definidos antes das imagens e
  registrados com origem e congelamento no perfil persistido do projeto.
- Título recebido conserva a capitalização. Fotos originais são enviadas em cada
  chamada, junto às referências de acabamento escolhidas. Cartoon recebe seus
  dois assets; a referência da mãe fica restrita ao acabamento realista.
- Na capa e no livro aberto, o gerador cria a arte-base sem letras e o backend
  compõe os textos literais com Nunito SemiBold incluída no projeto: azul
  #172A3A, título superior centralizado, versos à esquerda e entrelinha 1,2.
  O encaixe falha de modo fechado se o texto não couber. A cena final é validada
  contra texto duplicado, extra, ausente, cortado ou sobreposto.
- Cada chamada de geração recebe somente as regras da cena correspondente.
  Para o livro aberto, a capa não é enviada como imagem de referência, evitando
  que o título seja copiado para as páginas; a identidade vem das fotos originais.
  A cena de leitura usa a capa aprovada como referência do livro físico. No livro aberto, os versos também chegam ao gerador como guias semânticos da ação de cada página, mas ficam excluídos do campo de texto visível da arte-base.
- A leitura depende da capa validada daquele idioma, enviada como imagem. Uma
  correção de capa remove a leitura anterior e gera a substituta. A aplicação
  não possui composição em perspectiva da capa: sua fidelidade depende de
  geração por referência e posterior inspeção, sem garantia de igualdade pixel a pixel.
- Validação visual multimodal compara a saída final, fotos, referências de
  estilo, texto literal e capa. Resposta de validação incompleta, com issues ou
  sem aprovação explícita impede conclusão; candidato e relatório ficam no
  trabalho. A cena de leitura precisa corresponder à capa validada; divergência
  mantém a prévia bloqueada para correção.
- Cenas prontas são gravadas individualmente; falhas preservam as anteriores.
  O trabalho registra estados e arquivos, e cada asset registra textos,
  referências por hash, perfil, validação e hash da capa dependente.
- Não há geração automática da história completa após essa prévia. O botão
  existente permite ao cliente pedir a próxima etapa explicitamente, mantendo
  as aprovações, pagamento e autorização de impressão existentes.
- `GET /v1/projects/{id}/preview/package` exige autorização do projeto e das
  fotos, três PNGs validados, distintos e decodificáveis, textos atuais e capa
  correspondente na leitura. A interface oferece o download autenticado do ZIP.
  Imagens de demonstração não satisfazem o download oficial.

## Verificações

Verificações concluídas nesta revisão:

- Backend focado (`test_master_book.py` e `test_text_openai.py`): 57 passaram.
- Ruff (`check` e `format --check`) nos arquivos Python alterados: passou.
- Web: 241 testes passaram; lint e build passaram.
- Navegador: 17 testes passaram, incluindo Estúdio, Catálogo nos três idiomas, capas desktop/celular e fluxo de pedido.
- A suíte completa do backend não foi repetida nesta revisão; em execução anterior, todos os testes exceto um teste de observabilidade passaram. O teste restante falhou por fixture de banco sem `scalar`, fora desta alteração.
- A suíte usa provedores simulados. Não fiz uma geração real de aceitação nesta revisão; os logs recentes de produção mostram geração pela OpenAI, mas as cenas foram reprovadas pela validação automática.
- O diff passou em `git diff --check` e contém somente os arquivos editoriais, backend relacionado, testes e este registro.

## Ativação

Não há migração de banco: os registros usam os campos JSON existentes. Conserve
os diretórios da versão editorial para permitir a retomada de trabalhos antigos;
uma mudança de conteúdo exige nova versão. Não altere os arquivos de uma versão
em uso: a impressão digital divergente interrompe a geração.

Os perfis 2026-11-04.1, 2026-11-04.2 e 2026-11-04.3 permanecem imutáveis. Em um pedido de prévia para um projeto
com a versão anterior, o worker atualiza o perfil e regenera as cenas que não
correspondem à nova versão. Isso impede misturar imagens com regras diferentes.
Não há migração de banco. Antes de publicar, executar a CI e conferir Estúdio,
Catálogo e capas conforme `AGENTS.md`.
