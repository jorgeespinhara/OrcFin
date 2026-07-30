## OrcFin v0.2.13

Orçamento financeiro local para **pessoal**, **casal** e **MEI** — dados no seu computador, sem nuvem para cadastro ou relatórios.

### Pacote portátil (Windows)

O arquivo **`OrcFin-portable.zip`** já inclui o runtime Python e **todas as dependências de execução** (Flet/desktop, SQLite, Pydantic, PDF, importação OFX/PDF, criptografia, SDKs de IA, etc.) embutidas via `flet pack`.

**Você NÃO precisa instalar Python, pip nem bibliotecas manualmente.**

1. Baixe `OrcFin-portable.zip` abaixo.
2. Extraia a pasta em qualquer local (**não apague** a pasta `_internal`).
3. Execute `OrcFin.exe`.
4. Confira na barra de título: **OrcFin v0.2.13**.
5. No primeiro uso, escolha **Começar com dados fictícios** se quiser explorar com exemplos.

Leia também o `LEIA-ME.txt` dentro do ZIP (lista o que vem embutido).

### O que ainda é opcional (não vem “instalado” no sentido de conta)

| Recurso | Requisito |
|---------|-----------|
| Análise com IA | API key em Configurações + rede liberada |
| Cotações de investimentos | Rede (yfinance); pode desligar no modo offline |
| Dados financeiros | Ficam em `C:\OrcFin` (ou pasta escolhida), **fora** do ZIP |

### Destaques desta versão

- Dashboard com KPIs acionáveis, *quanto posso gastar* em destaque e empty states com CTA.
- Relatórios & IA reorganizados: resumo → IA → gráficos; export PDF/CSV; simulador com presets; disclaimer de IA.
- Correção do painel cinza vazio em Relatórios.

> Executáveis sem assinatura digital podem ser sinalizados pelo SmartScreen. Use “Mais informações” → “Executar mesmo assim” se confiar na origem (release oficial deste repositório).

**Changelog completo:** https://github.com/jorgeespinhara/OrcFin/blob/main/CHANGELOG.md
