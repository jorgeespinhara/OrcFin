import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeftRight,
  BarChart3,
  CreditCard,
  LayoutDashboard,
  Moon,
  Plus,
  Search,
  Settings,
  Sparkles,
  Sun,
  TrendingUp,
  UploadCloud,
} from "lucide-react";

export type NavTab =
  | "dashboard"
  | "transactions"
  | "import"
  | "cards"
  | "investments"
  | "reports"
  | "mei"
  | "settings";

export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  shortcut?: string;
  icon:
    | "plus"
    | "dashboard"
    | "transactions"
    | "import"
    | "cards"
    | "investments"
    | "reports"
    | "settings"
    | "theme"
    | "demo";
  onSelect: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  theme: "dark" | "light";
  onNewTransaction: () => void;
  onNavigate: (tab: NavTab) => void;
  onToggleTheme: () => void;
  onSeedDemo: () => void;
}

export function CommandPalette({
  open,
  onClose,
  theme,
  onNewTransaction,
  onNavigate,
  onToggleTheme,
  onSeedDemo,
}: CommandPaletteProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);

  const items: CommandItem[] = useMemo(
    () => [
      {
        id: "new-tx",
        label: "Novo lançamento",
        hint: "Registrar receita ou despesa rapidamente",
        shortcut: "Ctrl+N",
        icon: "plus",
        onSelect: onNewTransaction,
      },
      {
        id: "nav-dash",
        label: "Ir para Dashboard",
        hint: "KPIs, fluxo de caixa, categorias e vencimentos",
        shortcut: "G D",
        icon: "dashboard",
        onSelect: () => onNavigate("dashboard"),
      },
      {
        id: "nav-tx",
        label: "Ir para Transações",
        hint: "Buscar, filtrar, editar em lote e desfazer",
        shortcut: "Ctrl+F",
        icon: "transactions",
        onSelect: () => onNavigate("transactions"),
      },
      {
        id: "nav-import",
        label: "Importar extratos (OFX / CSV / PDF)",
        hint: "Arraste extratos bancários com detecção de duplicatas",
        icon: "import",
        onSelect: () => onNavigate("import"),
      },
      {
        id: "nav-cards",
        label: "Ir para Cartões de Crédito",
        hint: "Faturas do mês e limites disponíveis",
        icon: "cards",
        onSelect: () => onNavigate("cards"),
      },
      {
        id: "nav-investments",
        label: "Ir para Investimentos",
        hint: "Carteira, alocação por classe e cotações",
        icon: "investments",
        onSelect: () => onNavigate("investments"),
      },
      {
        id: "nav-reports",
        label: "Ir para Relatórios & IA",
        hint: "Sazonalidade, simulador, PDF e análise com IA",
        icon: "reports",
        onSelect: () => onNavigate("reports"),
      },
      {
        id: "nav-settings",
        label: "Ir para Configurações",
        hint: "Perfis, metas, orçamentos, backup e diagnóstico",
        icon: "settings",
        onSelect: () => onNavigate("settings"),
      },
      {
        id: "toggle-theme",
        label: theme === "dark" ? "Mudar para Tema Claro" : "Mudar para Tema Escuro",
        hint: "Alterna instantaneamente a aparência",
        icon: "theme",
        onSelect: onToggleTheme,
      },
      {
        id: "seed-demo",
        label: "Popular dados de demonstração",
        hint: "Adiciona lançamentos fictícios para explorar gráficos",
        icon: "demo",
        onSelect: onSeedDemo,
      },
    ],
    [onNavigate, onNewTransaction, onSeedDemo, onToggleTheme, theme]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        i.label.toLowerCase().includes(q) ||
        (i.hint || "").toLowerCase().includes(q)
    );
  }, [items, query]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setQuery("");
      setActiveIdx(0);
      dialog.showModal();
      setTimeout(() => inputRef.current?.focus(), 20);
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const onCloseEvt = () => {
      dialog.returnValue = "";
      onClose();
    };
    dialog.addEventListener("close", onCloseEvt);
    return () => dialog.removeEventListener("close", onCloseEvt);
  }, [onClose]);

  const runItem = (item: CommandItem) => {
    dialogRef.current?.close();
    item.onSelect();
  };

  const renderIcon = (kind: CommandItem["icon"]) => {
    switch (kind) {
      case "plus":
        return <Plus className="h-4 w-4 text-[var(--accent)]" />;
      case "dashboard":
        return <LayoutDashboard className="h-4 w-4 text-[var(--indigo)]" />;
      case "transactions":
        return <ArrowLeftRight className="h-4 w-4 text-[var(--accent)]" />;
      case "import":
        return <UploadCloud className="h-4 w-4 text-teal-400" />;
      case "cards":
        return <CreditCard className="h-4 w-4 text-violet-400" />;
      case "investments":
        return <TrendingUp className="h-4 w-4 text-emerald-400" />;
      case "reports":
        return <BarChart3 className="h-4 w-4 text-indigo-400" />;
      case "settings":
        return <Settings className="h-4 w-4 text-[var(--text-secondary)]" />;
      case "theme":
        return theme === "dark" ? (
          <Sun className="h-4 w-4 text-amber-400" />
        ) : (
          <Moon className="h-4 w-4 text-indigo-400" />
        );
      case "demo":
        return <Sparkles className="h-4 w-4 text-emerald-400" />;
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-label="Paleta de comandos"
      className="orcfin-dialog w-[540px]"
      {...({ closedby: "any" } as Record<string, string>)}
    >
      <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <Search className="h-4 w-4 text-[var(--text-muted)]" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIdx(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActiveIdx((idx) => (idx + 1) % Math.max(1, filtered.length));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActiveIdx((idx) =>
                (idx - 1 + Math.max(1, filtered.length)) % Math.max(1, filtered.length)
              );
            } else if (e.key === "Enter" && filtered[activeIdx]) {
              e.preventDefault();
              runItem(filtered[activeIdx]);
            }
          }}
          placeholder="Digite um comando ou navegue..."
          className="w-full bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
        />
        <kbd className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
          ESC
        </kbd>
      </div>

      <div className="max-h-80 overflow-y-auto p-2">
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-xs text-[var(--text-muted)]">
            Nenhum comando encontrado.
          </p>
        ) : (
          filtered.map((item, idx) => (
            <button
              key={item.id}
              type="button"
              onMouseEnter={() => setActiveIdx(idx)}
              onClick={() => runItem(item)}
              className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                idx === activeIdx
                  ? "bg-[var(--accent-soft)] text-[var(--text-primary)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-hover)]"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)]">
                  {renderIcon(item.icon)}
                </div>
                <div>
                  <div className="text-sm font-medium text-[var(--text-primary)]">
                    {item.label}
                  </div>
                  {item.hint && (
                    <div className="text-xs text-[var(--text-muted)]">{item.hint}</div>
                  )}
                </div>
              </div>
              {item.shortcut && (
                <kbd className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-solid)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-muted)]">
                  {item.shortcut}
                </kbd>
              )}
            </button>
          ))
        )}
      </div>
    </dialog>
  );
}
