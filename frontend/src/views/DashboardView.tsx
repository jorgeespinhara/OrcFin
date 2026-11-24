import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CalendarClock,
  Plus,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wallet,
  PiggyBank,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardData } from "../lib/api";
import { formatMoney, formatPct, formatShortMoney } from "../lib/format";

const PIE_COLORS = [
  "#14b8a6",
  "#6366f1",
  "#f97316",
  "#ec4899",
  "#eab308",
  "#06b6d4",
  "#8b5cf6",
  "#64748b",
];

interface DashboardViewProps {
  data: DashboardData | null;
  loading: boolean;
  currency: string;
  locale: string;
  onSelectCategory: (categoryId: number) => void;
  onOpenTransactions: () => void;
  onNewTransaction: () => void;
  onSeedDemo: () => void;
}

function CustomTooltip({
  active,
  payload,
  label,
  currency,
  locale,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  currency: string;
  locale: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3.5 py-2.5 text-xs shadow-2xl">
      {label && (
        <div className="mb-1.5 font-semibold text-[var(--text-primary)]">{label}</div>
      )}
      <div className="space-y-1">
        {payload.map((entry, idx) => (
          <div key={idx} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              {entry.name}
            </span>
            <span className="tabular-nums font-semibold text-[var(--text-primary)]">
              {formatMoney(entry.value, currency, locale)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DashboardView({
  data,
  loading,
  currency,
  locale,
  onSelectCategory,
  onOpenTransactions,
  onNewTransaction,
  onSeedDemo,
}: DashboardViewProps) {
  if (loading && !data) {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="surface-card h-36 animate-pulse rounded-2xl p-5"
            />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="surface-card h-80 animate-pulse rounded-2xl xl:col-span-7" />
          <div className="surface-card h-80 animate-pulse rounded-2xl xl:col-span-5" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  const current = data.current_month;
  const comp = data.comparison;
  const spend = data.spendable?.spendable ?? 0;
  const series = data.monthly_series || [];
  const categories = data.category_breakdown || [];
  const evolution = (data.balance_evolution || []).slice(-12);
  const budgets = data.budgets || [];
  const dueDates = data.due_dates || [];

  const isEmpty =
    current.total_income === 0 &&
    current.total_expense === 0 &&
    categories.length === 0;

  const sparkTail = series.slice(-6);
  const kpis = [
    {
      label: "Saldo do período",
      value: formatMoney(current.net_savings, currency, locale),
      badge: `Poupança ${current.savings_rate.toFixed(1)}%`,
      positive: current.net_savings >= 0,
      color: current.net_savings >= 0 ? "#22c55e" : "#ef4444",
      icon: Wallet,
      spark: sparkTail.map((p, i) => ({ i, v: p.net_savings })),
      onClick: onOpenTransactions,
    },
    {
      label: "Disponível para gastar",
      value: formatMoney(spend, currency, locale),
      badge: spend >= 0 ? "Dentro do plano" : "Acima do previsto",
      positive: spend >= 0,
      color: "#14b8a6",
      icon: PiggyBank,
      spark: sparkTail.map((p, i) => ({ i, v: Math.max(0, p.income - p.expense) })),
      onClick: onOpenTransactions,
    },
    {
      label: "Receitas",
      value: formatMoney(current.total_income, currency, locale),
      badge: formatPct(comp.income_change_pct),
      positive: comp.income_change_pct >= 0,
      color: "#22c55e",
      icon: TrendingUp,
      spark: sparkTail.map((p, i) => ({ i, v: p.income })),
      onClick: onOpenTransactions,
    },
    {
      label: "Despesas",
      value: formatMoney(current.total_expense, currency, locale),
      badge: formatPct(comp.expense_change_pct),
      positive: comp.expense_change_pct <= 0,
      color: "#f97316",
      icon: TrendingDown,
      spark: sparkTail.map((p, i) => ({ i, v: p.expense })),
      onClick: onOpenTransactions,
    },
  ];

  const totalCatExpense = categories.reduce((acc, c) => acc + c.total, 0);

  return (
    <div className="space-y-5">
      {isEmpty && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="surface-card flex flex-wrap items-center justify-between gap-4 rounded-2xl border-teal-500/30 p-5"
        >
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Nenhum lançamento neste período ainda
              </h2>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                Adicione seu primeiro lançamento ou carregue dados de demonstração para ver os gráficos em ação.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onSeedDemo}
              className="rounded-xl border border-[var(--border-strong)] px-3.5 py-2 text-xs font-semibold text-[var(--text-primary)] transition hover:bg-[var(--bg-surface-hover)]"
            >
              Carregar dados demo
            </button>
            <button
              type="button"
              onClick={onNewTransaction}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 transition hover:brightness-110"
            >
              <Plus className="h-3.5 w-3.5" />
              Novo lançamento
            </button>
          </div>
        </motion.div>
      )}

      {/* Band 1: 4 Responsive KPI Cards with Sparklines */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <motion.button
              key={kpi.label}
              type="button"
              onClick={kpi.onClick}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05, duration: 0.28 }}
              className="surface-card surface-card-interactive group flex flex-col justify-between rounded-2xl p-5 text-left"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-muted)]">
                  {kpi.label}
                </span>
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-xl"
                  style={{ backgroundColor: `${kpi.color}1a`, color: kpi.color }}
                >
                  <Icon className="h-4 w-4" />
                </div>
              </div>

              <div className="mt-3 flex items-end justify-between gap-2">
                <div>
                  <div className="tabular-nums text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                    {kpi.value}
                  </div>
                  <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-[var(--bg-surface-hover)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-secondary)]">
                    {kpi.positive ? (
                      <ArrowUpRight className="h-3 w-3 text-emerald-400" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3 text-orange-400" />
                    )}
                    {kpi.badge}
                  </div>
                </div>

                {kpi.spark.length > 1 && (
                  <div className="h-12 w-24 shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={kpi.spark}>
                        <defs>
                          <linearGradient id={`spark-${idx}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={kpi.color} stopOpacity={0.35} />
                            <stop offset="100%" stopColor={kpi.color} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <Area
                          type="monotone"
                          dataKey="v"
                          stroke={kpi.color}
                          strokeWidth={2}
                          fill={`url(#spark-${idx})`}
                          isAnimationActive={true}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Band 2: Upcoming Bills Strip (when present) */}
      {dueDates.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.16 }}
          className="surface-card rounded-2xl p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
              <CalendarClock className="h-4 w-4 text-amber-400" />
              Próximos vencimentos
            </div>
            <span className="text-[11px] text-[var(--text-muted)]">
              Próximos 30 dias
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {dueDates.map((d, i) => {
              const urgent = (d.days_until ?? 99) <= 3;
              return (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)] px-3.5 py-2.5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 truncate text-xs font-semibold text-[var(--text-primary)]">
                      {urgent && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />}
                      <span className="truncate">{d.title || d.description || "Vencimento"}</span>
                    </div>
                    <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
                      {d.due_date || ""}
                    </div>
                  </div>
                  {typeof d.amount === "number" && (
                    <span className="tabular-nums shrink-0 text-xs font-semibold text-[var(--text-primary)]">
                      {formatMoney(d.amount, currency, locale)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Band 3: Interactive Cashflow (12m) + Category Breakdown Donut */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="surface-card rounded-2xl p-5 xl:col-span-7"
        >
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Receitas × Despesas
              </h3>
              <p className="text-xs text-[var(--text-muted)]">
                Evolução mensal nos últimos 12 meses
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                Receitas
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-orange-500" />
                Despesas
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series.slice(-12)} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => formatShortMoney(v, currency)}
                  width={60}
                />
                <Tooltip
                  cursor={{ fill: "var(--bg-surface-hover)" }}
                  content={<CustomTooltip currency={currency} locale={locale} />}
                />
                <Bar
                  dataKey="income"
                  name="Receitas"
                  fill="#22c55e"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={24}
                />
                <Bar
                  dataKey="expense"
                  name="Despesas"
                  fill="#f97316"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={24}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="surface-card rounded-2xl p-5 xl:col-span-5"
        >
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Despesas por categoria
              </h3>
              <p className="text-xs text-[var(--text-muted)]">
                Clique em uma categoria para filtrar lançamentos
              </p>
            </div>
          </div>

          {categories.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-xs text-[var(--text-muted)]">
              Sem despesas registradas neste período.
            </div>
          ) : (
            <div className="grid grid-cols-1 items-center gap-4 sm:grid-cols-2">
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categories.slice(0, 8)}
                      dataKey="total"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={52}
                      outerRadius={82}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {categories.slice(0, 8).map((entry, idx) => (
                        <Cell
                          key={entry.name}
                          fill={entry.color || PIE_COLORS[idx % PIE_COLORS.length]}
                          className="cursor-pointer outline-none"
                          onClick={() => {
                            if (entry.category_id) onSelectCategory(entry.category_id);
                          }}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      content={<CustomTooltip currency={currency} locale={locale} />}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
                {categories.slice(0, 8).map((cat, idx) => {
                  const pct =
                    totalCatExpense > 0 ? (cat.total / totalCatExpense) * 100 : 0;
                  const dotColor = cat.color || PIE_COLORS[idx % PIE_COLORS.length];
                  return (
                    <button
                      key={`${cat.name}-${idx}`}
                      type="button"
                      onClick={() => {
                        if (cat.category_id) onSelectCategory(cat.category_id);
                      }}
                      className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-[var(--bg-surface-hover)]"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: dotColor }}
                        />
                        <span className="truncate text-xs font-medium text-[var(--text-secondary)]">
                          {cat.name}
                        </span>
                      </span>
                      <span className="tabular-nums shrink-0 text-xs font-semibold text-[var(--text-primary)]">
                        {pct.toFixed(0)}%
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Band 4: Balance Evolution Area + Monthly Budgets */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="surface-card rounded-2xl p-5 xl:col-span-7"
        >
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Evolução do saldo acumulado
            </h3>
            <p className="text-xs text-[var(--text-muted)]">
              Tendência patrimonial nos últimos 12 meses
            </p>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={evolution}>
                <defs>
                  <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => formatShortMoney(v, currency)}
                  width={62}
                />
                <Tooltip content={<CustomTooltip currency={currency} locale={locale} />} />
                <Area
                  type="monotone"
                  dataKey="cumulative_balance"
                  name="Saldo acumulado"
                  stroke="#14b8a6"
                  strokeWidth={2.5}
                  fill="url(#balanceGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="surface-card rounded-2xl p-5 xl:col-span-5"
        >
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Orçamentos do mês
            </h3>
            <p className="text-xs text-[var(--text-muted)]">
              Acompanhamento de limites por categoria
            </p>
          </div>

          {budgets.length === 0 ? (
            <div className="flex h-56 items-center justify-center text-xs text-[var(--text-muted)]">
              Nenhum orçamento configurado para este mês.
            </div>
          ) : (
            <div className="max-h-56 space-y-3.5 overflow-y-auto pr-1">
              {budgets.slice(0, 6).map((b, idx) => {
                const pct = Math.min(100, Math.max(0, b.percentage || 0));
                const barColor =
                  b.percentage >= 100
                    ? "#ef4444"
                    : b.percentage >= 80
                    ? "#f59e0b"
                    : "#14b8a6";
                return (
                  <div key={`${b.category_name}-${idx}`} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[var(--text-primary)]">
                        {b.icon ? `${b.icon} ` : ""}
                        {b.category_name}
                      </span>
                      <span className="tabular-nums text-[var(--text-muted)]">
                        <strong className="text-[var(--text-primary)]">
                          {formatMoney(b.spent, currency, locale)}
                        </strong>{" "}
                        / {formatMoney(b.limit, currency, locale)}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-surface-hover)]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.55, ease: "easeOut" }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: barColor }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
