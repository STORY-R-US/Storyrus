# Gerador editorial — LIVRO UPDATE

## Estado

Implementação local da política `2026-11-05.1`, baseada no pacote LIVRO UPDATE
e na instrução posterior do responsável: **exatamente três imagens no idioma
escolhido**. Os nove PNGs mencionados no pacote de origem não são a entrega ativa.
A homologação real descrita abaixo valida a geração da prévia; a aceitação
operacional de gráfica, compra e entrega permanece pendente.

## Funcionamento

- `services/editorial_profile.py` carrega e verifica a impressão digital do
  pacote imutável em `app/assets/editorial/2026-11-05.1/`.
- `config/editorial-policy.json` controla fonte, cor, entrelinha e tentativas.
  `storyrus-profile.json` conserva o mapeamento das referências e estilos.
- Os modelos `01_TEXTO_NARRATIVO`, `02_ARTE_E_CENAS` e `03_REVISAO_VISUAL`
  são carregados nas chamadas reais de texto, arte e revisão.
- `handlers/editorial_book.py` conecta o fluxo existente a artes planas,
  camadas tipográficas e composição física. Fotos originais são transmitidas
  como imagens e associadas a nomes por um manifesto, incluindo fotos extras.
- `workers/editorial_render.py` usa Nunito Medium 500 real, azul #172A3A e
  entrelinha 1,2. Registra texto literal, quebras, região, tamanho, fonte e versão.
  Verifica integridade e cobertura de caracteres da fonte. A fonte é OFL;
  sua origem e versão estão em `fonts/manifest.json`.

## As três imagens

1. Capa: arte plana sem letras, título composto e apresentação frontal.
2. Livro aberto: duas artes de página finalizadas com seus versos, aplicadas
   às duas superfícies de um mockup por transformação em perspectiva.
3. Leitura: a arte plana final da capa é aplicada ao livro da cena fotográfica.
   O compositor restaura as regiões de primeiro plano, como mãos e dedos.

As artes intermediárias ficam em armazenamento privado, com hashes e operações;
não são novos itens da prévia. O ZIP autenticado contém somente três PNGs.
A arte plana da capa é guardada separadamente e usada nos PDFs, em vez da
apresentação física da prévia.

## Miolo e correções

O livro pago usa a mesma política e fonte. O roteiro novo respeita o elenco e
a idade; não impõe criança ou vilão a todo pedido. Mantém o produto existente
de 16 páginas; esta mudança não cria um miolo automaticamente após a prévia.
Cada página possui arte sem texto, composição final e parâmetros persistidos.
A correção de versos pode reutilizar a arte quando a ação não mudou.
Texto longo exige recomposição dentro dos limites; não é truncado nem tem
a fonte reduzida indefinidamente. Páginas finais não são recortes de mockups.
O PDF do miolo não espelha páginas nem adiciona o antigo selo de numeração.

## Aprovação, falhas e retomada

Cada etapa possui chave derivada de projeto, política, fotografias, figurino,
idioma, cena e conteúdo relevante. Arte concluída é reutilizada em reenvios.
Uma regeneração explícita cria uma revisão identificável. Trocar a capa
invalida a leitura dependente; as páginas da abertura são preservadas.
Arquivos anteriores são arquivados, não apresentados como atuais.

Há até duas novas tentativas por etapa, respeitando os controles de gasto
existentes. Geometria, composição ou inspeção inconclusivas impedem conclusão.
Resultados genéricos de teste não permitem baixar ou aprovar a prévia oficial.
A nova política permite aprovar as três imagens antes da cotação; a história
completa permanece bloqueada até pagamento e aprovação da prévia no servidor.
Não altera autenticação, gateway de pagamento ou destinos de hospedagem.

## Compatibilidade e limites

Não há migração de banco; são usados os campos JSON existentes. As versões
editoriais anteriores são preservadas. Ler livros existentes não os regenera;
pedir nova prévia adota a versão atual. Não aplicar rollback ou reaplicar render.yaml.

A localização das superfícies usa marcações temporárias magenta/ciano na cena
base, detectadas nos pixels. O compositor mede os contornos e substitui somente
as áreas marcadas, preservando as mãos e bordas externas. Não usa coordenadas
estimadas livremente pelo modelo de texto. Superfícies não identificadas,
curvas ou excessivamente ocultas falham sem entregar o mockup.
A transformação reutiliza os arquivos exatos; a naturalidade das bordas, luz,
oclusões e fidelidade das pessoas precisa de aceitação visual com geração real.
Não se declara equivalência visual apenas por hash, contagem de arquivos ou teste.

A homologação privada passou a usar credencial OpenAI armazenada localmente
de forma criptografada, sem `.env` versionado. Gerações reais são feitas com
banco e armazenamento isolados, sem alterar dados de produção. A aceitação
visual teve uma execução real completa em português com um adulto, seguida
dos ajustes de acabamento descritos abaixo. Permanecem casos de
aceitação separados: criança com animal, textos fixados e três idiomas.

Prévia não é arquivo aprovado para gráfica. A resolução efetiva, sangria, cor,
lombada e requisitos de produção dependem da gráfica ainda não definida.

## Revisão e ativação

Antes de editar, `origin/main` foi consultado: o checkout já correspondia a
`6f91c9a`. Foram preservadas as alterações locais anteriores e o pacote .4.
Antes de publicar, conferir o remoto novamente, revisar o diff completo e
seguir o AGENTS.md. Este trabalho não autoriza anunciar aceitação real nem
produção atualizada sem essas verificações.

