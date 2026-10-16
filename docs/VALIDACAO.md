# Validação da base inicial

Verificação local concluída em 15/10/2026.

| Área | Verificação | Resultado |
| --- | --- | --- |
| Backend | Ruff e formatação | Aprovados |
| Backend | Pytest | 429 testes aprovados |
| Backend | Cobertura de código | 80,01 por cento, acima do mínimo de 70 |
| Web | ESLint e TypeScript | Aprovados |
| Web | Vitest | 207 testes aprovados em 21 arquivos |
| Web | Build de produção | Aprovado |
| Web | Playwright | 10 testes de navegador aprovados |
| Mobile | TypeScript | Aprovado |
| Mobile | Testes de regressão | 12 testes aprovados |

Os testes foram executados nesta pasta com Python 3.14 e Node.js 24.15.
Os testes de navegador usaram a aplicação local na porta 5196 e APIs simuladas.
Nenhuma geração paga ou implantação em produção foi realizada por essas verificações.

Durante a consolidação, o teste de formulário foi atualizado para o título
opcional já suportado pela aplicação. As capturas dos testes do perfil mestre
passaram a usar a pasta de resultados de cada teste, sem caminhos para outros trabalhos.

As dependências instaladas e os resultados brutos dos testes ficam fora do ZIP.
Os comandos de reprodução estão no README e na configuração de CI.
