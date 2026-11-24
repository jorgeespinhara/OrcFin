# Primeiros passos

## Assistente de primeira execução (3 passos)

Na primeira abertura (ou após reset), o OrcFin exibe um assistente rápido em **3 passos**:

| Passo | Conteúdo |
|---|---|
| **1. País, idioma e moeda** | `BR` (`pt-BR · R$ + MEI`), `US` (`en-US · $`) ou `ES` (`es-ES · €`) |
| **2. Modo de uso** | Finanças Pessoais / Casal, **Pessoal + MEI** ou **Somente MEI** (perfil Brasil) |
| **3. Começar agora** | **Importar extrato** (`OFX`/`CSV`/`PDF`), **Explorar com dados de exemplo** ou **Restaurar backup `.orcfin.bak`**, além da opção de **Backup automático ao fechar** |

## Atalhos de produtividade

- **`Ctrl+K`** — Paleta de Comandos (navegar entre módulos, criar lançamento, alternar tema ou carregar demo)
- **`Ctrl+N`** — Novo lançamento de qualquer tela
- **`Ctrl+F`** — Ir direto para a busca de Transações
- **`Esc`** — Fechar modal ativo

## Importar o primeiro extrato

1. Abra **Importar** no menu lateral (ou via `Ctrl+K`).
2. Arraste seu arquivo **`OFX`**, **`CSV`** ou **`PDF`** (Nubank, Inter, C6, Itaú, Bradesco, genérico) para a área de upload.
3. Revise o preview (duplicatas já vêm desmarcadas automaticamente), ajuste categorias se quiser e clique em **Confirmar importação**.

Todo o processamento ocorre localmente na sua máquina.

## Transações com segurança (Desfazer 5s)

- Filtre por texto, tipo (`Todos / Receitas / Despesas`), **Categoria**, **Cartão** e **Ordenação**.
- Selecione vários lançamentos para **Alterar categoria em lote** ou excluir em lote.
- Ao excluir um lançamento individual, um toast oferece **Desfazer** por 5 segundos antes de sair da tela.

## Backup, Diagnóstico e Atualizações

- **Configurações → Dados, Privacidade & IA:** crie backups criptografados `.orcfin.bak`, exporte em CSV/JSON, gere um **diagnóstico sanitizado `.txt`** para suporte (sem dados financeiros/PII) ou verifique manualmente se há nova versão no GitHub.

Mais detalhes: [Instalação no Windows](install-windows.md).