## Verificações locais iniciais

- Backend: suíte completa com 520 testes aprovados e cobertura de 79,04%
  (mínimo da CI: 70%). Após os últimos ajustes de título, referência da capa
  e retomada, os sete testes focados do fluxo composto também passaram.
- Web: 242 testes aprovados; lint, verificação de tipos e build aprovados.
- Navegador: 17 testes aprovados, incluindo Estúdio, Catálogo PT/EN/ES,
  capas em desktop/celular e pedidos.
- Ruff: lint e formatação aprovados. `git diff --check` aprovado.
- Conferência visual técnica com padrão sintético: texto, acentos,
  orientação, perspectiva e preservação do primeiro plano examinados.
  Esse padrão não representa uma geração de livro nem comprova identidade.
- O teste antigo de correlação dos logs foi isolado da autenticação de fotos
  simulada; os controles reais permanecem cobertos pelos testes de privacidade.
- O remoto oficial foi conferido novamente e permaneceu em `6f91c9a`.
  Nenhum push, deploy ou alteração de ambiente de produção foi realizado.

Essas verificações iniciais foram complementadas pela homologação real abaixo.

## Correções observadas na homologação real

A resposta da ficha visual pode conter identidade e figurino em objetos ou listas.
O normalizador preserva essas observações como descrição estruturada, exige
identidade, figurino e paleta, e permite personalidade/interesse vazios quando
não fornecidos. Não completa uma identidade ausente com conteúdo genérico.

A revisão mantém observações gerais sobre a natureza probabilística da avaliação
sem reprovar uma imagem explicitamente válida e sem defeitos. Problemas concretos
de identidade, anatomia, texto ou composição continuam impedindo a entrega.

A área reservada ao texto é calculada pelas caixas reais das letras, com margem
de segurança; a caixa maior de quebra de linhas não é tratada como tinta.
A área medida é conferida na arte sem letras e na composição real
antes de armazenar a arte como reutilizável. Uma sobreposição na primeira
composição regenera a cena com o relatório de correção; não reaplica o mesmo
texto sobre os mesmos pixels. A revisão recebe os dados medidos da tipografia,
incluindo o hash da fonte e o alinhamento, para separar confirmação técnica de
avaliação visual. Falhas do provedor não consomem o limite de reprovações visuais.

O avaliador recebe as referências separadas da imagem final e um recorte exato
da reserva medida. Uma foto original não é uma saída a avaliar quanto a layout.
A capa pode ser recomposta por deslocamento sem reduzir a pessoa, com geração
apenas da continuação natural do fundo. A máscara orienta a edição e não prova
preservação de pixels: identidade, anatomia e composição continuam sendo revistas.
Contrato consultado: [edição com máscara, documentação oficial OpenAI](https://developers.openai.com/api/docs/guides/image-generation#edit-an-image-using-a-mask).

Para o miolo, o planejamento inicial é adaptado à área livre da arte efetivamente
gerada. A aplicação confere o encaixe dos versos com fonte real e pode pedir até
três ajustes de layout sobre a mesma arte, sem reescrever o texto nem diminuir a
fonte. O layout final e sua procedência acompanham a página.

Os pacotes editoriais novos preservam seus bytes no Git entre Windows e Linux,
pois seus snapshots são calculados sobre os arquivos exatos. As versões antigas
já publicadas permanecem intactas. Fotos, resultados reais e credenciais da
homologação são privados e não integram esta publicação.

O compositor registra também o modelo de cena sem a arte aplicada para permitir
retomada de ajustes geométricos sem pagar por uma nova fotografia. Cores suaves
nas bordas das páginas são cobertas; perto de mãos, a seleção é mais restrita
para não confundir reflexos da marcação com dedos ou roupas.

## Verificações da correção

- Geração real em português com adulto concluída. Capa, livro aberto e pessoa
  segurando o livro conferidos; ZIP autenticado validado com exatamente três PNGs.
- Suíte local completa do backend: 537 testes aprovados, cobertura 78,90%.
  Inclui os testes do ambiente privado, que não acompanha o deploy.
- Testes focados posteriores: retomada, montagem das três cenas, encaixe de
  texto, preservação das mãos e remoção das marcações nas bordas.
- Web: 242 testes; lint, tipos e build aprovados. Os fluxos de navegador
  passaram em 17 casos; dois casos de Catálogo precisaram de nova execução
  isolada após timeout da execução concorrente.
- Remoto oficial conferido novamente em `6f91c9a`, sem alterações concorrentes.
- A publicação exclui o servidor de homologação, banco, fotos, resultados
  pessoais e credenciais. A aprovação do cliente e as regras de pagamento
  continuam sendo aplicadas no servidor.
- A CI identificou a dependência de teste PyMuPDF ausente; ela foi declarada
  em `dev`, mantendo a verificação visual da orientação do PDF.
- O job mobile já falhava em `6f91c9a`: Expo 51 conflita com a exigência de
  Expo 53–54 do Clerk instalado. A mesma falha foi confirmada no job anterior
  `126893967714`. Nenhum arquivo mobile foi alterado nesta publicação.
- O caso reportado também revelou uma região inicial pequena demais para
  versos curtos. A calibração mede alternativas maiores com a fonte real antes
  de gerar a arte, preservando integralmente as palavras e o tamanho da fonte.
