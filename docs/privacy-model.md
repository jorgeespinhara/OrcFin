# Modelo de privacidade

O OrcFin é **local-first**: funções essenciais operam sem internet.

## Dados no dispositivo

| Dado | Local padrão (Windows) |
|------|-------------------------|
| Banco SQLite | `C:\OrcFin\data\orcfin.db` |
| Preferências | `C:\OrcFin\config\settings.json` |
| Backups | `C:\OrcFin\backups\` |
| Plugins de importação | `C:\OrcFin\plugins\import_parsers\` |
| Chaves de API | Criptografadas em settings + keyring do SO |

## Processamento local

- Extratos (CSV, OFX, PDF) são parseados no dispositivo.
- Descrições, valores e dados MEI não são enviados por padrão.
- Backups são criptografados antes de gravar em disco.

## Integração opcional com IA

- Apenas totais agregados do período podem ser enviados.
- Preview obrigatório antes de cada requisição.
- Modo offline estrito bloqueia chamadas externas.
- Eventos de rede ficam em `audit_events`; alterações locais em `change_log`.

## Portabilidade e exclusão

- Exportação CSV/JSON nas configurações.
- Restauração guiada a partir de backup `.orcfin.bak`.
- Zona de perigo para reset financeiro ou instalação limpa.

Guia do usuário: [privacy.md](privacy.md).