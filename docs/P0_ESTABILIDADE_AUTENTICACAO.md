# P0 — estabilidade e autenticação

Escopo recuperado em 13/11/2026 da revisão compartilhada:
https://chatgpt.com/share/e/6af71796-4ff8-83ea-a399-e18b24a34777

1. Comprovar geração/exportação e retomada sem perder resultados ou repetir custos.
2. Preparar autenticação de produção, preservar contas/projetos e isolar clientes.

## Correções desta etapa

- Sessão encerrada ou indisponível no Clerk deixa de reutilizar o Bearer anterior.
  Respostas atrasadas de login não restauram a conta após logout ou troca de acesso.
  O token persistido também é removido nesses casos.
- Vinculação por email de uma conta local existente exige email verificado no Clerk.
  Outro Clerk ID não substitui uma vinculação existente. `users.id`, projetos,
  pedidos e créditos permanecem com a mesma conta local.
- A validação RS256 exige expiração e rejeita sessões `pending`.
- O ZIP da prévia é montado em arquivo temporário e transmitido em blocos de 64 KiB.
  Não mantém uma cópia completa do pacote na memória nem recomprime PNGs.
  O arquivo temporário é fechado em sucesso, erro e término da transmissão.
- A exportação do miolo processa as páginas sequencialmente e libera imagens
  decodificadas; deixa de guardar todas as páginas redimensionadas em PNG ao mesmo tempo.

## Evidências sem chamadas pagas

Teste local em processos separados, com a implementação anterior do mesmo `main`
e a implementação corrigida, 16 imagens sintéticas de ruído em 1024 × 1024,
miolo de 20 cm mais dedicatória, renderização em 2480 × 2480 e amostragem do RSS
a cada 10 ms:

| Implementação | Pico RSS | Páginas do PDF | Bytes do PDF |
|---|---:|---:|---:|
| Anterior | 386,7 MiB | 17 | 25.099.377 |
| Corrigida | 293,0 MiB | 17 | 25.099.377 |

Redução de aproximadamente 24%. É um cenário sintético local, não uma prova de
capacidade para qualquer imagem ou concorrência em uma instância de 512 MiB.

O teste `test_preview_export_retry_and_other_customer_isolation` interrompe a
leitura do armazenamento durante a exportação, repete o download e verifica ZIP,
fechamento dos temporários, bytes originais preservados, mesmo custo e nenhuma
chamada adicional de imagem. Outra conta recebe 404 no projeto, ZIP e job.

Os testes existentes de `test_request_journal.py`, `test_workers.py` e
`test_master_book.py` cobrem interrupção após recebimento pago, reaproveitamento
no mesmo/novo job, armazenamento temporariamente indisponível, resposta desconhecida,
prévia entregue e bloqueio de recompra quando não é possível confirmar o resultado.
Resposta desconhecida continua sem autorização para comprar outra geração.

Em produção, o deploy `dep-dbrhbbmtlv9c738hkej0` estava `live` no commit
`96cc09a35585bdaa077c22f774ea351a3f3f3d8d` antes desta alteração. Na amostra de
13:52–14:12 UTC de 13/11, a instância nova estava perto de 102 MiB e não havia
respostas 502 nas séries retornadas. Houve pouco tráfego: isso não comprova
estabilidade sob carga nem invalida os incidentes anteriores.

## Corte do Clerk: pendência externa, ainda não concluída

Em 13/11/2026, as consultas CNAME para `clerk.storyrus.ai` e
`accounts.storyrus.ai` retornaram nome inexistente. Os registros de preparação
local de 12/11 também identificam OAuth próprio de Google/Microsoft e preservação
do acesso das contas atuais como pendências. Não foram trocadas chaves nem contas.

Para concluir o corte:

1. O administrador DNS cadastra os CNAMEs exatos exibidos na instância de produção
   do Clerk, preservando os registros atuais. Validar domínio, SSL e email no Clerk.
2. Configurar OAuth próprio de Google/Microsoft e os redirecionamentos web/mobile.
3. Definir o acesso das contas existentes na nova instância. Não basta substituir
   `sk_test`/`pk_test` por chaves `live`: os IDs de usuários são diferentes entre
   instâncias. O Clerk não oferece transferência direta de development para production.
4. Preparar e revisar o mapeamento explícito entre as identidades antigas e novas
   e os mesmos UUIDs locais. Conferir titularidade nas duas instâncias, manter
   livros/pedidos/créditos e resolver a conta com senha antes do corte. Não liberar
   reatribuição automática de uma conta já vinculada apenas por coincidência de email.
5. Atualizar conjuntamente as chaves do site/API/mobile e o segredo do webhook,
   com um plano de retorno que preserve o banco. Não alterar a base de produção.
6. Validar sessão real, renovação, logout, nova entrada, senha/código, Google,
   Microsoft e dois clientes comuns acessando somente seus próprios arquivos.
7. Repetir a verificação operacional de geração/exportação com os resultados
   salvos, acompanhando memória, saúde e retomada. Testes automatizados usam
   provedores simulados; não autorizam gerações pagas de homologação.

O P0 de autenticação permanece aberto até concluir essas dependências e a
validação real após o corte. As correções de código não substituem essa etapa.

Referências oficiais verificadas:
- https://clerk.com/docs/guides/development/deployment/production
- https://clerk.com/docs/guides/development/migrating/overview
- https://clerk.com/docs/guides/sessions/session-tokens
