# Auditoria da geração de livros — 12/11/2026

## Constatações verificadas sem geração paga

- Produção: `OPENAI_IMAGE_MODEL=gpt-image-1.5`; qualidade efetiva `high`.
- Edições com esse modelo enviam `input_fidelity=high`. Fotos são lidas do
  armazenamento e transmitidas sem redução ou recompressão pelo provider.
- Arte quadrada: 1024 × 1024; retrato: 1024 × 1536; paisagem: 1536 × 1024.
  A resolução da prévia não constitui comprovação de qualidade de impressão.
- As cinco imagens do pacote editorial 2026-11-05.3 são byte a byte idênticas
  às referências do pacote local Story R Us 1.0.20: acabamento Amor de Mãe,
  texto Meu Pai Meu Herói, título Amor de Bisavó e duas referências Cartoon.
- O modelo interno da ferramenta de imagem do Codex não está exposto nesta
  sessão. Portanto não é possível declarar equivalência de modelo ou de saída.
- A consulta somente de leitura `/v1/models` confirmou acesso a modelos mais
  novos, incluindo as famílias GPT Image 2, 2.5 e 2.6. Disponibilidade não
  comprova equivalência visual; esta correção mantém o modelo de produção.

## Correções

1. O padrão de configuração e o exemplo de ambiente passam a usar 1.5,
   alinhados à produção, em vez do modelo antigo 1.
2. Capa, páginas e apresentação física recebem a referência visual do modelo
   escolhido também nas versões anteriores à versão 4 do Catálogo. Projetos
   sem modelo selecionado recebem o guia visual resolvido para aquele projeto.
3. Cada guia tem papel explícito de estilo/composição, nunca de identidade.
   Fotos originais continuam primeiro. A referência da capa não substitui
   a referência do miolo; o tema solicitado não é substituído pelo exemplo.
4. A instrução da referência visual usa seu número na lista. Assim uma arte
   salva acrescentada para correção continua sendo o alvo da edição.
5. O provider Cartoon não acrescenta um livro genérico a um pedido que já
   contém o contrato completo do modelo selecionado. Nos caminhos genéricos,
   o alvo da edição é numerado antes de acrescentar a referência de estilo.

## Preservação e validação

Nenhuma migração de dados, regeneração de projeto ou alteração de cobrança.
Os identificadores dos intermediários e as proteções de retomada permanecem
inalterados. Artes já compradas continuam sendo reutilizadas; a melhoria de
referência aplica-se às próximas gerações necessárias/autorizadas.

Testes locais usam providers simulados: parâmetros e bytes enviados, capa e
miolo de vários modelos, apresentação, alvo de edição, retomada, arte corrupta
e resultados de provedor incertos. A CI existente valida API, web, mobile e E2E.
Não houve geração paga de teste. Passar esses testes não é aprovação estética
de uma nova imagem; o acabamento precisa ser avaliado numa criação real.

Referência técnica consultada: [documentação oficial de imagens da OpenAI](https://developers.openai.com/api/docs/guides/image-generation).
