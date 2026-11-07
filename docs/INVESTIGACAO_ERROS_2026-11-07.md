# Investigação de erros — 07/11/2026

Varredura solicitada pelo responsável, com investigador independente e
reproduções locais. Nenhuma imagem paga foi gerada para testar.

## Erros corrigidos

- Títulos e versos podiam exceder áreas fixas e repetir o mesmo planejamento
  sem resolver. O encaixe agora é local, conserva as palavras e mantém limites
  legíveis. Formas equivalentes de acentos Unicode são aceitas.
- A prévia passa a medir todos os textos antes de comprar a primeira imagem;
  o livro completo confere os 16 trechos antes da primeira página.
- Novos prompts do Catálogo descartavam pedidos de melhoria da capa, do livro
  aberto e da imagem segurando. A instrução agora acompanha o papel correto.
- Ajustes do livro aberto e da imagem segurando eram convertidos em
  `cover_only`, voltando para a capa sem realizar a melhoria. A restrição agora
  respeita a etapa e a imagem solicitada; alterações de capa ainda exigem aprovação.
- Ajustes de fundos de páginas de leitura ignoravam a instrução e reutilizavam
  o mesmo resultado. A instrução explícita agora participa do prompt e do cache.
- Na falha, a tela ocultava a edição e só oferecia repetir. Há um editor local
  dos textos da prévia e acesso a Novo Projeto. Salvar não enfileira geração.

## Proteções verificadas

Recomposição de texto conserva a arte armazenada. Salvar correções exige
proprietário autenticado, projeto sem pagamento e nenhuma geração ativa.
Texto impossível pede correção antes de chamadas de imagem. A avaliação
artística e as aprovações permanecem com o usuário.

Os testes de regressão cobrem os três modelos e os três papéis da prévia,
recuperação local, limites de leitura, acentos e preservação de aprovações.
Testes simulados verificam o fluxo e as instruções enviadas, sem provar que
todo resultado artístico futuro será satisfatório.
