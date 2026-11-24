import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  FileCode2,
  Receipt,
  Settings2,
  Trash2,
  Users,
} from "lucide-react";
import { api, type MeiOverviewResponse } from "../lib/api";
import { formatMoney } from "../lib/format";

interface MeiViewProps {
  currency: string;
  locale: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
}

export function MeiView({ currency, locale, onToast }: MeiViewProps) {
  const [data, setData] = useState<MeiOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [subtab, setSubtab] = useState<"home" | "invoices" | "config">("home");

  // Setup / Config form
  const [razao, setRazao] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [activity, setActivity] = useState<"servico" | "comercio" | "misto">("servico");
  const [opProfile, setOpProfile] = useState<"on_demand" | "recurring" | "inventory" | "hybrid">("on_demand");
  const [dasDay, setDasDay] = useState("20");

  // Quick client & invoice forms
  const [clientName, setClientName] = useState("");
  const [clientDoc, setClientDoc] = useState("");
  const [invNum, setInvNum] = useState("");
  const [invAmount, setInvAmount] = useState("");
  const [invDesc, setInvDesc] = useState("");
  const [invClientId, setInvClientId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.meiOverview();
      setData(res);
      if (res.configured && res.config) {
        setRazao(res.config.razao_social);
        setCnpj(res.config.cnpj);
        setActivity(res.config.activity_type);
        setOpProfile(res.config.operational_profile);
        setDasDay(String(res.config.das_day || 20));
      }
    } catch {
      onToast("Erro ao carregar módulo MEI.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!razao.trim() || !cnpj.trim()) {
      onToast("Informe Razão Social e CNPJ.", "error");
      return;
    }
    try {
      await api.meiSetup({
        razao_social: razao.trim(),
        cnpj: cnpj.trim(),
        activity_type: activity,
        operational_profile: opProfile,
        das_day: Number(dasDay) || 20,
      });
      onToast("Configuração MEI salva!");
      setSubtab("home");
      await load();
    } catch {
      onToast("Erro ao salvar dados do MEI.", "error");
    }
  };

  const handleXmlUpload = async (file: File) => {
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let bin = "";
      for (let i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      }
      const res = await api.meiImportNfeXml(btoa(bin));
      onToast(`NF-e ${res.invoice_number} importada!`);
      await load();
    } catch {
      onToast("Não foi possível importar o XML NF-e.", "error");
    }
  };

  if (loading && !data) {
    return <div className="surface-card h-80 animate-pulse rounded-2xl" />;
  }

  if (!data?.configured) {
    return (
      <div className="surface-card mx-auto max-w-lg rounded-2xl border-amber-500/30 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 text-amber-400">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[var(--text-primary)]">
              Ativar OrcFin MEI
            </h2>
            <p className="text-xs text-[var(--text-muted)]">
              Configure seu CNPJ para acompanhar DAS, teto de R$ 81.000, notas e clientes.
            </p>
          </div>
        </div>
        <form onSubmit={handleSaveSetup} className="mt-5 space-y-3.5">
          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Razão Social / Nome Fantasia
            </label>
            <input
              type="text"
              value={razao}
              onChange={(e) => setRazao(e.target.value)}
              placeholder="Ex.: Jorge Silva Serviços MEI"
              className="input-pro w-full px-3.5 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                CNPJ
              </label>
              <input
                type="text"
                value={cnpj}
                onChange={(e) => setCnpj(e.target.value)}
                placeholder="00.000.000/0001-00"
                className="input-pro w-full px-3.5 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Atividade
              </label>
              <select
                value={activity}
                onChange={(e) => setActivity(e.target.value as "servico" | "comercio" | "misto")}
                className="input-pro w-full px-3 py-2 text-sm"
              >
                <option value="servico">Prestação de Serviços</option>
                <option value="comercio">Comércio / Indústria</option>
                <option value="misto">Comércio e Serviços</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            className="w-full rounded-xl bg-amber-500 py-2.5 text-xs font-semibold text-slate-950 shadow-lg shadow-amber-500/20 transition hover:brightness-110"
          >
            Criar perfil MEI
          </button>
        </form>
      </div>
    );
  }

  const dash = data.dashboard!;
  const lim = data.limit_status!;
  const das = data.das!;
  const pctLimit = Math.min(100, Math.max(0, lim.percentage || 0));

  return (
    <div className="space-y-5">
      {/* Header + Subtabs */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/15 text-amber-400">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-[var(--text-primary)]">
              {data.config?.razao_social}
            </div>
            <div className="text-xs text-[var(--text-muted)]">
              CNPJ {data.config?.cnpj} · Atividade: {data.config?.activity_type}
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {(
            [
              ["home", "Visão Geral", Building2],
              ["invoices", "Notas & Clientes", Receipt],
              ["config", "Configuração", Settings2],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setSubtab(id)}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                subtab === id
                  ? "border border-amber-500/40 bg-amber-500/15 text-amber-300"
                  : "border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Subtab 1: Overview */}
      {subtab === "home" && (
        <div className="space-y-4">
          {/* DAS Alert */}
          <div
            className={`surface-card flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4 ${
              das.paid ? "border-emerald-500/30" : "border-amber-500/40"
            }`}
          >
            <div className="flex items-center gap-3">
              {das.paid ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-400" />
              )}
              <div>
                <div className="text-xs font-semibold text-[var(--text-primary)]">
                  {das.paid
                    ? "DAS deste mês pago e registrado!"
                    : `DAS pendente — vence em ${das.info?.days_left ?? "?"} dia(s)`}
                </div>
                <div className="tabular-nums text-[11px] text-[var(--text-muted)]">
                  Valor estimado: {formatMoney(das.amount, currency, locale)}
                </div>
              </div>
            </div>
            {!das.paid && (
              <button
                type="button"
                onClick={async () => {
                  await api.meiConfirmDas();
                  onToast("Pagamento do DAS registrado!");
                  await load();
                }}
                className="rounded-xl bg-amber-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:brightness-110"
              >
                Confirmar pagamento do DAS
              </button>
            )}
          </div>

          {/* 4 KPIs */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Faturamento (mês)", val: dash.month_income, color: "text-emerald-400" },
              { label: "Despesas MEI (mês)", val: dash.month_expense, color: "text-orange-400" },
              {
                label: "Resultado simplificado",
                val: data.report?.simplified_result ?? 0,
                color: "text-amber-400",
              },
              { label: "Ticket médio", val: dash.ticket_medio, color: "text-indigo-400" },
            ].map((k) => (
              <div key={k.label} className="surface-card rounded-2xl p-5">
                <div className="text-xs text-[var(--text-muted)]">{k.label}</div>
                <div className={`tabular-nums mt-2 text-2xl font-bold ${k.color}`}>
                  {formatMoney(k.val, currency, locale)}
                </div>
              </div>
            ))}
          </div>

          {/* Annual Limit Progress Bar */}
          <div className="surface-card rounded-2xl p-5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-[var(--text-primary)]">
                Teto anual MEI ({pctLimit.toFixed(1)}%)
              </span>
              <span className="tabular-nums text-[var(--text-muted)]">
                <strong className="text-[var(--text-primary)]">
                  {formatMoney(lim.ytd_revenue, currency, locale)}
                </strong>{" "}
                / {formatMoney(lim.annual_limit, currency, locale)}
              </span>
            </div>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[var(--bg-surface-hover)]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pctLimit}%` }}
                transition={{ duration: 0.6 }}
                className="h-full rounded-full"
                style={{
                  backgroundColor: lim.at_risk ? "#ef4444" : "#f59e0b",
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Subtab 2: Invoices & Clients */}
      {subtab === "invoices" && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="surface-card space-y-4 rounded-2xl p-5 xl:col-span-7">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Notas fiscais ({data.invoices?.length || 0})
              </h3>
              <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300">
                <FileCode2 className="h-3.5 w-3.5" />
                Importar NF-e XML
                <input
                  type="file"
                  accept=".xml"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleXmlUpload(f);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <input
                type="text"
                value={invNum}
                onChange={(e) => setInvNum(e.target.value)}
                placeholder="Nº NF"
                className="input-pro px-3 py-1.5 text-xs"
              />
              <input
                type="text"
                value={invAmount}
                onChange={(e) => setInvAmount(e.target.value)}
                placeholder="Valor"
                className="input-pro tabular-nums px-3 py-1.5 text-xs"
              />
              <select
                value={invClientId}
                onChange={(e) => setInvClientId(e.target.value)}
                className="input-pro px-2 py-1.5 text-xs"
              >
                <option value="">Sem cliente</option>
                {(data.clients || []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={async () => {
                  const val = Number(invAmount.replace(",", "."));
                  if (!invNum.trim() || !val) return;
                  await api.meiCreateInvoice({
                    invoice_number: invNum.trim(),
                    issue_date: new Date().toISOString().slice(0, 10),
                    amount: val,
                    description: invDesc.trim(),
                    client_id: invClientId ? Number(invClientId) : null,
                  });
                  setInvNum("");
                  setInvAmount("");
                  setInvDesc("");
                  await load();
                  onToast("Nota registrada.");
                }}
                className="rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-950"
              >
                + Nota
              </button>
            </div>

            <div className="max-h-72 divide-y divide-[var(--border-subtle)] overflow-y-auto text-xs">
              {(data.invoices || []).map((inv) => (
                <div key={inv.id} className="flex items-center justify-between gap-2 py-2.5">
                  <div>
                    <div className="font-semibold text-[var(--text-primary)]">
                      NF {inv.invoice_number} · {inv.issue_date}
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      {inv.client_name || inv.description || "Sem cliente"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums font-semibold text-[var(--text-primary)]">
                      {formatMoney(inv.amount, currency, locale)}
                    </span>
                    {!inv.paid_at ? (
                      <button
                        type="button"
                        onClick={async () => {
                          await api.meiReceiveInvoice(inv.id);
                          onToast("Recebimento registrado no caixa MEI!");
                          await load();
                        }}
                        className="rounded-lg bg-emerald-500/20 px-2 py-1 text-[11px] font-semibold text-emerald-400"
                      >
                        Receber
                      </button>
                    ) : (
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                        Pago
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={async () => {
                        await api.meiDeleteInvoice(inv.id);
                        await load();
                      }}
                      className="text-[var(--text-muted)] hover:text-red-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-card space-y-4 rounded-2xl p-5 xl:col-span-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
              <Users className="h-4 w-4 text-amber-400" />
              Clientes ({data.clients?.length || 0})
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="Nome do cliente"
                className="input-pro flex-1 px-3 py-1.5 text-xs"
              />
              <input
                type="text"
                value={clientDoc}
                onChange={(e) => setClientDoc(e.target.value)}
                placeholder="CPF/CNPJ"
                className="input-pro w-32 px-2.5 py-1.5 text-xs"
              />
              <button
                type="button"
                onClick={async () => {
                  if (!clientName.trim()) return;
                  await api.meiCreateClient({ name: clientName.trim(), document: clientDoc.trim() });
                  setClientName("");
                  setClientDoc("");
                  await load();
                  onToast("Cliente cadastrado.");
                }}
                className="rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-950"
              >
                +
              </button>
            </div>
            <div className="max-h-72 divide-y divide-[var(--border-subtle)] overflow-y-auto text-xs">
              {(data.clients || []).map((c) => (
                <div key={c.id} className="flex items-center justify-between py-2">
                  <div>
                    <div className="font-medium text-[var(--text-primary)]">{c.name}</div>
                    {c.document && (
                      <div className="text-[11px] text-[var(--text-muted)]">{c.document}</div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={async () => {
                      await api.meiDeleteClient(c.id);
                      await load();
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

      {/* Subtab 3: Config */}
      {subtab === "config" && (
        <form onSubmit={handleSaveSetup} className="surface-card max-w-lg space-y-3.5 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            Dados do MEI
          </h3>
          <input
            type="text"
            value={razao}
            onChange={(e) => setRazao(e.target.value)}
            placeholder="Razão Social"
            className="input-pro w-full px-3.5 py-2 text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="CNPJ"
              className="input-pro w-full px-3.5 py-2 text-sm"
            />
            <input
              type="number"
              min={1}
              max={28}
              value={dasDay}
              onChange={(e) => setDasDay(e.target.value)}
              placeholder="Dia DAS"
              className="input-pro w-full px-3.5 py-2 text-sm"
            />
          </div>
          <select
            value={activity}
            onChange={(e) => setActivity(e.target.value as "servico" | "comercio" | "misto")}
            className="input-pro w-full px-3 py-2 text-sm"
          >
            <option value="servico">Prestação de Serviços</option>
            <option value="comercio">Comércio / Indústria</option>
            <option value="misto">Comércio e Serviços</option>
          </select>
          <button
            type="submit"
            className="rounded-xl bg-amber-500 px-5 py-2 text-xs font-semibold text-slate-950"
          >
            Salvar alterações
          </button>
        </form>
      )}
    </div>
  );
}
