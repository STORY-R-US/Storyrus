# Ferramenta editorial — revisão 2026-11-05.2

Revisão solicitada após a comparação com as três referências fornecidas pelo
responsável. Os ajustes pertencem ao gerador; as fotografias enviadas e as
imagens já produzidas não são editadas por esta atualização.

## Composição e tipografia

- Capa: personagem em destaque à esquerda, atividade/objetos à direita e título
  centralizado dentro de um bloco superior direito. Retirada a regra que
  reservava todo o quarto superior vazio e empurrava o personagem para baixo.
- Nunito Black 900 no título, com tamanho de 8,3% da largura; Nunito Bold 700
  nos versos, com tamanho de 4,3%, entrelinha 1,2 e alinhamento centralizado.
  Arquivos reais, licença OFL, cobertura de caracteres e hashes registrados.
- Cenários e objetos com aquarela/lápis de cor, papel marfim, cores coordenadas
  e luz suave. Rosto reconhecível e anatomia natural. Um filtro sépia ou fundo
  fotográfico desfocado não atende ao acabamento ilustrado solicitado.
- A apresentação frontal da capa ganha lombada e espessura sem deformar a arte
  quadrada usada na impressão.
- Foto segurando o livro: enquadramento mais aberto, cabeça inteira, cadeira e
  colo; livro próximo de um terço da largura da imagem. O compositor recusa
  superfícies fora da faixa de 28–36%, mesmo que a revisão visual as aceite.
  A roupa externa pode diferir do figurino da personagem impressa.

## Textos e narrativa visual

Os rascunhos priorizam quatro versos curtos, naturais para leitura em voz alta,
com rimas leves e aprendizado concreto. As páginas mostram passos sucessivos
de uma mesma atividade e um resultado visível. No tema amplo de computador,
uma atividade criativa acessível é preferível a código/programação não pedidos.

Ações de cada página e ambiente compartilhado ficam registrados separadamente
dos versos. A arte usa essas ações e o livro completo recebe o plano da prévia
para manter a experiência. Versos automáticos são medidos com a fonte real antes
de gerar imagens; nomes, títulos e textos literais fornecidos são preservados.

## Versões e ativação

O novo pacote é `backend/app/assets/editorial/2026-11-05.2/`; a versão .1 permanece
intacta para consulta e livros existentes. Novos projetos usam .2. Uma nova
solicitação explícita de prévia não aprovada pode adotar .2 e renovar somente
rascunhos gerados automaticamente. Textos fornecidos e prévias aprovadas são
protegidos. A publicação não inicia trabalhos nem regenera imagens por si só.

Continuam sendo três imagens no idioma escolhido. Pagamento, autenticação,
aprovações, Catálogo e pedidos conservam seus controles.

## Verificação

- Backend local: 541 testes, cobertura 79,20%; inclui testes privados da
  homologação, que não acompanham a publicação.
- Tipografia medida com cópia literal: título em duas linhas e versos de
  referência em quatro linhas, sem cortes ou redução automática da fonte.
- Testes com provedores simulados verificam a composição, ações das páginas,
  escala do livro, proteção de textos fornecidos e compatibilidade da versão .1.
- Site: lint, tipos/build e 23 testes focados aprovados; 17 casos de navegação
  aprovados, incluindo Estúdio, Catálogo, idiomas e pedidos.
- Não foram executadas gerações reais de fotos nesta revisão, conforme pedido.
  A aceitação estética será feita nas próximas gerações do responsável; testes
  automatizados não comprovam que uma imagem atingiu o acabamento de referência.

Referências técnicas: [fontes Nunito e licença](https://github.com/google/fonts/tree/main/ofl/nunito)
e [instruções oficiais de imagens](https://developers.openai.com/api/docs/guides/image-prompting).
