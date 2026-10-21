# Validação da base com fluxo de impressão

Verificação local concluída em 16/10/2026.

| Área | Verificação | Resultado |
| --- | --- | --- |
| Backend | Ruff e formatação | Aprovados |
| Backend | Pytest | 438 testes aprovados |
| Backend | Cobertura de código | 79,95 por cento, acima do mínimo de 70 |
| Banco | Cabeça das migrações | 0027_purchase_flow, única revisão final |
| Web | ESLint e TypeScript | Aprovados |
| Web | Vitest | 210 testes aprovados em 22 arquivos |
| Web | Build de produção | Aprovado |
| Web | Playwright | 12 testes de navegador aprovados |
| Mobile | TypeScript | Aprovado |
| Mobile | Testes de regressão | 12 testes aprovados |

Os testes foram executados nesta pasta com Python 3.14 e Node.js 24.15.
Os testes de navegador usaram o build de produção local na porta 5197, um worker
e APIs simuladas, com `playwright.export.config.ts`.
Nenhuma geração paga ou implantação em produção foi realizada por essas verificações.

A suíte cobre a prévia, aprovação, cotação persistente, acompanhamento do pedido,
controle de acesso, geração após pagamento e autorização final de impressão.
O pagamento real e a integração com a gráfica dependem das configurações descritas
em `FLUXO_IMPRESSAO.md`.

As dependências instaladas e os resultados brutos dos testes ficam fora do ZIP.
Os comandos de reprodução estão no README e na configuração de CI.
