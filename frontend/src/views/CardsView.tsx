import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { CreditCard as CardIcon, Plus, Trash2 } from "lucide-react";
import { api, type CardSummary, type Profile } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Modal } from "../components/Modal";

interface CardsViewProps {
  profileId: number | null;
  consolidated: boolean;
  year: number;
  month: number | null;
  profiles: Profile[];
  currency: string;
  locale: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
  onMutated: () => void;
}

export function CardsView({
  profileId,
  consolidated,
  year,
  month,
  profiles,
  currency,
  locale,
  onToast,
  onMutated,
}: CardsViewProps) {
  const [cards, setCards] = useState<CardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const [name, setName] = useState("");
  const [limitRaw, setLimitRaw] = useState("");
  const [dueDay, setDueDay] = useState("10");
  const [closingDay, setClosingDay] = useState("3");
  const [selectedProfile, setSelectedProfile] = useState<number>(
    profileId || profiles[0]?.id || 1
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.cards({ profile_id: profileId, consolidated, year, month });
      setCards(res.items || []);
    } catch {
      onToast("Erro ao carregar cartões.", "error");
    } finally {
      setLoading(false);
    }
  }, [profileId, consolidated, year, month, onToast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const lim = Number(limitRaw.replace(",", "."));
    const due = Number(dueDay);
    const close = Number(closingDay);
    if (!name.trim() || !Number.isFinite(lim) || lim <= 0 || due < 1 || due > 31) {
      onToast("Preencha nome, limite válido e dia de vencimento (1-31).", "error");
      return;
    }
    try {
      await api.createCard({
        profile_id: selectedProfile,
        name: name.trim(),
        credit_limit: lim,
        due_day: due,
        closing_day: Math.min(31, Math.max(1, close || 1)),
      });
      setModalOpen(false);
      setName("");
      setLimitRaw("");
      onToast("Cartão adicionado.");
      await load();
      onMutated();
    } catch {
      onToast("Não foi possível criar o cartão.", "error");
    }
  };

  const handleDelete = async (card: CardSummary) => {
    try {
      await api.deleteCard(card.id);
      onToast(`Cartão "${card.name}" removido.`);
      await load();
      onMutated();
    } catch {
      onToast("Erro ao remover cartão.", "error");
    }
  };

  const totalLimit = cards.reduce((a, c) => a + c.credit_limit, 0);
  const totalSpent = cards.reduce((a, c) => a + c.spent, 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-6">
          <div className="surface-card rounded-2xl px-5 py-3.5">
            <div className="text-[11px] text-[var(--text-muted)]">Fatura total no mês</div>
            <div className="tabular-nums mt-0.5 text-lg font-bold text-violet-400">
              {formatMoney(totalSpent, currency, locale)}
            </div>
          </div>
          <div className="surface-card rounded-2xl px-5 py-3.5">
            <div className="text-[11px] text-[var(--text-muted)]">Limite total</div>
            <div className="tabular-nums mt-0.5 text-lg font-bold text-[var(--text-primary)]">
              {formatMoney(totalLimit, currency, locale)}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            setSelectedProfile(profileId || profiles[0]?.id || 1);
            setModalOpen(true);
          }}
          className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 transition hover:brightness-110"
        >
          <Plus className="h-3.5 w-3.5" />
          Novo cartão
        </button>
      </div>

      {loading && cards.length === 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="surface-card h-44 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <div className="surface-card flex flex-col items-center justify-center rounded-2xl py-16 text-center">
          <CardIcon className="h-10 w-10 text-violet-400/70" />
          <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
            Nenhum cartão cadastrado
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Cadastre seus cartões para acompanhar faturas e limites automaticamente.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cards.map((card, idx) => {
            const pct = Math.min(100, Math.max(0, card.usage_pct));
            const barColor =
              pct >= 90 ? "#ef4444" : pct >= 70 ? "#f59e0b" : "#8b5cf6";
            return (
              <motion.div
                key={card.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="surface-card surface-card-interactive relative overflow-hidden rounded-2xl p-5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15 text-violet-400">
                      <CardIcon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-[var(--text-primary)]">
                        {card.name}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)]">
                        Vence dia {card.due_day} · Fecha dia {card.closing_day}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(card)}
                    title="Remover cartão"
                    className="rounded-lg p-1.5 text-[var(--text-muted)] transition hover:bg-red-500/15 hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="mt-5 flex items-baseline justify-between">
                  <div>
                    <div className="text-[11px] text-[var(--text-muted)]">Fatura atual</div>
                    <div className="tabular-nums text-xl font-bold text-[var(--text-primary)]">
                      {formatMoney(card.spent, currency, locale)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11px] text-[var(--text-muted)]">Disponível</div>
                    <div className="tabular-nums text-xs font-semibold text-emerald-400">
                      {formatMoney(card.available, currency, locale)}
                    </div>
                  </div>
                </div>

                <div className="mt-4 space-y-1.5">
                  <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-surface-hover)]">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: barColor }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-[var(--text-muted)]">
                    <span>{pct.toFixed(0)}% utilizado</span>
                    <span className="tabular-nums">
                      Limite {formatMoney(card.credit_limit, currency, locale)}
                    </span>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo cartão de crédito"
        widthClass="w-[420px]"
      >
        <form onSubmit={handleCreate} className="space-y-3.5">
          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Nome do cartão
            </label>
            <input
              type="text"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex.: Nubank Ultravioleta"
              className="input-pro w-full px-3.5 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Limite
              </label>
              <input
                type="text"
                inputMode="decimal"
                value={limitRaw}
                onChange={(e) => setLimitRaw(e.target.value)}
                placeholder="5000,00"
                className="input-pro tabular-nums w-full px-3.5 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Perfil
              </label>
              <select
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(Number(e.target.value))}
                className="input-pro w-full px-3 py-2 text-sm"
              >
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Dia do vencimento
              </label>
              <input
                type="number"
                min={1}
                max={31}
                value={dueDay}
                onChange={(e) => setDueDay(e.target.value)}
                className="input-pro w-full px-3.5 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Dia do fechamento
              </label>
              <input
                type="number"
                min={1}
                max={31}
                value={closingDay}
                onChange={(e) => setClosingDay(e.target.value)}
                className="input-pro w-full px-3.5 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white"
            >
              Salvar cartão
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
