# Importadores

Registry em `core/import_parsers/registry.py`.

## Formatos suportados

- Nubank (CSV, PDF)
- Inter, C6, Bradesco, Itaú (CSV)
- OFX/QFX
- CSV genérico com auto-detecção ou template salvo (`import_templates`)

## Fluxo

1. `parse_statement_file()` — roteador
2. `prepare_import()` — categorização + duplicatas + confiança
3. Preview na UI — editar categoria, confirmar
4. `commit_import()` — lote rastreável
5. `rollback_import_batch()` — soft-delete por lote