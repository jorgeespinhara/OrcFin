import { useCallback, useEffect, useState } from "react";
import {
  Bug,
  Database,
  Download,
  RefreshCw,
  Shield,
  Sparkles,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import {
  api,
  type Category,
  type GoalItem,
  type NetWorthResponse,
  type Profile,
  type SettingsResponse,
} from "../lib/api";
import { formatMoney } from "../lib/format";

type SettingsTab = "accounts" | "finance" | "data";

interface SettingsViewProps {
  profiles: Profile[];
  categories: Category[];
  profileId: number;
  consolidated: boolean;
  year: number;
  month: number;
  currency: string;
  locale: string;
  version: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
  onRefreshMeta: () => Promise<void>;
}

export function SettingsView({
  profiles,
  categories,
  profileId,
  consolidated,
  year,
  month,
  currency,
  locale,
  version,
  onToast,
  onRefreshMeta,
}: SettingsViewProps) {
  const [subtab, setSubtab] = useState<SettingsTab>("accounts");
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [budgets, setBudgets] = useState<
    Array<{ id: number; category_name: string; spent: number; limit: number; percentage: number }>
  >([]);
  const [rules, setRules] = useState<
    Array<{ id: number; pattern: string; category_id: number; match_type: string }>
  >([]);
  const [netWorth, setNetWorth] = useState<NetWorthResponse | null>(null);

  // Quick form states
  const [newProfile, setNewProfile] = useState("");
  const [newCatName, setNewCatName] = useState("");
  const [newCatType, setNewCatType] = useState<"expense" | "income">("expense");
  const [newGoalName, setNewGoalName] = useState("");
  const [newGoalTarget, setNewGoalTarget] = useState("");
  const [budgetCatId, setBudgetCatId] = useState<number>(categories[0]?.id || 1);
  const [budgetLimit, setBudgetLimit] = useState("");
  const [rulePattern, setRulePattern] = useState("");
  const [ruleCatId, setRuleCatId] = useState<number>(categories[0]?.id || 1);
  const [assetName, setAssetName] = useState("");
  const [assetVal, setAssetVal] = useState("");
  const [liabName, setLiabName] = useState("");
  const [liabVal, setLiabVal] = useState("");

  // AI & Data
  const [apiKey, setApiKey] = useState("");
  const [updateMsg, setUpdateMsg] = useState("");

  const loadAll = useCallback(async () => {
    try {
      const [s, g, b, r, nw] = await Promise.all([
        api.settings(),
        api.goals(consolidated ? null : profileId),
        api.budgets(year, month, consolidated, profileId),
        api.rules(),
        api.netWorth(profileId),
      ]);
      setSettings(s);
      setGoals(g.items || []);
      setBudgets(b.items || []);
      setRules(r.items || []);
      setNetWorth(nw);
    } catch {
      onToast("Erro ao carregar configurações.", "error");
    }
  }, [consolidated, profileId, year, month, onToast]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const tabs: Array<{ id: SettingsTab; label: string; icon: typeof Users }> = [
    { id: "accounts", label: "Perfis & Categorias", icon: Users },
    { id: "finance", label: "Metas, Orçamentos & Patrimônio", icon: Target },
    { id: "data", label: "Dados, Privacidade & IA", icon: Shield },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = subtab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setSubtab(t.id)}
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
                active
                  ? "border border-teal-500/35 bg-[var(--accent-soft)] text-[var(--text-primary)]"
                  : "border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Profiles & Categories */}
      {subtab === "accounts" && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="surface-card space-y-4 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Perfis</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newProfile}
                onChange={(e) => setNewProfile(e.target.value)}
                placeholder="Nome do novo perfil"
                className="input-pro flex-1 px-3 py-2 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  if (!newProfile.trim()) return;
                  await api.createProfile(newProfile.trim(), "#14B8A6");
                  setNewProfile("");
                  await onRefreshMeta();
                  onToast("Perfil criado.");
                }}
                className="rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white"
              >
                Adicionar
              </button>
            </div>
            <div className="divide-y divide-[var(--border-subtle)]">
              {profiles.map((p) => (
                <div key={p.id} className="flex items-center justify-between py-2.5 text-xs">
                  <span className="flex items-center gap-2 font-medium text-[var(--text-primary)]">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                    {p.name}
                  </span>
                  {profiles.length > 1 && (
                    <button
                      type="button"
                      onClick={async () => {
                        await api.deleteProfile(p.id);
                        await onRefreshMeta();
                        onToast("Perfil removido.");
                      }}
                      className="rounded p-1 text-[var(--text-muted)] hover:text-red-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="surface-card space-y-4 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Categorias ({categories.length})
            </h3>
            <div className="flex flex-wrap gap-2">
              <input
                type="text"
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
                placeholder="Nova categoria"
                className="input-pro flex-1 px-3 py-2 text-xs"
              />
              <select
                value={newCatType}
                onChange={(e) => setNewCatType(e.target.value as "expense" | "income")}
                className="input-pro px-2.5 py-2 text-xs"
              >
                <option value="expense">Despesa</option>
                <option value="income">Receita</option>
              </select>
              <button
                type="button"
                onClick={async () => {
                  if (!newCatName.trim()) return;
                  await api.createCategory(newCatName.trim(), newCatType, "");
                  setNewCatName("");
                  await onRefreshMeta();
                  onToast("Categoria criada.");
                }}
                className="rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white"
              >
                Adicionar
              </button>
            </div>
            <div className="max-h-72 divide-y divide-[var(--border-subtle)] overflow-y-auto">
              {categories.map((c) => (
                <div key={c.id} className="flex items-center justify-between py-2 text-xs">
                  <span className="text-[var(--text-primary)]">
                    {c.icon ? `${c.icon} ` : ""}
                    {c.name}{" "}
                    <span className="text-[10px] text-[var(--text-muted)]">
                      ({c.type === "income" ? "Receita" : "Despesa"})
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteCategory(c.id);
                      await onRefreshMeta();
                      onToast("Categoria removida.");
                    }}
                    className="rounded p-1 text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Goals, Budgets, Rules, Net Worth */}
      {subtab === "finance" && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {/* Goals */}
          <div className="surface-card space-y-3 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Metas</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newGoalName}
                onChange={(e) => setNewGoalName(e.target.value)}
                placeholder="Nome da meta"
                className="input-pro flex-1 px-3 py-2 text-xs"
              />
              <input
                type="text"
                value={newGoalTarget}
                onChange={(e) => setNewGoalTarget(e.target.value)}
                placeholder="Alvo"
                className="input-pro tabular-nums w-28 px-3 py-2 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  const tgt = Number(newGoalTarget.replace(",", "."));
                  if (!newGoalName.trim() || !tgt) return;
                  await api.createGoal(newGoalName.trim(), tgt, consolidated ? null : profileId);
                  setNewGoalName("");
                  setNewGoalTarget("");
                  await loadAll();
                  onToast("Meta criada.");
                }}
                className="rounded-xl bg-[var(--accent)] px-3.5 py-2 text-xs font-semibold text-white"
              >
                Criar
              </button>
            </div>
            <div className="space-y-2">
              {goals.map((g) => (
                <div
                  key={g.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] px-3 py-2 text-xs"
                >
                  <div>
                    <div className="font-semibold text-[var(--text-primary)]">{g.name}</div>
                    <div className="tabular-nums text-[11px] text-[var(--text-muted)]">
                      {formatMoney(g.current_amount, currency, locale)} /{" "}
                      {formatMoney(g.target_amount, currency, locale)}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteGoal(g.id);
                      await loadAll();
                    }}
                    className="rounded p-1 text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Budgets */}
          <div className="surface-card space-y-3 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Orçamentos ({month}/{year})
            </h3>
            <div className="flex gap-2">
              <select
                value={budgetCatId}
                onChange={(e) => setBudgetCatId(Number(e.target.value))}
                className="input-pro flex-1 px-2.5 py-2 text-xs"
              >
                {categories
                  .filter((c) => c.type === "expense")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
              <input
                type="text"
                value={budgetLimit}
                onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder="Limite"
                className="input-pro tabular-nums w-28 px-3 py-2 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  const lim = Number(budgetLimit.replace(",", "."));
                  if (!lim) return;
                  await api.setBudget({
                    profile_id: consolidated ? null : profileId,
                    category_id: budgetCatId,
                    year,
                    month,
                    limit_amount: lim,
                  });
                  setBudgetLimit("");
                  await loadAll();
                  onToast("Orçamento salvo.");
                }}
                className="rounded-xl bg-[var(--accent)] px-3.5 py-2 text-xs font-semibold text-white"
              >
                Salvar
              </button>
            </div>
            <div className="space-y-2">
              {budgets.map((b) => (
                <div
                  key={b.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] px-3 py-2 text-xs"
                >
                  <div>
                    <div className="font-semibold text-[var(--text-primary)]">
                      {b.category_name}
                    </div>
                    <div className="tabular-nums text-[11px] text-[var(--text-muted)]">
                      {formatMoney(b.spent, currency, locale)} /{" "}
                      {formatMoney(b.limit, currency, locale)} ({b.percentage.toFixed(0)}%)
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteBudget(b.id);
                      await loadAll();
                    }}
                    className="rounded p-1 text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Rules */}
          <div className="surface-card space-y-3 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Regras de categorização automática
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={rulePattern}
                onChange={(e) => setRulePattern(e.target.value)}
                placeholder="Ex.: UBER, IFOOD, NETFLIX"
                className="input-pro flex-1 px-3 py-2 text-xs"
              />
              <select
                value={ruleCatId}
                onChange={(e) => setRuleCatId(Number(e.target.value))}
                className="input-pro w-36 px-2 py-2 text-xs"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={async () => {
                  if (!rulePattern.trim()) return;
                  await api.createRule(rulePattern.trim(), ruleCatId);
                  setRulePattern("");
                  await loadAll();
                  onToast("Regra criada.");
                }}
                className="rounded-xl bg-[var(--accent)] px-3.5 py-2 text-xs font-semibold text-white"
              >
                Criar
              </button>
            </div>
            <div className="max-h-48 divide-y divide-[var(--border-subtle)] overflow-y-auto">
              {rules.map((r) => (
                <div key={r.id} className="flex items-center justify-between py-2 text-xs">
                  <span className="text-[var(--text-primary)]">
                    <strong>{r.pattern}</strong> →{" "}
                    {categories.find((c) => c.id === r.category_id)?.name || r.category_id}
                  </span>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteRule(r.id);
                      await loadAll();
                    }}
                    className="rounded p-1 text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Net Worth */}
          <div className="surface-card space-y-3 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Patrimônio</h3>
              <span className="tabular-nums text-xs font-bold text-emerald-400">
                Líquido:{" "}
                {formatMoney(netWorth?.totals?.net_worth || 0, currency, locale)}
              </span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={assetName}
                onChange={(e) => setAssetName(e.target.value)}
                placeholder="Novo ativo (ex.: Imóvel)"
                className="input-pro flex-1 px-3 py-1.5 text-xs"
              />
              <input
                type="text"
                value={assetVal}
                onChange={(e) => setAssetVal(e.target.value)}
                placeholder="Valor"
                className="input-pro tabular-nums w-24 px-2.5 py-1.5 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  const v = Number(assetVal.replace(",", "."));
                  if (!assetName.trim() || !v) return;
                  await api.createAsset(profileId, assetName.trim(), v);
                  setAssetName("");
                  setAssetVal("");
                  await loadAll();
                }}
                className="rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white"
              >
                + Ativo
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={liabName}
                onChange={(e) => setLiabName(e.target.value)}
                placeholder="Novo passivo (ex.: Financiamento)"
                className="input-pro flex-1 px-3 py-1.5 text-xs"
              />
              <input
                type="text"
                value={liabVal}
                onChange={(e) => setLiabVal(e.target.value)}
                placeholder="Saldo"
                className="input-pro tabular-nums w-24 px-2.5 py-1.5 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  const v = Number(liabVal.replace(",", "."));
                  if (!liabName.trim() || !v) return;
                  await api.createLiability(profileId, liabName.trim(), v);
                  setLiabName("");
                  setLiabVal("");
                  await loadAll();
                }}
                className="rounded-xl bg-orange-600 px-3 py-1.5 text-xs font-semibold text-white"
              >
                + Passivo
              </button>
            </div>
            <div className="max-h-40 divide-y divide-[var(--border-subtle)] overflow-y-auto text-xs">
              {(netWorth?.assets || []).map((a) => (
                <div key={`a-${a.id}`} className="flex items-center justify-between py-1.5">
                  <span className="text-emerald-400">
                    + {a.name} ({formatMoney(a.value, currency, locale)})
                  </span>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteAsset(a.id);
                      await loadAll();
                    }}
                    className="text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {(netWorth?.liabilities || []).map((l) => (
                <div key={`l-${l.id}`} className="flex items-center justify-between py-1.5">
                  <span className="text-orange-400">
                    - {l.name} ({formatMoney(l.balance, currency, locale)})
                  </span>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.deleteLiability(l.id);
                      await loadAll();
                    }}
                    className="text-[var(--text-muted)] hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Data, Privacy, AI, Diagnostics & Updates */}
      {subtab === "data" && settings && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="surface-card space-y-4 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
              <Database className="h-4 w-4 text-[var(--accent)]" />
              Backup, Exportação & Privacidade
            </div>
            <label className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] px-3.5 py-2.5 text-xs">
              <span className="text-[var(--text-primary)]">
                Modo Offline Estrito (bloqueia rede)
              </span>
              <input
                type="checkbox"
                checked={settings.strict_offline}
                onChange={async (e) => {
                  await api.updateSettings({ strict_offline: e.target.checked });
                  await loadAll();
                  onToast("Preferência de privacidade salva.");
                }}
              />
            </label>
            <label className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] px-3.5 py-2.5 text-xs">
              <span className="text-[var(--text-primary)]">
                Backup automático ao fechar
              </span>
              <input
                type="checkbox"
                checked={settings.backup_on_close}
                onChange={async (e) => {
                  await api.updateSettings({ backup_on_close: e.target.checked });
                  await loadAll();
                }}
              />
            </label>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={async () => {
                  const res = await api.createBackup();
                  onToast(`Backup criptografado criado: ${res.path}`);
                  await loadAll();
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-3.5 py-2 text-xs font-semibold text-white"
              >
                <Shield className="h-3.5 w-3.5" />
                Criar backup agora
              </button>
              <button
                type="button"
                onClick={async () => {
                  const res = await api.exportCsv(consolidated ? null : profileId);
                  onToast(`CSV salvo: ${res.path}`);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-strong)] px-3.5 py-2 text-xs font-medium text-[var(--text-primary)]"
              >
                <Download className="h-3.5 w-3.5" />
                Exportar CSV
              </button>
              <button
                type="button"
                onClick={async () => {
                  const res = await api.exportJson(consolidated ? null : profileId);
                  onToast(`JSON salvo: ${res.path}`);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-strong)] px-3.5 py-2 text-xs font-medium text-[var(--text-primary)]"
              >
                <Download className="h-3.5 w-3.5" />
                Exportar JSON
              </button>
            </div>
          </div>

          <div className="surface-card space-y-4 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
              <Sparkles className="h-4 w-4 text-violet-400" />
              Provedor de IA & Suporte
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={settings.ai_provider}
                onChange={async (e) => {
                  await api.updateSettings({ ai_provider: e.target.value });
                  await loadAll();
                }}
                className="input-pro px-3 py-2 text-xs"
              >
                {settings.providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={
                  settings.ai_has_key ? "Chave salva (digite para trocar)" : "API Key"
                }
                className="input-pro px-3 py-2 text-xs"
              />
            </div>
            <button
              type="button"
              onClick={async () => {
                if (!apiKey.trim()) return;
                await api.updateSettings({ ai_api_key: apiKey.trim() });
                setApiKey("");
                await loadAll();
                onToast("Chave de API salva com criptografia local.");
              }}
              className="rounded-xl border border-[var(--border-strong)] px-3.5 py-1.5 text-xs font-semibold text-[var(--text-primary)]"
            >
              Salvar chave de API
            </button>

            <div className="border-t border-[var(--border-subtle)] pt-3 space-y-2.5">
              <div className="text-xs font-semibold text-[var(--accent)]">
                Versão atual: v{version}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    const res = await api.exportDiagnostics();
                    onToast(`Diagnóstico sanitizado salvo: ${res.path}`);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-strong)] px-3 py-1.5 text-xs text-[var(--text-primary)]"
                >
                  <Bug className="h-3.5 w-3.5" />
                  Exportar diagnóstico sanitizado
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    const res = await api.checkUpdates();
                    if (res.status === "offline")
                      setUpdateMsg("Modo offline estrito ativo.");
                    else if (res.status === "update_available")
                      setUpdateMsg(`Nova versão disponível: v${res.latest}`);
                    else if (res.status === "up_to_date")
                      setUpdateMsg(`Você já está na última versão (v${res.current}).`);
                    else setUpdateMsg("Não foi possível verificar agora.");
                  }}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-strong)] px-3 py-1.5 text-xs text-[var(--text-primary)]"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Verificar atualizações
                </button>
              </div>
              {updateMsg && (
                <div className="text-xs text-[var(--text-secondary)]">{updateMsg}</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
