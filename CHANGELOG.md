# Changelog

## [Unreleased]

## [0.2.11] - 2026-07-07

### Fixed

- Empacotamento portátil Windows: build migrado de PyInstaller cru para `flet pack`, incluindo `flet-desktop` e runtime desktop do Flet (corrige `ModuleNotFoundError: flet_desktop` na release).

## [0.2.10] - 2026-07-02

### Added

- Dados fictícios de onboarding ampliados com **12 meses** de histórico para finanças pessoais e MEI.
- Demo pessoal: metas, orçamentos do mês, ativos e passivos; modo **casal** popula os dois perfis padrão.
- Demo MEI: quatro clientes, dezoito notas fiscais, DAS nos meses anteriores e módulos conforme perfil operacional (estoque, pedidos, recorrentes).
- Testes de geração do recibo PDF MEI (`tests/test_pdf_generator.py`).

### Changed

- Versão do app `0.2.10`; seed de onboarding passa a cobrir dashboards, gráficos e indicadores com volume realista.

### Fixed

- **Recibo PDF** em Notas e Clientes MEI: registra estilo itálico nas fontes embutidas (corrige `undefined font: OrcFin`).

## [0.2.9] - 2026-07-02

### Added

- Dados fictícios de onboarding para perfil MEI (cliente, NF, lançamentos e módulos por perfil operacional).
- `section_card` nas Configurações, `modal_dialog_kwargs` para modais e cache mensal de cotas CVM.
- `db_session()` para reuso de conexão SQLite; dependência `defusedxml` para XML de NF-e.
- Testes de seed MEI, estilo de modal, zip slip em backup e pilha de diálogos.

### Changed

- Versão do app `0.2.9`; dashboard reutiliza série de evolução em uma única carga.
- SegmentedButton e seções de Configurações usam bordas do tema ativo.
- Modais com borda 2px, scrim e elevação; diálogos rastreados na pilha do app.

### Fixed

- Toast do assistente inicial após dados fictícios (`_toast_text` ainda não criado).
- Botão Fechar em Configurações MEI e demais modais que dependiam de internals do Flet.
- Restore/inspect de backup rejeita paths com zip slip; UI expõe fallback fraco do keyring.

## [0.2.8] - 2026-07-02

### Added

- Perfis operacionais MEI (CNAE, cinco perfis) com navegação dinâmica por módulo.
- Pedidos e terceiros (`by_order`, `mixed`): schema v12, payables mensais e lançamento de pagamento.
- Cobrança recorrente (`recurring`): contratos, cobranças do mês e recebimento.
- Estoque leve (`sales`, `mixed`): produtos, movimentações e alerta de estoque baixo.
- Testes para perfis MEI, pedidos, recorrentes, estoque e fechamento de modais.

### Changed

- Versão do app `0.2.8`; onboarding e setup MEI incluem perfil operacional.
- `close_modal` remove diálogos da pilha Flet; Cancelar fecha só o modal atual.

### Fixed

- Botões Cancelar em modais MEI e formulários que não dispensavam o overlay.
- Import `view_from_map` em `ui/router.py`.

## [0.2.7] - 2026-07-02

### Added

- Pacote `core/ai/` com gateway modular; SDK nativo `anthropic` para Claude.
- Workflow CI (pytest + gitleaks) em push e pull request.
- Testes para fallback de IA, cache por totais e cliente por provedor.

### Changed

- Versão do app `0.2.7`; README com seções de público-alvo, fluxo prático e dados fictícios.
- `use_fallback_on_error` passa a controlar de fato o retorno (sem insight quando desligado).
- Cache de IA por período e totais agregados, em vez do texto completo do contexto.
- `response_format` JSON só para provedores que suportam; Claude fora da camada OpenAI-compat.
- `main.py` aceita `FLET_ASSETS_DIR` para builds empacotados.

### Removed

- Migração e fallbacks do nome legado FinForge (banco, backup, keyring, atalho).

## [0.2.6] - 2026-07-01

### Added

