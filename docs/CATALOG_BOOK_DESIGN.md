# Modelo completo do Catálogo

Novos projetos do Estúdio enviam `catalog_design_id`: `auto`, `family`,
`adventure` ou `cartoon`. O servidor grava o modelo completo em
`book_profile.book_design`, com versão, posições, acabamento e hashes das
três referências reais do mesmo livro. O modo automático mantém a escolha
gravada mesmo quando o tema muda. Projetos antigos sem esse campo conservam
seu fluxo anterior.

- Amor de Bisavó: título no alto à direita; leitura à esquerda e ilustração
  à direita no miolo.
- Meu Pai, Meu Herói: título superior central; duas cenas, cada uma com seu
  texto superior.
- Amor de Mãe cartoon: título no alto à esquerda; ilustração à esquerda e
  leitura à direita.

As imagens do Catálogo são enviadas como referências visuais efetivas ao
provedor, além das regras de composição. Fotos do projeto definem as pessoas;
nomes, versos, objetos e personagens do exemplo não são copiados. A capa
aprovada acompanha a geração das páginas seguintes para manter continuidade.

Título e versos são compostos localmente com fonte e posição do modelo.
O encaixe começa no tamanho preferido do modelo e, se necessário, ajusta a
quebra de linhas e o tamanho dentro de limites legíveis: mínimo de 3,5% da
largura para títulos e 2,8% para versos. Não altera palavras nem move o bloco
do Catálogo. Acentos de teclado em formas Unicode equivalentes são aceitos.
Todos os textos conhecidos da prévia são medidos antes da primeira imagem;
um excesso extremo pede correção do trecho específico sem comprar imagens.
Atualizações desse encaixe invalidam somente a composição local de texto,
preservando a arte já comprada e a capa explicitamente aprovada.
No miolo com leitura separada, cada página de leitura reúne dois trechos
consecutivos sem reescrever nem perder nenhum dos 16 trechos. Ao corrigir o
trecho da página ilustrada, a leitura correspondente é atualizada a partir
do fundo guardado, sem uma segunda geração de imagem.

A capa é apresentada primeiro para aprovação explícita; a prévia completa
também depende da avaliação do usuário. Integridade técnica continua sendo
verificada. Os testes usam provedores simulados e validam referências,
continuidade, aprovação e composição literal; não comprovam qualidade
artística nem equivalem a treinamento de modelo.

`book-designs-v1.json` e os três arquivos referenciados por cada modelo são
contratos imutáveis. Uma evolução visual deve criar nova versão e manter a
anterior disponível para os livros já iniciados.
