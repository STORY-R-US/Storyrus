# Perfil editorial do Estúdio — 2026-11-04.1

Implementado na branch `codex/perfil-editorial-estudio`, a partir do main oficial
`a4ea3d7`. Não publicado nem aceito visualmente em produção.

## Ligação com o produto

O formulário existente chama `POST /v1/projects`, que usa
`services/book_profile.initial_profile` para fixar versão e SHA-256 do pacote.
`POST /v1/projects/{id}/preview` continua enfileirando EBOOK;
`workers/handlers/ebook.handle_ebook` chama `master_book.preview`.
Este passa a carregar o perfil e prompts consolidados por
`services/editorial_profile`, sem um segundo Estúdio ou provedor novo.

Conforme a correção do usuário, novos livros geram somente capa, livro aberto e
pessoa segurando o livro, no idioma escolhido (PT-BR, inglês ou espanhol). Trabalhos antigos conservam o contrato anterior. Arquivos
editoriais ficam em `backend/app/assets/editorial/2026-11-04.1`; não copie
fixtures privados, fotos de clientes ou baseline para esse diretório.

## Comportamento

- Três cenas independentes; textos localizados são definidos antes das imagens e
  registrados com origem e congelamento no perfil persistido do projeto.
- Título recebido conserva a capitalização. Fotos originais são enviadas em cada
  chamada, junto às referências de acabamento escolhidas. Cartoon recebe seus
  dois assets; a referência da mãe fica restrita ao acabamento realista.
- Títulos e versos da prévia são compostos com a fonte Nunito SemiBold já
  incluída no backend: azul #172A3A, título superior centralizado, versos à
  esquerda e entrelinha 1,2. Textos grandes falham se não couberem integralmente.
  O layout pede áreas livres; a inspeção visual verifica possíveis sobreposições.
- A leitura depende da capa validada daquele idioma, enviada como imagem. Uma
  correção de capa remove a leitura anterior e gera a substituta. A aplicação
  não possui composição em perspectiva da capa: sua fidelidade depende de
  geração por referência e posterior inspeção, sem garantia de igualdade pixel a pixel.
- Validação visual multimodal compara saída, fotos, referências de estilo,
  texto literal e capa. Reprovação impede conclusão; o candidato e o relatório
  ficam registrados no trabalho. Essa avaliação automática tem limitações e
  não equivale a aceitação visual humana ou aprovação de compra.
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

- Suíte de compatibilidade do Estúdio e novos casos editoriais: 38 passaram na revisão pré-publicação, incluindo os três casos editoriais (quantidade, referências, dependências, retomada e ZIP).
- Teste adicional com provedor simulado: passou; cobre referências anexadas,
  falha na terceira chamada, retomada sem refazer as duas saídas prontas e ZIP
  com três PNGs decodificáveis. Não é geração real de aceitação.
- Interface: 25 testes passaram (MasterBookFlow e idempotência da API).
- Ruff, verificação de tipos, lint web e build web passaram.
- Navegador: seis testes passaram, cobrindo Estúdio, Catálogo nos três idiomas e capas em desktop/celular.
- A revisão corrigiu a substituição por papel/idioma/página, evitando duplicatas quando os metadados da nova imagem diferem.

O caso privado de André não foi enviado ao provedor. O ambiente local informa
`openai_key_configured=False` e `skip_openai=True`; isso bloqueia a aceitação
real, sem expor qualquer segredo. Ainda é necessário executar o fixture privado,
comparar as três saídas novas com as referências e validar identidade, rima,
anatomia, texto, geometria e capa na leitura no idioma escolhido.

## Ativação

Não há migração de banco: os registros usam os campos JSON existentes. Conserve
os diretórios da versão editorial para permitir a retomada de trabalhos antigos;
uma mudança de conteúdo exige nova versão. Não altere os arquivos de uma versão
em uso: a impressão digital divergente interrompe a geração.

Antes da publicação, configure um ambiente autorizado de testes usando a gestão
de segredos existente, com OpenAI disponível, `SKIP_OPENAI=false` e
`OFFLINE_FALLBACK=false`; conclua a aceitação real acima. Revise o diff, execute
os fluxos Estúdio e Catálogo e confira novamente o main remoto. Publique pelo
GitHub oficial conforme AGENTS.md, sem force push ou sincronização do render.yaml
histórico. Depois confirme a implantação e um trabalho do Estúdio contendo
`book_profile.editorial.version=2026-11-04.1` antes de anunciar produção ativa.