- Módulo **Investimentos**: posições (ações, FIIs, ETFs, fundos CVM, cripto), tabela de holdings, cotações e atualização automática.
- Autocomplete de tickers (B3/cripto) e corretoras no formulário de posição.
- Card **Carteira de investimentos** na Dashboard (visível só com posições cadastradas).
- Cache TTL (90s) de `get_portfolio_summary` compartilhado entre Dashboard e Investimentos.
- Validação de quantidade por classe de ativo; testes de cache e soft-delete de perfil.

### Changed

- Versão do app `0.2.6`; pacote portátil e barra de título alinhados em `core/branding.py`.
- Formulário de investimentos: debounce nas buscas, CVM/tickers em background, sem refresh duplo após salvar.
- Tela de investimentos: layout sem bloco cinza (remoção de gráficos com `expand` e cards de resumo com altura fixa).

### Fixed

- Conflito snackbar/modal no formulário de investimentos; artefato visual do overlay.
- Imports em formulário de transações, dropdown de investimentos e rebuild do executável.

## [0.2.0] - 2026-07-01

### Added

- Schema v9 com snapshots `old_value_json` / `new_value_json` na trilha local.
- Parsers PDF Santander e Caixa; plugins de importação na pasta de dados.
- Mapeador CSV com encoding e formato de data; edição de regras de categorização.
- Confirmação digitada na restauração de backup; `docs/privacy-model.md`.
- Publicação automática do pacote portátil no GitHub Release ao criar tag `v*`.

### Added (0.1.x series)

- Mapeador CSV manual com templates salvos e botão no fluxo de importação.
- Preview de backup em sandbox (`preview_backup`) com período e perfis.
- Detalhe de lançamento com origem, lote de importação e trilha local.
- Parsers CSV Santander e Caixa; detecção PDF ampliada.
- **Schema v8:** templates CSV, `change_log`, soft-delete em rollback, insights ignorados, histórico local de IA.
- Importação: confiança por linha, edição de categoria no preview, rollback sem apagar (marca `deleted_at`).
- Dashboard: ações e ignorar em decisões; central de insights; cards MEI (limite, DAS, recebíveis).
- Backup: escolher pasta, próximo backup automático, histórico em privacidade.
- MEI: seletor de mês e guia do pacote contador; exports em pasta do usuário.
- Parser registry (`core/import_parsers/registry.py`) e docs (`architecture`, `data-model`, `importers`, `release-process`).
- **Histórico de importações** com lotes rastreáveis (`import_batches`, schema v7) e botão **Desfazer** por lote.
- Tela **Privacidade e dados** em Configurações: caminhos locais, tamanho do banco, política de rede, status da IA e registro de eventos externos.
- Modo **offline estrito** (`strict_offline`) que bloqueia chamadas a provedores de IA.
- Preview do payload agregado antes de enviar análises de IA (Relatórios → Análises com IA).
- Tabela `audit_events` (schema v6) para auditoria local de testes e requisições de IA.

### Changed

- Licença GPL-3.0; versão do app `0.2.0`.
- Teste de conexão e análises de IA respeitam a política de rede e registram eventos no log local.

## [0.1.0-alpha] - 2026-07-01

### Added

- Pasta de dados do usuário fora do repositório (`C:\OrcFin` no Windows, com opção de escolher outro local no assistente inicial).
- Migração automática de bancos e configurações antigas (pasta `data/` do projeto e `%LOCALAPPDATA%\OrcFin`).
- Assistente de primeira execução: modo de uso, pasta de dados, backup, importação ou dados fictícios.
- Transações de demonstração para explorar o app sem dados reais.
- Empacotamento portátil para Windows (`scripts/package_portable.py`) e workflow de release no GitHub Actions.

### Changed

- Banco SQLite, configurações e backups padrão passam a ficar na pasta de dados do usuário.
- Janela do assistente e do app principal abrem centralizadas no monitor.

### Fixed

- Validação do banco SQLite na migração (arquivos inválidos não são copiados).
- Empacotamento PyInstaller: assets, ícones do Flet e API de alinhamento compatíveis com Flet 0.85.