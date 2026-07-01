# Arquitetura OrcFin

Desktop Python/Flet, SQLite local, dados em pasta do usuário (`C:\OrcFin` no Windows).

## Camadas

- `ui/` — telas Flet (dashboard, lançamentos, configurações, MEI)
- `core/services/` — fluxos (importação, cartões, MEI)
- `core/engine/` — regras locais (orçamento, insights, decisões)
- `core/db/` — schema, migrations, repositórios, queries agregadas
- `core/import_parsers/` — parsers por banco/formato + registry

## Persistência

Migrations incrementais via `PRAGMA user_version` (`core/db/migrations.py`). Schema atual: ver `SCHEMA_VERSION` em `core/db/connection.py`.

## Privacidade

IA e rede passam por `core/ai_gateway.py` e `core/network_policy.py`. Eventos externos em `audit_events`; alterações locais em `change_log`.