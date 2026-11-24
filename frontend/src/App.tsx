import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeftRight,
  BarChart3,
  Building2,
  ChevronLeft,
  ChevronRight,
  Command,
  CreditCard,
  LayoutDashboard,
  Moon,
  Plus,
  Settings,
  ShieldCheck,
  Sun,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import {
  api,
  type DashboardData,
  type MetaResponse,
  type TransactionItem,
  type TransactionPayload,
  type TransactionsResponse,
} from "./lib/api";
import { monthName } from "./lib/format";
import { DashboardView } from "./views/DashboardView";
import { TransactionsView } from "./views/TransactionsView";
import { ImportView } from "./views/ImportView";
import { CardsView } from "./views/CardsView";
import { InvestmentsView } from "./views/InvestmentsView";
import { ReportsView } from "./views/ReportsView";
import { MeiView } from "./views/MeiView";
import { SettingsView } from "./views/SettingsView";
import { TransactionModal } from "./components/TransactionModal";
import { CommandPalette, type NavTab } from "./components/CommandPalette";
import { OnboardingModal } from "./components/OnboardingModal";
import { Toast, type ToastState } from "./components/Toast";
import { Modal } from "./components/Modal";

type ActiveTab = NavTab;

export function App() {
  const now = new Date();
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [tab, setTab] = useState<ActiveTab>("dashboard");
  const [consolidated, setConsolidated] = useState(true);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState<number | null>(now.getMonth() + 1);

  const [dashData, setDashData] = useState<DashboardData | null>(null);
  const [dashLoading, setDashLoading] = useState(true);
  const [txData, setTxData] = useState<TransactionsResponse | null>(null);
  const [txLoading, setTxLoading] = useState(false);

  // Transaction filters
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "income" | "expense">("all");
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  const [cardFilter, setCardFilter] = useState<number | null>(null);
  const [sortOrder, setSortOrder] = useState<
    "date_desc" | "date_asc" | "amount_desc" | "amount_asc"
  >("date_desc");

  // Modals & UI chrome
  const [txModalOpen, setTxModalOpen] = useState(false);
  const [editingTx, setEditingTx] = useState<TransactionItem | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const toastTimer = useRef<number | null>(null);

  const showToast = useCallback(
    (
      message: string,
      kind: "success" | "error" = "success",
      action?: { label: string; onAction: () => void },
      durationMs?: number
    ) => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
      const id = Date.now();
      setToast({
        id,
        message,
        kind,
        actionLabel: action?.label,
        onAction: action?.onAction,
      });
      toastTimer.current = window.setTimeout(
        () => setToast((cur) => (cur?.id === id ? null : cur)),
        durationMs ?? (action ? 5200 : 3000)
      );
    },
    []
  );

  // Apply theme attribute on <html>
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  // Debounce search
  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQuery(searchQuery), 260);
    return () => window.clearTimeout(id);
  }, [searchQuery]);

  // Load metadata on mount
  const loadMeta = useCallback(async () => {
    try {
      const m = await api.meta();
      setMeta(m);
      setTheme(m.theme_mode === "light" ? "light" : "dark");
      if (m.onboarding_completed === false) {
        setOnboardingOpen(true);
      }
      if (m.profiles.length && profileId === null) {
        setProfileId(m.profiles[0].id);
      }
    } catch {
      showToast("Erro ao conectar ao motor local do OrcFin.", "error");
    }
  }, [profileId, showToast]);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  const loadDashboard = useCallback(async () => {
    setDashLoading(true);
    try {
      const d = await api.dashboard({
        profile_id: profileId,
        consolidated,
        year,
        month,
      });
      setDashData(d);
    } catch {
      showToast("Não foi possível carregar o Dashboard.", "error");
    } finally {
      setDashLoading(false);
    }
  }, [profileId, consolidated, year, month, showToast]);

  const loadTransactions = useCallback(async () => {
    setTxLoading(true);
    try {
      const r = await api.transactions({
        profile_id: profileId,
        consolidated,
        year,
        month,
        q: debouncedQuery,
        type_filter: typeFilter,
        category_id: categoryFilter,
        card_id: cardFilter,
        sort: sortOrder,
      });
      setTxData(r);
    } catch {
      showToast("Não foi possível carregar as transações.", "error");
    } finally {
      setTxLoading(false);
    }
  }, [
    profileId,
    consolidated,
    year,
    month,
    debouncedQuery,
    typeFilter,
    categoryFilter,
    cardFilter,
    sortOrder,
    showToast,
  ]);

  useEffect(() => {
    if (tab === "dashboard") loadDashboard();
    else loadTransactions();
  }, [tab, loadDashboard, loadTransactions]);

  const refreshActive = useCallback(async () => {
    await Promise.all([loadDashboard(), loadTransactions()]);
  }, [loadDashboard, loadTransactions]);

  // Global keyboard shortcuts (Ctrl+K, Ctrl+N, Ctrl+F)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const key = e.key.toLowerCase();
      if (key === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      } else if (key === "n") {
        e.preventDefault();
        setEditingTx(null);
        setTxModalOpen(true);
      } else if (key === "f") {
        e.preventDefault();
        setTab("transactions");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const toggleTheme = async () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      await api.setTheme(next);
    } catch {
      /* local only */
    }
  };

  const shiftMonth = (delta: number) => {
    if (month === null) {
      setYear((y) => y + delta);
      return;
    }
    const next = month + delta;
    if (next < 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else if (next > 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else {
      setMonth(next);
    }
  };

  const handleSaveTx = async (payload: TransactionPayload, editingId: number | null) => {
    if (editingId) {
      await api.updateTransaction(editingId, payload);
      showToast("Lançamento atualizado.");
    } else {
      await api.createTransaction(payload);
      showToast("Lançamento adicionado.");
    }
    await refreshActive();
  };

  const handleSoftDelete = async (tx: TransactionItem) => {
    try {
      await api.softDeleteTransaction(tx.id);
      await refreshActive();
      showToast(`Removido: ${tx.description}`, "success", {
        label: "Desfazer",
        onAction: async () => {
          await api.restoreTransactions([tx.id]);
          await refreshActive();
          showToast("Lançamento restaurado.");
        },
      });
    } catch {
      showToast("Erro ao remover lançamento.", "error");
    }
  };

  const handleSeedDemo = async () => {
    try {
      const res = await api.seedDemo();
      await loadMeta();
      await refreshActive();
      showToast(`${res.seeded} lançamentos de demonstração carregados!`);
    } catch {
      showToast("Erro ao carregar dados demo.", "error");
    }
  };

  const currency = meta?.currency || "BRL";
  const locale = meta?.locale || "pt-BR";

  const navItems: Array<{ id: ActiveTab; label: string; icon: typeof LayoutDashboard }> = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "transactions", label: "Transações", icon: ArrowLeftRight },
    { id: "import", label: "Importar", icon: UploadCloud },
    { id: "cards", label: "Cartões", icon: CreditCard },
    { id: "investments", label: "Investimentos", icon: TrendingUp },
    { id: "reports", label: "Relatórios & IA", icon: BarChart3 },
    ...(meta?.mei_available !== false
      ? [{ id: "mei" as ActiveTab, label: "MEI", icon: Building2 }]
      : []),
    { id: "settings", label: "Configurações", icon: Settings },
  ];

  const tabTitles: Record<ActiveTab, string> = {
    dashboard: "Dashboard",
    transactions: "Transações",
    import: "Importar Extratos",
    cards: "Cartões de Crédito",
    investments: "Investimentos",
    reports: "Relatórios & IA",
    mei: "OrcFin MEI",
    settings: "Configurações",
  };
  const activeProfileId = profileId || meta?.profiles[0]?.id || 1;

  return (
    <div className="app-ambient-bg flex h-screen w-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-sidebar)] px-3.5 py-5">
        <div className="flex items-center gap-2.5 px-2">
          <img
            src="/orcfin_logo.png"
            alt="OrcFin"
            className="h-9 w-9 rounded-xl object-contain shadow-lg shadow-teal-500/20"
          />
          <div>
            <div className="text-sm font-bold tracking-tight text-[var(--text-primary)]">
              {meta?.app_name || "OrcFin"}
            </div>
            <div className="text-[11px] text-[var(--text-muted)]">
              Finanças locais
            </div>
          </div>
        </div>

        {/* Command Palette Trigger */}
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="mt-5 flex items-center justify-between rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)] px-3 py-2 text-xs text-[var(--text-muted)] transition hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
        >
          <span className="flex items-center gap-2">
            <Command className="h-3.5 w-3.5" />
            Comando rápido
          </span>
          <kbd className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px]">
            Ctrl+K
          </kbd>
        </button>

        {/* Navigation */}
        <nav className="mt-5 flex-1 space-y-1">
          {navItems.map((item) => {
            const active = tab === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? "text-[var(--text-primary)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="active-nav"
                    transition={{ type: "spring", stiffness: 420, damping: 32 }}
                    className="absolute inset-0 rounded-xl border border-teal-500/25 bg-[var(--accent-soft)]"
                  />
                )}
                <Icon className={`relative z-10 h-4 w-4 ${active ? "text-[var(--accent)]" : ""}`} />
                <span className="relative z-10">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Bottom chrome: privacy badge + theme + version */}
        <div className="space-y-2 border-t border-[var(--border-subtle)] pt-3">
          <div className="flex items-center gap-2 px-2 text-[11px] text-[var(--text-muted)]">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            100% Local · SQLite
          </div>
          <div className="flex items-center justify-between px-1">
            <button
              type="button"
              onClick={toggleTheme}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-[var(--text-muted)] transition hover:bg-[var(--bg-surface-hover)] hover:text-[var(--text-primary)]"
            >
              {theme === "dark" ? (
                <>
                  <Sun className="h-3.5 w-3.5 text-amber-400" />
                  Claro
                </>
              ) : (
                <>
                  <Moon className="h-3.5 w-3.5 text-indigo-400" />
                  Escuro
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => setAboutOpen(true)}
              className="rounded-lg px-2 py-1 text-[11px] font-medium text-[var(--text-muted)] transition hover:bg-[var(--bg-surface-hover)] hover:text-[var(--text-primary)]"
            >
              v{meta?.version || "1.0.0"}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Clean Header */}
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] px-7 py-4">
          <div>
            <h1 className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
              {tabTitles[tab]}
            </h1>
            <p className="text-xs text-[var(--text-muted)]">
              {consolidated
                ? "Visão consolidada"
                : meta?.profiles.find((p) => p.id === profileId)?.name || "Individual"}{" "}
              · {month ? `${monthName(month)} ${year}` : `Ano ${year}`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Scope selector */}
            <select
              value={consolidated ? "consolidated" : String(profileId || "")}
              onChange={(e) => {
                if (e.target.value === "consolidated") {
                  setConsolidated(true);
                } else {
                  setConsolidated(false);
                  setProfileId(Number(e.target.value));
                }
              }}
              className="input-pro px-3 py-1.5 text-xs font-medium"
            >
              <option value="consolidated">Todos os perfis (Consolidado)</option>
              {(meta?.profiles || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {/* Period selector */}
            <div className="inline-flex items-center rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)]">
              <button
                type="button"
                onClick={() => shiftMonth(-1)}
                aria-label="Período anterior"
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setMonth((m) => (m === null ? now.getMonth() + 1 : null))}
                title="Alternar mês / ano inteiro"
                className="min-w-[116px] px-2 py-1 text-center text-xs font-semibold text-[var(--text-primary)]"
              >
                {month ? `${monthName(month)} ${year}` : `Ano ${year}`}
              </button>
              <button
                type="button"
                onClick={() => shiftMonth(1)}
                aria-label="Próximo período"
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                setEditingTx(null);
                setTxModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-3.5 py-2 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 transition hover:brightness-110"
            >
              <Plus className="h-3.5 w-3.5" />
              Lançamento
            </button>
          </div>
        </header>

        {/* Scrollable View Body */}
        <main className="flex-1 overflow-y-auto px-7 py-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              {tab === "dashboard" ? (
                <DashboardView
                  data={dashData}
                  loading={dashLoading}
                  currency={currency}
                  locale={locale}
                  onSelectCategory={(catId) => {
                    setCategoryFilter(catId);
                    setTypeFilter("expense");
                    setTab("transactions");
                  }}
                  onOpenTransactions={() => setTab("transactions")}
                  onNewTransaction={() => {
                    setEditingTx(null);
                    setTxModalOpen(true);
                  }}
                  onSeedDemo={handleSeedDemo}
                />
              ) : tab === "transactions" ? (
                <TransactionsView
                  data={txData}
                  loading={txLoading}
                  currency={currency}
                  locale={locale}
                  consolidated={consolidated}
                  categories={meta?.categories || []}
                  cards={meta?.credit_cards || []}
                  query={searchQuery}
                  onQueryChange={setSearchQuery}
                  typeFilter={typeFilter}
                  onTypeFilterChange={setTypeFilter}
                  categoryFilter={categoryFilter}
                  onCategoryFilterChange={setCategoryFilter}
                  cardFilter={cardFilter}
                  onCardFilterChange={setCardFilter}
                  sortOrder={sortOrder}
                  onSortOrderChange={setSortOrder}
                  onNewTransaction={() => {
                    setEditingTx(null);
                    setTxModalOpen(true);
                  }}
                  onEditTransaction={(tx) => {
                    setEditingTx(tx);
                    setTxModalOpen(true);
                  }}
                  onSoftDeleteOne={handleSoftDelete}
                  onBatchCategory={async (ids, catId) => {
                    const res = await api.batchCategory(ids, catId);
                    await refreshActive();
                    showToast(`${res.updated} lançamento(s) atualizado(s).`);
                  }}
                  onBatchDelete={async (ids) => {
                    const res = await api.batchDelete(ids);
                    await refreshActive();
                    showToast(`${res.deleted} lançamento(s) excluído(s).`);
                  }}
                />
              ) : tab === "import" ? (
                <ImportView
                  profiles={meta?.profiles || []}
                  categories={meta?.categories || []}
                  cards={meta?.credit_cards || []}
                  defaultProfileId={activeProfileId}
                  currency={currency}
                  locale={locale}
                  onToast={(m, k) => showToast(m, k)}
                  onImported={() => {
                    refreshActive();
                    setTab("transactions");
                  }}
                />
              ) : tab === "cards" ? (
                <CardsView
                  profileId={activeProfileId}
                  consolidated={consolidated}
                  year={year}
                  month={month}
                  profiles={meta?.profiles || []}
                  currency={currency}
                  locale={locale}
                  onToast={(m, k) => showToast(m, k)}
                  onMutated={() => {
                    loadMeta();
                    refreshActive();
                  }}
                />
              ) : tab === "investments" ? (
                <InvestmentsView
                  profileId={activeProfileId}
                  currency={currency}
                  locale={locale}
                  onToast={(m, k) => showToast(m, k)}
                />
              ) : tab === "reports" ? (
                <ReportsView
                  profileId={activeProfileId}
                  consolidated={consolidated}
                  year={year}
                  month={month}
                  currency={currency}
                  locale={locale}
                  onToast={(m, k) => showToast(m, k)}
                />
              ) : tab === "mei" ? (
                <MeiView
                  currency={currency}
                  locale={locale}
                  onToast={(m, k) => showToast(m, k)}
                />
              ) : (
                <SettingsView
                  profiles={meta?.profiles || []}
                  categories={meta?.categories || []}
                  profileId={activeProfileId}
                  consolidated={consolidated}
                  year={year}
                  month={month || now.getMonth() + 1}
                  currency={currency}
                  locale={locale}
                  version={meta?.version || "1.0.0"}
                  onToast={(m, k) => showToast(m, k)}
                  onRefreshMeta={async () => {
                    await loadMeta();
                    await refreshActive();
                  }}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Modals & Overlays */}
      <TransactionModal
        open={txModalOpen}
        onClose={() => setTxModalOpen(false)}
        editing={editingTx}
        profiles={meta?.profiles || []}
        categories={meta?.categories || []}
        cards={meta?.credit_cards || []}
        defaultProfileId={profileId}
        onSave={handleSaveTx}
      />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        theme={theme}
        onNewTransaction={() => {
          setEditingTx(null);
          setTxModalOpen(true);
        }}
        onNavigate={(next) => setTab(next)}
        onToggleTheme={toggleTheme}
        onSeedDemo={handleSeedDemo}
      />

      <Modal
        open={aboutOpen}
        onClose={() => setAboutOpen(false)}
        title="Sobre o OrcFin"
        widthClass="w-[400px]"
      >
        <div className="space-y-3 text-xs text-[var(--text-secondary)]">
          <div className="flex items-center gap-3">
            <img
              src="/orcfin_logo.png"
              alt="OrcFin"
              className="h-10 w-10 rounded-xl object-contain"
            />
            <div>
              <div className="text-sm font-bold text-[var(--text-primary)]">
                OrcFin v{meta?.version || "1.0.0"}
              </div>
              <div className="text-[11px] text-[var(--accent)]">
                Interface PRO (React + WebView2) · Schema v{meta?.schema_version || 15}
              </div>
            </div>
          </div>
          <p className="leading-relaxed text-[var(--text-muted)]">
            Orçamento financeiro 100% local (SQLite), sem nuvem obrigatória e sem telemetria.
          </p>
          <div className="border-t border-[var(--border-subtle)] pt-2 text-[11px] text-[var(--text-muted)]">
            Licença: GNU GPL v3.0
          </div>
        </div>
      </Modal>

      <OnboardingModal
        open={onboardingOpen}
        onToast={(m, k) => showToast(m, k)}
        onComplete={async ({ openImport, openMei }) => {
          setOnboardingOpen(false);
          await loadMeta();
          await refreshActive();
          if (openImport) setTab("import");
          else if (openMei) setTab("mei");
        }}
      />

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

export default App;
