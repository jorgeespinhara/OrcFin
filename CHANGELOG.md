# Changelog

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