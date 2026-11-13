# Fluxo editorial integrado

Novos projetos congelam scene_workflow=integrated-v1 antes da primeira imagem.
Capa, prévia do livro aberto, páginas para impressão e livro segurado usam a
composição integrada de arte, pessoas, cenário e texto literal. A prévia completa
usa três imagens: capa, livro aberto e leitura. Não compra duas páginas separadas
para depois montar o livro aberto.

As fotos originais definem identidade. A capa final define continuidade nas cenas
seguintes; o exemplar do Catálogo define acabamento e layout, nunca as pessoas ou
os nomes. A prévia respeita o layout próprio do exemplar, incluindo modelos com
uma página de leitura e outra de ilustração. O livro completo preserva todos os
versos uma vez nas páginas correspondentes. O PDF usa as páginas finais planas;
não recorta páginas da fotografia do livro aberto nem reaplica texto por cima de
uma imagem que já contém letras. Não apresenta essas páginas como “sem texto”.

Na leitura, pessoa, ambiente, mãos e capa impressa nascem na mesma fotografia.
Não há superfície rosa, localização de quadrilátero ou colagem posterior. Pessoas
externas permanecem fotográficas mesmo nos livros Cartoon. A capa plana para
impressão recebe apenas a apresentação física local na primeira imagem da prévia.

Todas as novas cenas passam por revisão obrigatória de texto literal, identidade,
anatomia, proporções, continuidade do cenário e sobreposição de letras. A revisão
considera o layout específico do Catálogo. A imagem é salva antes dessa revisão;
reprovação não causa regeneração automática e não publica conteúdo de contingência.
Retomadas reaproveitam a mesma imagem; resultado desconhecido bloqueia recompra.

Projetos com artes salvas, etapas antigas iniciadas ou resultado desconhecido
mantêm o caminho anterior. Uma atualização não migra nem regenera imagens pagas.
A cena de leitura integrada também pode ser usada em projetos anteriores quando
nenhum template antigo foi comprado/iniciado. Pedidos, pagamentos e exigência de
aprovação da prévia continuam no fluxo existente.

Testes usam fornecedores simulados e bloqueiam chamadas reais à OpenAI. Cobrem
três idiomas, múltiplas fotos, modelos família/aventura/Cartoon, prévia completa,
páginas de impressão, reprovação, retomada e proteção de projetos antigos.
Não demonstram equivalência estética nem ausência absoluta de falhas: o modelo
de imagem do chat não é exposto, e a qualidade visual real requer a avaliação de
uma criação real autorizada. Esta publicação não inclui gerações pagas de teste.


## Fidelidade de imagem — novembro de 2026

Novas chamadas usam `gpt-image-2.6-sunburst`, qualidade `high` e complexidade
`high`. As fotos originais seguem sem reamostragem e antes das referências de
capa e Catálogo. O parâmetro legado `input_fidelity` permanece restrito aos
modelos 1/1.5; não há troca automática de modelo após falha. Configurar também
`OPENAI_IMAGE_MODEL=gpt-image-2.6-sunburst` no serviço existente do Render,
pois a variável explícita prevalece sobre o padrão do código.

O contrato editorial mantém a letra arredondada sem serifa do padrão Meu Pai,
Meu Herói, respeitando a tipografia própria de cada modelo escolhido. O tema
não escolhe outra fonte. Na leitura, a capa inteira pertence somente à frente;
contracapa em material complementar separado e lombada sem repetição da arte.
A revisão obrigatória verifica identidade, letras e distribuição entre faces.

Nenhuma versão de cache foi alterada: imagens compradas continuam reutilizáveis.
Esta mudança não regenera livros anteriores. Testes simulados verificam chamadas,
referências e retomadas; não comprovam equivalência visual com o chat nem identidade
perfeita. Uma comparação visual com o modelo novo exige geração real autorizada.
O modelo interno do chat não é conhecido; não se afirma que seja o mesmo.

Referências técnicas verificadas:
- https://developers.openai.com/api/docs/models/gpt-image-2.6-sunburst
- https://developers.openai.com/api/docs/guides/image-generation#gpt-image-26

## Validação do caminho do Estúdio sem gerar imagens

`test_studio_preview_reaches_image_transport_and_resumes_without_repurchase`
percorre as rotas HTTP de prévia, o worker, o provedor OpenAI real até o limite
HTTP simulado, armazenamento, ZIP e aprovação. Confere JPEG original intacto,
modelo/qualidade/complexidade, contrato de letra e capa em uma única face,
referência exata da capa nas cenas seguintes e bytes intactos do miolo/leitura
no ZIP. Exercita sucesso, reprovação visual e resposta de imagem desconhecida.
Retomar não faz outra chamada de imagem nem adiciona custo ao novo trabalho;
resultado desconhecido mantém o pacote e a aprovação bloqueados.

Para repetir localmente com imagens já compradas, definir
`STORYRUS_LOCAL_REPLAY_DIR` para uma pasta contendo `api-capa.png`,
`api-miolo.png`, `api-leitura.png` e executar esse teste. As imagens não são
versionadas e toda resposta de imagem/texto permanece simulada: nenhuma chamada
paga é feita. Isso verifica preservação e integração, não mede a qualidade de uma
nova geração nem a acurácia do revisor visual. A navegação do Estúdio e do Catálogo
permanece coberta pela suíte Playwright do GitHub.


## Falhas internas e revisão da leitura

Falhas editoriais, de enquadramento e resultados incertos permanecem nos registros
operacionais. O trabalho recebe `internal_resolution` sem autorização para gerar
outra imagem automaticamente. O Estúdio mostra revisão interna, remove o relatório
técnico e as ações de corrigir texto/repetir criação, e continua consultando o
projeto para apresentar o resultado quando a equipe concluir a recuperação.
Isso não é uma promessa de reparo automático de toda falha: a inspeção de arte
reprovada continua necessária, e nenhuma arte inválida é aprovada para esconder
um erro. Pagamento e aprovação do cliente permanecem obrigatórios.

A revisão da cena de leitura distingue a frente impressa da contracapa lisa.
Pessoa externa mais retrato na capa é a composição esperada; só reprovar como
capa atravessada quando arte/letras realmente continuarem além da lombada.

A assinatura do pacote editorial agora ordena caminhos de forma igual no Windows
e no servidor, preservando os bytes originais. Assinaturas antigas da ordenação
Windows continuam verificadas contra o mesmo pacote, sem alterar o perfil salvo
ou invalidar artes já pagas. O teste de recuperação percorre também a passagem de
revisão interna para resultado concluído sem disparar criação pelo navegador.
