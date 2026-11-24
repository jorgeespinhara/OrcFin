import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus, RefreshCw, Trash2, TrendingUp } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { api, type PortfolioSummary } from "../lib/api";
import { formatMoney, formatPct } from "../lib/format";
import { Modal } from "../components/Modal";

const COLORS = ["#14b8a6", "#6366f1", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6"];

interface InvestmentsViewProps {
  profileId: number;
  currency: string;
  locale: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
}

export function InvestmentsView({
  profileId,
  currency,
  locale,
  onToast,
}: InvestmentsViewProps) {
  const [data, setData] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const [name, setName] = useState("");
  const [ticker, setTicker] = useState("");
  const [assetClass, setAssetClass] = useState("acoes");
  const [quantity, setQuantity] = useState("1");
  const [avgPrice, setAvgPrice] = useState("");
  const [institution, setInstitution] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.investments(profileId);
      setData(res);
    } catch {
      onToast("Erro ao carregar carteira.", "error");
    } finally {
      setLoading(false);
    }
  }, [profileId, onToast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRefreshQuotes = async () => {
    setRefreshing(true);
    try {
      await api.refreshQuotes(profileId);
      await load();
      onToast("Cotações atualizadas.");
    } catch {
      onToast("Não foi possível atualizar cotações agora.", "error");
    } finally {
      setRefreshing(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = Number(quantity.replace(",", "."));
    const price = Number(avgPrice.replace(",", "."));
    if (!name.trim() || !Number.isFinite(qty) || qty <= 0 || !Number.isFinite(price)) {
      onToast("Informe nome, quantidade e preço médio válidos.", "error");
      return;
    }
    try {
      await api.createHolding({
        profile_id: profileId,
        name: name.trim(),
        ticker: ticker.trim(),
        asset_class: assetClass,
        quantity: qty,
        avg_price: price,
        institution: institution.trim(),
      });
      setModalOpen(false);
      setName("");
      setTicker("");
      setAvgPrice("");
      onToast("Ativo adicionado à carteira.");
      await load();
    } catch {
      onToast("Erro ao adicionar ativo.", "error");
    }
  };

  const items = data?.items || [];
  const byClass = data?.by_class || [];
  const totalValue = data?.total_market_value ?? 0;
  const totalInvested = data?.total_invested ?? 0;
  const totalPnl = data?.total_pnl ?? 0;
  const totalPnlPct = data?.total_pnl_pct ?? 0;

  return (
    <div className="space-y-5">
      {/* KPIs + Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="surface-card rounded-2xl p-4">
            <div className="text-[11px] text-[var(--text-muted)]">Valor de mercado</div>
            <div className="tabular-nums mt-1 text-xl font-bold text-[var(--text-primary)]">
              {formatMoney(totalValue, currency, locale)}
            </div>
          </div>
          <div className="surface-card rounded-2xl p-4">
            <div className="text-[11px] text-[var(--text-muted)]">Total investido</div>
            <div className="tabular-nums mt-1 text-xl font-bold text-[var(--text-secondary)]">
              {formatMoney(totalInvested, currency, locale)}
            </div>
          </div>
          <div className="surface-card rounded-2xl p-4">
            <div className="text-[11px] text-[var(--text-muted)]">Resultado (PnL)</div>
            <div
              className={`tabular-nums mt-1 text-xl font-bold ${
                totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {formatMoney(totalPnl, currency, locale)}{" "}
              <span className="text-xs font-semibold">({formatPct(totalPnlPct)})</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={refreshing}
            onClick={handleRefreshQuotes}
            className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-strong)] px-3.5 py-2 text-xs font-semibold text-[var(--text-primary)] transition hover:bg-[var(--bg-surface-hover)] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar cotações
          </button>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20"
          >
            <Plus className="h-3.5 w-3.5" />
            Novo ativo
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="surface-card h-72 animate-pulse rounded-2xl" />
      ) : items.length === 0 ? (
        <div className="surface-card flex flex-col items-center justify-center rounded-2xl py-16 text-center">
          <TrendingUp className="h-10 w-10 text-[var(--indigo)]" />
          <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
            Sua carteira está vazia
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Adicione ações, FIIs, renda fixa, ETFs, fundos ou cripto para acompanhar sua alocação.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          {/* Allocation Donut */}
          <div className="surface-card rounded-2xl p-5 xl:col-span-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Alocação por classe
            </h3>
            <div className="mt-3 h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={byClass}
                    dataKey="value"
                    nameKey="asset_class"
                    innerRadius={48}
                    outerRadius={78}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {byClass.map((entry, idx) => (
                      <Cell key={entry.asset_class} fill={COLORS[idx % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number) => formatMoney(v, currency, locale)}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 space-y-1.5">
              {byClass.map((c, idx) => (
                <div
                  key={c.asset_class}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="flex items-center gap-2 text-[var(--text-secondary)]">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                    />
                    {c.label || c.asset_class}
                  </span>
                  <span className="tabular-nums font-semibold text-[var(--text-primary)]">
                    {(c.pct || 0).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Holdings Table */}
          <div className="surface-card overflow-hidden rounded-2xl xl:col-span-8">
            <div className="border-b border-[var(--border-subtle)] px-5 py-3.5 text-sm font-semibold text-[var(--text-primary)]">
              Posições ({items.length})
            </div>
            <div className="divide-y divide-[var(--border-subtle)]">
              {items.map((h) => (
                <motion.div
                  key={h.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-xs hover:bg-[var(--bg-surface-hover)]"
                >
                  <div className="min-w-[160px] flex-1">
                    <div className="font-semibold text-[var(--text-primary)]">
                      {h.ticker ? `${h.ticker} · ` : ""}
                      {h.name}
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      {h.asset_class}
                      {h.institution ? ` · ${h.institution}` : ""} · Qtd {h.quantity}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="tabular-nums font-semibold text-[var(--text-primary)]">
                      {formatMoney(h.market_value, currency, locale)}
                    </div>
                    <div
                      className={`tabular-nums text-[11px] font-medium ${
                        h.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {h.pnl >= 0 ? "+" : ""}
                      {formatMoney(h.pnl, currency, locale)} ({formatPct(h.pnl_pct)})
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteHolding(h.id);
                      onToast("Posição removida.");
                      await load();
                    }}
                    className="rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-red-500/15 hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo ativo na carteira"
        widthClass="w-[440px]"
      >
        <form onSubmit={handleCreate} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Nome
              </label>
              <input
                type="text"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ex.: Tesouro Selic / PETR4"
                className="input-pro w-full px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Ticker (opcional)
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="PETR4, HGLG11..."
                className="input-pro w-full px-3 py-2 text-sm uppercase"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Classe
              </label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value)}
                className="input-pro w-full px-3 py-2 text-sm"
              >
                <option value="acoes">Ações</option>
                <option value="fiis">FIIs</option>
                <option value="renda_fixa">Renda Fixa</option>
                <option value="etf">ETFs</option>
                <option value="fundos">Fundos</option>
                <option value="cripto">Cripto</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Corretora / Banco
              </label>
              <input
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="Ex.: XP, NuInvest..."
                className="input-pro w-full px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Quantidade
              </label>
              <input
                type="text"
                inputMode="decimal"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="input-pro tabular-nums w-full px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Preço médio
              </label>
              <input
                type="text"
                inputMode="decimal"
                value={avgPrice}
                onChange={(e) => setAvgPrice(e.target.value)}
                placeholder="0,00"
                className="input-pro tabular-nums w-full px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white"
            >
              Adicionar
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
