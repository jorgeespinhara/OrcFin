import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  FileDown,
  Lightbulb,
  Repeat,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type ReportsResponse } from "../lib/api";
import { formatMoney, formatShortMoney } from "../lib/format";

interface ReportsViewProps {
  profileId: number | null;
  consolidated: boolean;
  year: number;
  month: number | null;
  currency: string;
  locale: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
}

export function ReportsView({
  profileId,
  consolidated,
  year,
  month,
  currency,
  locale,
  onToast,
}: ReportsViewProps) {
  const [data, setData] = useState<ReportsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);

  // Simulator
  const [simKind, setSimKind] = useState("expense_pct");
  const [simVal, setSimVal] = useState("10");
  const [simMonths, setSimMonths] = useState("12");
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null);

  // AI
  const [provider, setProvider] = useState("deepseek");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<{
    summary?: string;
    insights?: string[];
    recommendations?: string[];
    alerts?: string[];
    error?: string;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.reports({ profile_id: profileId, consolidated, year, month });
      setData(res);
      if (res.ai_provider) setProvider(res.ai_provider);
    } catch {
      onToast("Erro ao carregar relatórios.", "error");
    } finally {
      setLoading(false);
    }
  }, [profileId, consolidated, year, month, onToast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExportPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await api.exportPdf({
        profile_id: profileId,
        consolidated,
        year,
        month: month || new Date().getMonth() + 1,
      });
      onToast(`PDF salvo em ${res.path}`);
    } catch {
      onToast("Erro ao gerar PDF.", "error");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.simulate({
        profile_id: profileId,
        consolidated,
        months_ahead: Number(simMonths) || 12,
        kind: simKind,
        value: Number(simVal.replace(",", ".")) || 10,
      });
      setSimResult(res);
    } catch {
      onToast("Erro ao simular cenário.", "error");
    }
  };

  const handleRunAi = async () => {
    setAiLoading(true);
    try {
      const res = await api.runAi({ profile_id: profileId, consolidated, provider });
      setAiResult(res);
      if (res.error) onToast(res.error, "error");
    } catch {
      onToast("Não foi possível consultar a IA agora.", "error");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading && !data) {
    return <div className="surface-card h-80 animate-pulse rounded-2xl" />;
  }

  const seasonalMonths = data?.seasonal?.months || [];
  const recurrences = data?.recurrences || [];
  const insights = data?.local_insights || [];

  return (
    <div className="space-y-5">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Análises, Simulador e Inteligência Artificial
          </h2>
          <p className="text-xs text-[var(--text-muted)]">
            Relatórios locais + IA opcional recebendo apenas totais agregados (LGPD).
          </p>
        </div>
        <button
          type="button"
          disabled={pdfLoading}
          onClick={handleExportPdf}
          className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 disabled:opacity-50"
        >
          <FileDown className="h-3.5 w-3.5" />
          {pdfLoading ? "Gerando PDF..." : "Exportar Relatório PDF"}
        </button>
      </div>

      {/* Local Insights */}
      {insights.length > 0 && (
        <div className="surface-card rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
            <Lightbulb className="h-4 w-4 text-amber-400" />
            Insights locais do período
          </div>
          <ul className="space-y-2 text-xs text-[var(--text-secondary)]">
            {insights.map((tip, i) => (
              <li
                key={i}
                className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)] px-3.5 py-2.5"
              >
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Seasonal Chart + Recurrences */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="surface-card rounded-2xl p-5 xl:col-span-7">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            Sazonalidade de despesas
          </h3>
          <p className="mb-4 text-xs text-[var(--text-muted)]">
            Comparação do ano atual com a média histórica
          </p>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={seasonalMonths}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis
                  dataKey="month_label"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => formatShortMoney(v, currency)}
                  width={56}
                />
                <Tooltip formatter={(v: number) => formatMoney(v, currency, locale)} />
                <Bar dataKey="current" name="Ano atual" fill="#14b8a6" radius={[5, 5, 0, 0]} />
                <Bar dataKey="average" name="Média" fill="#6366f1" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="surface-card rounded-2xl p-5 xl:col-span-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
            <Repeat className="h-4 w-4 text-[var(--indigo)]" />
            Recorrências detectadas
          </div>
          {recurrences.length === 0 ? (
            <div className="flex h-52 items-center justify-center text-xs text-[var(--text-muted)]">
              Nenhuma recorrência detectada ainda.
            </div>
          ) : (
            <div className="max-h-56 divide-y divide-[var(--border-subtle)] overflow-y-auto">
              {recurrences.map((r, i) => (
                <div key={i} className="flex items-center justify-between py-2.5 text-xs">
                  <div className="min-w-0 pr-2">
                    <div className="truncate font-medium text-[var(--text-primary)]">
                      {r.description}
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      {r.distinct_months} meses
                    </div>
                  </div>
                  <span className="tabular-nums font-semibold text-[var(--text-primary)]">
                    {formatMoney(r.average_amount, currency, locale)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Scenario Simulator + AI Insights */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="surface-card rounded-2xl p-5 xl:col-span-6">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
            <SlidersHorizontal className="h-4 w-4 text-[var(--accent)]" />
            Simulador de cenários
          </div>
          <form onSubmit={handleSimulate} className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <select
                value={simKind}
                onChange={(e) => setSimKind(e.target.value)}
                className="input-pro px-2.5 py-2 text-xs"
              >
                <option value="expense_pct">Reduzir despesas (%)</option>
                <option value="income_pct">Aumentar receitas (%)</option>
                <option value="monthly_cut">Corte mensal fixo</option>
                <option value="extra_income">Renda extra mensal</option>
              </select>
              <input
                type="text"
                value={simVal}
                onChange={(e) => setSimVal(e.target.value)}
                placeholder="Valor"
                className="input-pro tabular-nums px-3 py-2 text-xs"
              />
              <input
                type="number"
                min={1}
                max={36}
                value={simMonths}
                onChange={(e) => setSimMonths(e.target.value)}
                placeholder="Meses"
                className="input-pro tabular-nums px-3 py-2 text-xs"
              />
            </div>
            <button
              type="submit"
              className="rounded-xl border border-[var(--border-strong)] px-4 py-2 text-xs font-semibold text-[var(--text-primary)] transition hover:bg-[var(--bg-surface-hover)]"
            >
              Simular impacto
            </button>
          </form>

          {simResult && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-teal-500/30 bg-[var(--accent-soft)] p-3.5 text-xs"
            >
              <div>
                <div className="text-[var(--text-muted)]">Saldo base projetado</div>
                <div className="tabular-nums mt-0.5 text-sm font-bold text-[var(--text-primary)]">
                  {formatMoney(Number(simResult.baseline_total_savings || 0), currency, locale)}
                </div>
              </div>
              <div>
                <div className="text-[var(--text-muted)]">Ganho no cenário</div>
                <div className="tabular-nums mt-0.5 text-sm font-bold text-emerald-400">
                  +{formatMoney(Number(simResult.delta_total || 0), currency, locale)}
                </div>
              </div>
            </motion.div>
          )}
        </div>

        <div className="surface-card rounded-2xl p-5 xl:col-span-6">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
              <Sparkles className="h-4 w-4 text-violet-400" />
              Análise com IA (opcional)
            </div>
            <div className="flex items-center gap-2">
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="input-pro px-2.5 py-1.5 text-xs"
              >
                {(data?.providers || []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={aiLoading}
                onClick={handleRunAi}
                className="rounded-xl bg-violet-500 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
              >
                {aiLoading ? "Analisando..." : "Gerar análise"}
              </button>
            </div>
          </div>

          {!aiResult ? (
            <p className="text-xs leading-relaxed text-[var(--text-muted)]">
              A IA recebe apenas totais mensais e percentuais por categoria — nunca descrições individuais, CPFs ou nomes. Configure sua chave de API em Configurações → Dados & IA.
            </p>
          ) : (
            <div className="space-y-2.5 text-xs">
              {aiResult.summary && (
                <p className="rounded-xl bg-[var(--bg-surface-solid)] p-3 text-[var(--text-primary)]">
                  {aiResult.summary}
                </p>
              )}
              {(aiResult.recommendations || []).map((rec, i) => (
                <div key={i} className="text-[var(--text-secondary)]">
                  • {rec}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
