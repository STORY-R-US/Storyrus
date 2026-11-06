# Referências visuais e revisão da capa

As imagens fornecidas para capa e miolo de André no computador são referências de composição e acabamento, não treinamento de modelo nem fotografias de identidade dos clientes. Os originais não ficam em texto claro no repositório público. Os arquivos `visual-master-cover.enc` e `visual-master-page.enc` usam Fernet; a chave `EDITORIAL_VISUAL_REFERENCE_KEY` pertence ao ambiente privado do servidor. Preserve essa chave ao atualizar o serviço. Ela não deve aparecer em logs, respostas da API ou commits.

No estilo realista, a capa recebe o padrão de título no bloco superior direito e a referência de capa como última imagem. Páginas recebem a referência de miolo e a arte da capa do projeto para continuidade. As fotos originais do projeto continuam definindo a identidade. O estilo cartoon mantém suas referências próprias. A leitura da referência e a composição de texto são locais; a geração por provedor continua tendo custo.

O site solicita `cover_only: true` ao iniciar ou repetir uma prévia do Studio. O trabalho termina em `cover_ready`, entrega somente uma capa e mantém `preview_complete: false`. Não libera pagamento, pacote de três imagens nem aprovação da prévia completa. Ajustar a capa nessa etapa continua gerando apenas a capa.

O botão de aprovação envia `approved_cover_sha256` da capa atual. O servidor verifica o contexto e os bytes da capa e reutiliza a arte exata, sem gerar outra capa. Somente então gera o restante da prévia, que ainda exige aprovação explícita antes da compra. Alterações de identidade, título ou padrão visual invalidam a continuação antiga.

Os testes substituem os provedores por respostas locais. Nenhuma imagem real é gerada por esses testes; qualidade visual e semelhança continuam dependendo da avaliação do usuário.

## Padrões do Catálogo

A ferramenta também utiliza nove imagens que já são públicas no Catálogo oficial, copiadas sem alteração de `apps/web/public/exemplos/`. Os conjuntos Amor de Bisavó, Meu Pai Meu Herói e Amor de Mãe cartoon fornecem exemplos de capa, miolo e apresentação segurando o livro. O tema e o estilo selecionam a família de referência; o exemplo de André permanece para histórias de computador. Nenhum rosto ou texto do exemplo deve substituir o material do cliente. Isso é orientação por referências, não treinamento do modelo.

O posicionamento do texto interno usa detecção local de rostos com margem para cabelos e gorros e procura outra área quando há sobreposição. O detector é uma ajuda de composição: não garante localizar todas as pessoas ou animais, nem julga a qualidade artística. A decisão continua com o usuário. A renderização mantém o texto literal e o tamanho da fonte. O acabamento da lombada deriva das cores da capa; somente a apresentação recebe vinco e sombra, preservando a arte plana para impressão.
