# Arquitetura OrcFin (v1.0.0 PRO)

Aplicativo desktop **local-first**: interface moderna em **React 19 + TypeScript + Tailwind v4 + Recharts + Framer Motion** rodando em janela nativa **WebView2** (`pywebview`), comunicando-se via HTTP local (`127.0.0.1`, porta efêmera) com uma API **FastAPI** em thread interna sobre o motor Python + **SQLite (WAL)**.

## Camadas

- `desktop.py` / `main.py` — launcher nativo `pywebview` (WebView2 no Windows) que sobe o servidor local e abre a janela desktop (`--legacy` mantém fallback opcional)
- `frontend/` — SPA React 19 + TypeScript + Tailwind v4 + Framer Motion + Recharts (`Dashboard`, `Transactions`, `Import`, `Cards`, `Investments`, `Reports & AI`, `MEI`, `Settings`, `Onboarding`, `CommandPalette Ctrl+K`)
- `api/` — camada HTTP local FastAPI (`server.py`, `routes_personal.py`, `routes_mei.py`) servindo a API e o bundle estático `frontend/dist`
- `core/services/` — fluxos de negócio (importação, cartões, portfólio/cotações, MEI)
- `core/engine/` — regras locais (orçamento, insights, decisões, cenários, portfólio, sazonalidade, recorrências)
- `core/db/` — schema, migrations, repositórios e queries agregadas
- `core/ai/` — provedores, cliente HTTP, parser, cache e fallback local (reexportado via `core/ai_gateway.py`)
- `core/i18n/` — catálogos `pt-BR`, `en-US`, `es-ES` e perfis de país/moeda
- `core/import_parsers/` — parsers por banco/formato (`OFX`, `CSV`, `PDF`, `NF-e XML`) + registry
- `core/integrations/` — cotações opcionais (`yfinance`, registro B3, CVM)
- `core/diagnostics.py` & `core/update_check.py` — diagnóstico sanitizado sem telemetria e checagem manual de versão no GitHub Releases

## Persistência

Migrations incrementais via `PRAGMA user_version` (`core/db/migrations.py`), SQLite em modo **WAL** com `busy_timeout`. Schema atual: ver `SCHEMA_VERSION` (`15`) em `core/db/connection.py`.

## Privacidade

IA, cotações e verificação de atualizações passam por `core/network_policy.py` (bloqueáveis pelo modo **Offline Estrito**). A IA recebe apenas totais agregados, nunca linhas individuais de lançamento ou PII. Eventos externos em `audit_events`; alterações locais em `change_log`.
