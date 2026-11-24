# Modelo de dados (resumo)

Schema versionado via `PRAGMA user_version` (atual: ver `SCHEMA_VERSION` em `core/db/connection.py`).

## Principais tabelas

| Tabela | Uso |
|--------|-----|
| `profiles` | Perfis pessoal e MEI |
| `categories` | Categorias com `slug` estável e flag `is_mei_deductible` |
| `transactions` | Lançamentos (`import_batch_id`, `credit_card_id`, `mei_client_id`, `deleted_at`) |
| `budgets` | Limites mensais por categoria/perfil |
| `goals` | Metas financeiras |
| `credit_cards` | Cartões de crédito e fechamento/vencimento |
| `assets`, `liabilities`, `net_worth_snapshots` | Patrimônio líquido e histórico |
| `investment_holdings`, `investment_quotes`, `investment_snapshots` | Carteira de investimentos e cotações em cache |
| `mei_config`, `mei_clients`, `mei_invoices` | Configuração MEI, clientes e notas fiscais |
| `mei_suppliers`, `mei_orders`, `mei_order_outsource` | Pedidos sob encomenda e terceirização MEI |
| `mei_subscriptions`, `mei_subscription_charges` | Cobranças recorrentes MEI |
| `mei_products`, `mei_stock_movements` | Estoque leve MEI |
| `import_batches`, `import_templates` | Lotes de importação com rollback e templates CSV |
| `categorization_rules` | Regras de auto-categorização |
| `audit_events`, `change_log` | Auditoria de chamadas externas (IA) e alterações locais |
| `dismissed_insights`, `ai_analyses` | Insights ignorados e histórico local de análises IA |

Detalhe completo: `core/db/schema.py` + `core/db/migrations.py`.
