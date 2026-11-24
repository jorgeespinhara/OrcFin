import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  CheckSquare,
  CreditCard as CardIcon,
  Pencil,
  Plus,
  Search,
  Square,
  Tag,
  Trash2,
  X,
} from "lucide-react";
import type {
  Category,
  CreditCard,
  TransactionItem,
  TransactionsResponse,
} from "../lib/api";
import { formatDateGroup, formatMoney } from "../lib/format";
import { Modal } from "../components/Modal";

interface TransactionsViewProps {
  data: TransactionsResponse | null;
  loading: boolean;
  currency: string;
  locale: string;
  consolidated: boolean;
  categories: Category[];
  cards: CreditCard[];
  query: string;
  onQueryChange: (q: string) => void;
  typeFilter: "all" | "income" | "expense";
  onTypeFilterChange: (v: "all" | "income" | "expense") => void;
  categoryFilter: number | null;
  onCategoryFilterChange: (id: number | null) => void;
  cardFilter: number | null;
  onCardFilterChange: (id: number | null) => void;
  sortOrder: "date_desc" | "date_asc" | "amount_desc" | "amount_asc";
  onSortOrderChange: (v: "date_desc" | "date_asc" | "amount_desc" | "amount_asc") => void;
  onNewTransaction: () => void;
  onEditTransaction: (tx: TransactionItem) => void;
  onSoftDeleteOne: (tx: TransactionItem) => void;
  onBatchCategory: (ids: number[], categoryId: number) => Promise<void>;
  onBatchDelete: (ids: number[]) => Promise<void>;
}

