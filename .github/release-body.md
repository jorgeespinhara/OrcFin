## OrcFin v1.0.0

Orçamento financeiro local para **pessoal**, **casal** e **MEI** — dados no seu computador (SQLite), sem nuvem obrigatória, sem mensalidade e sem telemetria.

### Instalação no Windows

Escolha a opção que preferir (ambas já incluem Python e todas as dependências embutidas):

1. **Instalador (`OrcFin-Setup.exe`) — recomendado:** instala na pasta do usuário (não exige administrador), cria atalhos no Menu Iniciar/Área de Trabalho e desinstalador limpo.
2. **Pacote portátil (`OrcFin-portable.zip`):** extraia em qualquer pasta (sem apagar `_internal`) e execute `OrcFin.exe`.

No primeiro uso, escolha **Importar extrato**, **Explorar com dados fictícios** ou **Restaurar backup existente (`.orcfin.bak`)**.

### O que é opcional

| Recurso | Requisito |
|---------|-----------|
| Análise com IA | API key em Configurações + rede liberada (envia apenas totais agregados) |
| Cotações de investimentos | Rede (`yfinance`); pode desligar no modo offline |
| Verificar atualizações | Verificação manual no GitHub em Configurações (respeita modo offline) |
| Dados financeiros | Ficam em `C:\OrcFin` (ou pasta escolhida), **fora** do instalador/ZIP |

### Destaques da v1.0.0

- **UX/UI renovada:** barra superior limpa, botão global `+ Lançamento` (`Ctrl+N`), atalhos de teclado (`Ctrl+N`, `Ctrl+F`, `Esc`), menu lateral responsivo, alternador rápido de tema Claro/Escuro e toast discreto com ação.
- **Transações mais rápidas:** filtros por categoria, cartão e ordenação, alteração de categoria em lote, valores com alinhamento tabular e exclusão com **Desfazer (5s)**.
- **Dashboard & MEI responsivos:** grade de KPIs 2×2 / 4×1 sem quebras desiguais, vencimentos em destaque no topo e banner MEI dispensável.
- **Onboarding em 3 passos:** início rápido com opção direta de importar extrato, explorar demo ou restaurar backup `.orcfin.bak`.
- **Segurança, integridade e suporte sem telemetria:** SQLite em modo WAL com 16 novos índices (schema v15), backups WAL-safe sem vazamento temporário, contraste aprimorado no modo claro e exportação de **diagnóstico sanitizado** em Configurações → Dados.
- **Idiomas e moedas:** `pt-BR` (BRL + MEI), `en-US` (USD) e `es-ES` (EUR).

> Executáveis sem assinatura digital podem ser sinalizados pelo Windows SmartScreen. Use “Mais informações” → “Executar mesmo assim” ao baixar da release oficial deste repositório.

**Changelog completo:** https://github.com/jorgeespinhara/OrcFin/blob/main/CHANGELOG.md
