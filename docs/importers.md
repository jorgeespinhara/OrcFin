# Importadores

Registry em `core/import_parsers/registry.py`. Plugins opcionais em `plugins/import_parsers/` na pasta de dados do usuário.

## Formatos suportados

- Nubank (CSV, PDF dedicado)
- Santander e Caixa (CSV, PDF dedicado em `bank_pdf.py`)
- Inter, C6, Bradesco, Itaú (CSV)
- OFX/QFX
- PDF genérico (BTG, Itaú, Bradesco e demais bancos)
- CSV genérico com auto-detecção ou mapeador manual + template salvo (`import_templates`)

> **Filtro por país:** perfis não-BR (`US`, `ES`) exibem apenas importadores internacionais (`OFX/QFX` e `CSV genérico`), ocultando parsers específicos de bancos brasileiros.

## Fluxo

1. `parse_statement_file()` — roteador
2. `prepare_import()` — categorização + duplicatas + confiança
3. Preview na UI — editar categoria, confirmar
4. `commit_import()` — lote rastreável
5. `rollback_import_batch()` — soft-delete por lote