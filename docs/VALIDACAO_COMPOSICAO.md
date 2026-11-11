# Composição segura do livro

## Contrato

A arte recebida do provedor é salva antes da revisão e continua privada. O texto
literal é composto localmente com as fontes verificadas do projeto. Cada linha
tem sua própria área de tinta com margem: o retângulo que envolve o título todo
não transforma o espaço vazio ao lado de uma linha curta em texto.

Uma invasão da área de leitura permite um único mapeamento da **cena inteira já
recebida**. Esse mapa deve incluir cabeças completas, cabelo, gorros, mãos e ação
importante. As coordenadas são verificadas, recebem margem adicional e alimentam
uma busca local de áreas livres, inclusive áreas derivadas das bordas dos objetos.
Todo candidato passa por conferência das linhas e revisão visual da capa. Caixas
da visão são estimativas; a verificação visual final continua obrigatória.

O detector local de rostos auxilia a ordenação. Ele não prova ausência de cabelo
ou gorro e não substitui a revisão. A composição mantém todos os pixels da cena
fora das letras e de seus contornos. Não há extensão desfocada, faixa, geração de
contingência nem nova compra automática de ilustração para corrigir o título.

O mapa fica associado à arte, texto, política e revisão do compositor. Se o mesmo
pedido esgotar as posições revisadas, o diagnóstico salvo interrompe a repetição
antes de novas chamadas pagas. Texto ou arte alterados permitem uma nova análise.
Uma revisão de identidade, anatomia ou acabamento nunca é reinterpretada como um
problema de posicionamento apenas por conter palavras como “rosto” ou “título”.

Alterar o título também verifica as novas áreas de tinta sobre a arte em cache.
Uma região aprovada para o texto anterior não aprova automaticamente um título
mais longo. O ajuste mantém a mesma ilustração e suas áreas protegidas.

## Falhas e verificações

| Classe | Tratamento / evidência |
| --- | --- |
| Rosto, cabelo e gorro no título | Áreas protegidas, margem e interseção por linha; cenários com gorros desenhados localmente e detector de rosto ausente. |
| Sem espaço seguro | Falha `BOOK_LAYOUT_UNSAFE`, arte retida e bloqueio da repetição idêntica; não aprova uma capa obstruída. |
| Texto longo, vazio ou símbolos inválidos | Preflight antes da compra da primeira arte; mantém os limites de leitura e o texto literal. |
| Texto errado, extra, duplicado ou cortado | Camada literal local, fonte verificada e revisão obrigatória da arte/capa; aprovação humana permanece separada. |
| Contraste insuficiente | Mede o fundo sob as letras e escolhe entre a cor prevista, azul escuro e creme; não altera o cenário. Revisão visual permanece obrigatória. |
| Identidade, idade, anatomia e figurino | Revisão com as fotos originais e continuidade do projeto; falha concreta bloqueia a etapa. |
| Elenco, ação, objetos ou acabamento incorretos | Contrato de cena e revisão da arte inteira; não permite reparo tipográfico contornar essas reprovações. |
| Mockup ou geometria inválidos | Validação de superfícies, oclusões e proveniência; montagem usa a capa e páginas reais do projeto. |
| Arquivo inválido, proporção ou tamanho inadequados | Validação antes da revisão; JPEG/WEBP válidos viram PNG sem alterar os pixels decodificados. |
| Arquivo salvo ausente ou corrompido | Integridade verificada, etapa bloqueada e mensagem de recuperação; não compra uma substituição automaticamente. |
| Revisão malformada, contraditória ou inconclusiva | JSON e tipos estritos; resposta positiva com defeitos nunca aprova a imagem. |
| Provedor indisponível, limite ou autorização inválida | Erros continuam visíveis e não viram conteúdo simulado; testes dos transportes existentes cobrem as respostas e o retry seguro. |
| Resultado pago incerto | Diário persistente conserva IDs e bloqueia repetição de resultado desconhecido. |
| Fotos sem autorização ou limite de gastos | Guardas anteriores às chamadas e ao armazenamento continuam obrigatórias. |
| Aprovação antiga ou pagamento pendente | Hash/contexto da capa e aprovações explícitas do servidor continuam exigidos. |

## Validação sem custo de geração

- `test_editorial_geometry_contract.py`: áreas adversas, gorro completo, espaços
  entre linhas, preservação dos pixels, contraste, formatos e revisão estrita.
- `test_master_book.py`: reparo e retomada, mapa salvo, bloqueio da repetição,
  isolamento de contexto, integridade, aprovação e livro completo.
- `test_text_openai.py`: recortes exatos por linha, geometria rejeitada antes de
  qualquer HTTP pago e contrato do planejador da cena inteira.
- `generationError.test.ts`: mensagens de falha em PT/EN/ES e prioridade do bloqueio
  de resultado incerto.
- `title-layout-failure.spec.ts`: recarrega o projeto com falha salva sem disparar
  geração automaticamente. Demais E2E cobrem Estúdio, Catálogo e aprovações.

Os testes usam imagens locais e transportes simulados. A suíte bloqueia HTTP real
para a OpenAI; E2E usa a fixture que bloqueia serviços externos e chamadas de API
nativas não simuladas. Isso valida as regras do software sem comprar imagens.
Falhas externas e a qualidade semântica de uma futura geração continuam sujeitas
às verificações do provedor, à revisão visual e à aprovação explícita do usuário.
