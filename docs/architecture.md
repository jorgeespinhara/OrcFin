# Arquitetura OrcFin

Desktop Python/Flet, SQLite local (WAL), dados em pasta do usuário (`C:\OrcFin` no Windows).

## Camadas

- `ui/` — telas Flet (`dashboard/`, `transactions/`, `credit_cards.py`, `investments/`, `reports/`, `settings/`, `onboarding/`, `mei/`, `personal/`)
- `core/services/` — fluxos de negócio (importação, cartões, portfólio/cotações, MEI)
- `core/engine/` — regras locais (orçamento, insights, decisões, cenários, portfólio, sazonalidade)
- `core/db/` — schema, migrations, repositórios e queries agregadas
- `core/ai/` — provedores, cliente HTTP, parser, cache e fallback local (reexportado via `core/ai_gateway.py`)
- `core/i18n/` — catálogos `pt-BR`, `en-US`, `es-ES` e perfis de país/moeda
- `core/import_parsers/` — parsers por banco/formato + registry
- `core/integrations/` — cotações opcionais (`yfinance`, registro B3, CVM)

## Persistência

Migrations incrementais via `PRAGMA user_version` (`core/db/migrations.py`). Schema atual: ver `SCHEMA_VERSION` em `core/db/connection.py`.

## Privacidade

IA e rede passam por `core/ai/` (`core/ai_gateway.py`) e `core/network_policy.py`. A IA recebe apenas totais agregados, nunca linhas individuais de lançamento. Eventos externos em `audit_events`; alterações locais em `change_log`.
