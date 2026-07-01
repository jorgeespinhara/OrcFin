# Changelog

## [Unreleased]

### Added

- **Histórico de importações** com lotes rastreáveis (`import_batches`, schema v7) e botão **Desfazer** por lote.
- Tela **Privacidade e dados** em Configurações: caminhos locais, tamanho do banco, política de rede, status da IA e registro de eventos externos.
- Modo **offline estrito** (`strict_offline`) que bloqueia chamadas a provedores de IA.
- Preview do payload agregado antes de enviar análises de IA (Relatórios → Análises com IA).
- Tabela `audit_events` (schema v6) para auditoria local de testes e requisições de IA.

### Changed

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