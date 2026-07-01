# Modelo de dados (resumo)

## Principais tabelas

| Tabela | Uso |
|--------|-----|
| `profiles` | Perfis pessoal/MEI |
| `transactions` | Lançamentos (`import_batch_id`, `deleted_at` soft-delete) |
| `import_batches` | Lotes de importação com rollback |
| `import_templates` | Mapeamento de colunas CSV salvos |
| `categorization_rules` | Auto-categorização |
| `audit_events` | Chamadas externas (IA) |
| `change_log` | Import, backup, alterações locais |
| `dismissed_insights` | Insights ignorados no dashboard |
| `ai_analyses` | Resumos de análises IA (local) |

Detalhe completo: `core/db/schema.py` + migrations.