# Recuperações automáticas na criação

A ferramenta deve recuperar problemas de transporte e formatação sem pedir que o
cliente refaça seus dados e sem comprar o mesmo resultado novamente.

Casos tratados nesta revisão:

- JSON com marcador Markdown, BOM ou uma camada adicional de codificação é lido
  localmente. Identificadores equivalentes de idioma e listas de versos são
  normalizados sem inventar dados ausentes.
- O título informado e os trechos fornecidos prevalecem antes da validação dos
  campos retornados pela IA. Não dependem de a IA repeti-los corretamente.
- Quebras rígidas excessivas em versos gerados podem ser reorganizadas localmente
  quando necessário para caber. Todas as palavras são mantidas, os limites mínimos
  de fonte continuam valendo e texto do cliente não é reescrito.
- Cabeçalhos Página/Page, Markdown e blocos de texto são reconhecidos na separação
  do miolo. Páginas repetidas, ausentes ou fora de ordem não são renumeradas para
  simular um livro completo.
- Falha temporária de leitura do armazenamento não transforma um recibo pago e
  concluído em geração incerta. O worker tenta ler novamente com limite de
  tentativas e retoma o resultado salvo, sem chamar o provedor novamente.
- Erros temporários específicos de S3/R2 passam pela recuperação automática do
  worker. Falta de arquivo, credencial inválida e dados corrompidos não autorizam
  comprar outra imagem.
- Conteúdo recebido incompleto e inválido não é repetido inutilmente do mesmo
  cache; é identificado como falha interna, não erro nos dados do cliente.

Limites preservados: geração realmente incerta permanece bloqueada para evitar
cobrança duplicada; não se inventam identidade, roupa, páginas ou aprovações.
Recuperação automática não permite desenhar sobre áreas protegidas nem pular
aprovação de prévia, pagamento ou autorização de fotos.

Testes usam resultados simulados e armazenamento em memória, incluindo falha de
leitura seguida de recuperação pelo worker com uma única chamada inicial ao
provedor simulado. Não requerem gerações pagas.
