import { useEffect, useMemo, useState } from "react";
import { Modal } from "./Modal";
import type {
  Category,
  CreditCard,
  Profile,
  TransactionItem,
  TransactionPayload,
} from "../lib/api";

interface TransactionModalProps {
  open: boolean;
  onClose: () => void;
  editing: TransactionItem | null;
  profiles: Profile[];
  categories: Category[];
  cards: CreditCard[];
  defaultProfileId: number | null;
  onSave: (payload: TransactionPayload, editingId: number | null) => Promise<void>;
}

export function TransactionModal({
  open,
  onClose,
  editing,
  profiles,
  categories,
  cards,
  defaultProfileId,
  onSave,
}: TransactionModalProps) {
  const [type, setType] = useState<"expense" | "income">("expense");
  const [description, setDescription] = useState("");
  const [amountRaw, setAmountRaw] = useState("");
  const [dateStr, setDateStr] = useState(() => new Date().toISOString().slice(0, 10));
  const [profileId, setProfileId] = useState<number>(defaultProfileId || profiles[0]?.id || 1);
  const [categoryId, setCategoryId] = useState<number>(0);
  const [cardId, setCardId] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredCategories = useMemo(
    () => categories.filter((c) => c.type === type),
    [categories, type]
  );

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (editing) {
      setType(editing.type);
      setDescription(editing.description);
      setAmountRaw(editing.amount.toFixed(2).replace(".", ","));
      setDateStr(editing.date);
      setProfileId(editing.profile_id);
      setCategoryId(editing.category_id);
      setCardId(editing.credit_card_id ? String(editing.credit_card_id) : "");
      setNotes(editing.notes || "");
    } else {
      setType("expense");
      setDescription("");
      setAmountRaw("");
      setDateStr(new Date().toISOString().slice(0, 10));
      setProfileId(defaultProfileId || profiles[0]?.id || 1);
      const firstExp = categories.find((c) => c.type === "expense");
      setCategoryId(firstExp?.id || categories[0]?.id || 1);
      setCardId("");
      setNotes("");
    }
  }, [open, editing, defaultProfileId, profiles, categories]);

  useEffect(() => {
    if (filteredCategories.length && !filteredCategories.some((c) => c.id === categoryId)) {
      setCategoryId(filteredCategories[0].id);
    }
  }, [filteredCategories, categoryId]);

  const parseAmount = (raw: string): number => {
    const clean = raw.replace(/[R$€\s]/g, "");
    if (!clean) return NaN;
    if (clean.includes(",") && clean.includes(".")) {
      return Number(clean.replace(/\./g, "").replace(",", "."));
    }
    return Number(clean.replace(",", "."));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseAmount(amountRaw);
    if (!description.trim()) {
      setError("Informe uma descrição.");
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Informe um valor maior que zero.");
      return;
    }
    if (!categoryId) {
      setError("Selecione uma categoria.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(
        {
          profile_id: profileId,
          date: dateStr,
          description: description.trim(),
          amount,
          category_id: categoryId,
          type,
          credit_card_id: cardId ? Number(cardId) : null,
          notes: notes.trim() || null,
        },
        editing?.id ?? null
      );
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar lançamento.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? "Editar lançamento" : "Novo lançamento"}
      subtitle="Salvo localmente no SQLite com privacidade total"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-1">
          {(["expense", "income"] as const).map((t) => {
            const active = type === t;
            return (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={`rounded-lg py-2 text-xs font-semibold transition ${
                  active
                    ? t === "expense"
                      ? "bg-orange-500/20 text-orange-400 shadow-sm"
                      : "bg-emerald-500/20 text-emerald-400 shadow-sm"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                {t === "expense" ? "Despesa" : "Receita"}
              </button>
            );
          })}
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
            Descrição
          </label>
          <input
            type="text"
            autoFocus
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ex.: Supermercado, Salário, Uber..."
            className="input-pro w-full px-3.5 py-2.5 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Valor
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={amountRaw}
              onChange={(e) => setAmountRaw(e.target.value)}
              placeholder="0,00"
              className="input-pro tabular-nums w-full px-3.5 py-2.5 text-sm font-semibold"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Data
            </label>
            <input
              type="date"
              value={dateStr}
              onChange={(e) => setDateStr(e.target.value)}
              className="input-pro w-full px-3.5 py-2.5 text-sm"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Categoria
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              className="input-pro w-full px-3 py-2.5 text-sm"
            >
              {filteredCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.icon ? `${c.icon} ` : ""}
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Perfil
            </label>
            <select
              value={profileId}
              onChange={(e) => setProfileId(Number(e.target.value))}
              className="input-pro w-full px-3 py-2.5 text-sm"
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {cards.length > 0 && type === "expense" && (
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Cartão de crédito (opcional)
            </label>
            <select
              value={cardId}
              onChange={(e) => setCardId(e.target.value)}
              className="input-pro w-full px-3 py-2.5 text-sm"
            >
              <option value="">Sem cartão</option>
              {cards.map((cd) => (
                <option key={cd.id} value={cd.id}>
                  {cd.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
            Observações (opcional)
          </label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notas adicionais..."
            className="input-pro w-full px-3.5 py-2 text-sm"
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface-hover)]"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-[var(--accent)] px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 transition hover:brightness-110 disabled:opacity-60"
          >
            {saving ? "Salvando..." : editing ? "Salvar alterações" : "Adicionar lançamento"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