export function TransactionsView({
  data,
  loading,
  currency,
  locale,
  consolidated,
  categories,
  cards,
  query,
  onQueryChange,
  typeFilter,
  onTypeFilterChange,
  categoryFilter,
  onCategoryFilterChange,
  cardFilter,
  onCardFilterChange,
  sortOrder,
  onSortOrderChange,
  onNewTransaction,
  onEditTransaction,
  onSoftDeleteOne,
  onBatchCategory,
  onBatchDelete,
}: TransactionsViewProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [batchCatOpen, setBatchCatOpen] = useState(false);
  const [targetCatId, setTargetCatId] = useState<number>(categories[0]?.id || 1);

  const items = data?.items || [];
  const totals = data?.totals || { income: 0, expense: 0, net: 0, count: 0 };

  const grouped = useMemo(() => {
    const map = new Map<string, TransactionItem[]>();
    for (const tx of items) {
      const list = map.get(tx.date) || [];
      list.push(tx);
      map.set(tx.date, list);
    }
    return Array.from(map.entries());
  }, [items]);

  const toggleOne = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === items.length && items.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.id)));
    }
  };

  const selectedIds = Array.from(selected);

  return (
    <div className="space-y-4">
      {/* Filter Toolbar */}
      <div className="surface-card space-y-3 rounded-2xl p-4">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Buscar por descrição, nota ou categoria..."
              className="input-pro w-full py-2 pr-8 pl-10 text-sm"
            />
            {query && (
              <button
                type="button"
                onClick={() => onQueryChange("")}
                aria-label="Limpar busca"
                className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded p-0.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={onNewTransaction}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 transition hover:brightness-110"
          >
            <Plus className="h-3.5 w-3.5" />
            Novo lançamento
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-0.5">
            {(
              [
                ["all", "Todos"],
                ["income", "Receitas"],
                ["expense", "Despesas"],
              ] as const
            ).map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => onTypeFilterChange(val)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  typeFilter === val
                    ? "bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <select
            value={categoryFilter ?? ""}
            onChange={(e) =>
              onCategoryFilterChange(e.target.value ? Number(e.target.value) : null)
            }
            className="input-pro px-3 py-1.5 text-xs"
          >
            <option value="">Todas categorias</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.icon ? `${c.icon} ` : ""}
                {c.name}
              </option>
            ))}
          </select>

          {cards.length > 0 && (
            <select
              value={cardFilter ?? ""}
              onChange={(e) =>
                onCardFilterChange(e.target.value ? Number(e.target.value) : null)
              }
              className="input-pro px-3 py-1.5 text-xs"
            >
              <option value="">Todos cartões</option>
              {cards.map((cd) => (
                <option key={cd.id} value={cd.id}>
                  {cd.name}
                </option>
              ))}
            </select>
          )}

          <select
            value={sortOrder}
            onChange={(e) =>
              onSortOrderChange(
                e.target.value as "date_desc" | "date_asc" | "amount_desc" | "amount_asc"
              )
            }
            className="input-pro px-3 py-1.5 text-xs"
          >
            <option value="date_desc">Mais recentes</option>
            <option value="date_asc">Mais antigos</option>
            <option value="amount_desc">Maior valor</option>
            <option value="amount_asc">Menor valor</option>
          </select>
        </div>
      </div>

      {/* Summary Strip */}
      <div className="surface-card flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-3.5">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <div className="text-[11px] text-[var(--text-muted)]">Receitas</div>
            <div className="tabular-nums text-sm font-bold text-emerald-400">
              {formatMoney(totals.income, currency, locale)}
            </div>
          </div>
          <div>
            <div className="text-[11px] text-[var(--text-muted)]">Despesas</div>
            <div className="tabular-nums text-sm font-bold text-orange-400">
              {formatMoney(totals.expense, currency, locale)}
            </div>
          </div>
          <div>
            <div className="text-[11px] text-[var(--text-muted)]">Saldo do filtro</div>
            <div
              className={`tabular-nums text-sm font-bold ${
                totals.net >= 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {formatMoney(totals.net, currency, locale)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="tabular-nums text-xs text-[var(--text-muted)]">
            {totals.count} lançamento(s)
          </span>
          {items.length > 0 && (
            <button
              type="button"
              onClick={toggleAll}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface-hover)]"
            >
              {selected.size === items.length ? (
                <CheckSquare className="h-3.5 w-3.5 text-[var(--accent)]" />
              ) : (
                <Square className="h-3.5 w-3.5" />
              )}
              Selecionar todos
            </button>
          )}
        </div>
      </div>

      {/* Floating Batch Action Bar */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-500/40 bg-[var(--accent-soft)] px-4 py-2.5"
          >
            <span className="text-xs font-semibold text-[var(--text-primary)]">
              {selected.size} selecionado(s)
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setTargetCatId(categories[0]?.id || 1);
                  setBatchCatOpen(true);
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition hover:brightness-110"
              >
                <Tag className="h-3.5 w-3.5 text-[var(--accent)]" />
                Alterar categoria
              </button>
              <button
                type="button"
                onClick={async () => {
                  await onBatchDelete(selectedIds);
                  setSelected(new Set());
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-500/90 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-red-500"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Excluir ({selected.size})
              </button>
              <button
                type="button"
                onClick={() => setSelected(new Set())}
                className="rounded-lg px-2 py-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                Limpar
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Grouped Transaction Rows */}
      <div className="surface-card overflow-hidden rounded-2xl">
        {loading && !data ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-xl bg-[var(--bg-surface-hover)]"
              />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Nenhum lançamento encontrado
            </p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Ajuste os filtros ou clique em Novo lançamento para começar.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {grouped.map(([day, dayItems]) => (
              <div key={day}>
                <div className="bg-[var(--bg-surface-hover)] px-5 py-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  {formatDateGroup(day)}
                </div>
                <div className="divide-y divide-[var(--border-subtle)]">
                  {dayItems.map((tx) => {
                    const isChecked = selected.has(tx.id);
                    const isIncome = tx.type === "income";
                    return (
                      <div
                        key={tx.id}
                        className={`group flex items-center gap-3.5 px-5 py-3 transition hover:bg-[var(--bg-surface-hover)] ${
                          isChecked ? "bg-[var(--accent-soft)]" : ""
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => toggleOne(tx.id)}
                          aria-label={`Selecionar ${tx.description}`}
                          className="text-[var(--text-muted)] hover:text-[var(--accent)]"
                        >
                          {isChecked ? (
                            <CheckSquare className="h-4 w-4 text-[var(--accent)]" />
                          ) : (
                            <Square className="h-4 w-4" />
                          )}
                        </button>

                        <div
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm"
                          style={{
                            backgroundColor: `${tx.category_color || "#64748b"}22`,
                            color: tx.category_color || "#94a3b8",
                          }}
                        >
                          {tx.category_icon || (isIncome ? "↗" : "↘")}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium text-[var(--text-primary)]">
                            {tx.description}
                          </div>
                          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-muted)]">
                            <span>{tx.category_name || "Sem categoria"}</span>
                            {consolidated && tx.profile_name && (
                              <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border-subtle)] px-1.5 py-0.2">
                                <span
                                  className="h-1.5 w-1.5 rounded-full"
                                  style={{ backgroundColor: tx.profile_color }}
                                />
                                {tx.profile_name}
                              </span>
                            )}
                            {tx.credit_card_name && (
                              <span className="inline-flex items-center gap-1 text-violet-400">
                                <CardIcon className="h-3 w-3" />
                                {tx.credit_card_name}
                              </span>
                            )}
                          </div>
                        </div>

                        <div
                          className={`tabular-nums shrink-0 text-right text-sm font-semibold ${
                            isIncome ? "text-emerald-400" : "text-[var(--text-primary)]"
                          }`}
                        >
                          {isIncome ? "+" : "-"} {formatMoney(tx.amount, currency, locale)}
                        </div>

                        <div className="flex shrink-0 items-center gap-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
                          <button
                            type="button"
                            onClick={() => onEditTransaction(tx)}
                            title="Editar"
                            className="rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface-solid)] hover:text-[var(--text-primary)]"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onSoftDeleteOne(tx)}
                            title="Excluir (com Desfazer)"
                            className="rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-red-500/15 hover:text-red-400"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Batch Category Modal */}
      <Modal
        open={batchCatOpen}
        onClose={() => setBatchCatOpen(false)}
        title="Alterar categoria em lote"
        subtitle={`Aplicar a ${selected.size} lançamento(s) selecionado(s)`}
        widthClass="w-[400px]"
      >
        <div className="space-y-4">
          <select
            value={targetCatId}
            onChange={(e) => setTargetCatId(Number(e.target.value))}
            className="input-pro w-full px-3 py-2.5 text-sm"
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.icon ? `${c.icon} ` : ""}
                {c.name}
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setBatchCatOpen(false)}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)]"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={async () => {
                await onBatchCategory(selectedIds, targetCatId);
                setSelected(new Set());
                setBatchCatOpen(false);
              }}
              className="rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white"
            >
              Aplicar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
