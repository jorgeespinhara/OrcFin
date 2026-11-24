import { useState } from "react";
import { Building2, PlayCircle, RotateCcw, Sparkles, UploadCloud, User } from "lucide-react";
import { Modal } from "./Modal";
import { api } from "../lib/api";

interface OnboardingModalProps {
  open: boolean;
  onComplete: (opts: { openImport?: boolean; openMei?: boolean }) => Promise<void>;
  onToast: (msg: string, kind?: "success" | "error") => void;
}

export function OnboardingModal({ open, onComplete, onToast }: OnboardingModalProps) {
  const [step, setStep] = useState(0);
  const [country, setCountry] = useState<"BR" | "US" | "ES">("BR");
  const [mode, setMode] = useState<"personal" | "mei" | "both">("personal");
  const [backupOnClose, setBackupOnClose] = useState(true);
  const [busy, setBusy] = useState(false);

  const finish = async (useDemo: boolean, openImport = false) => {
    setBusy(true);
    try {
      await api.completeOnboarding({
        country,
        setup_mode: country === "BR" ? mode : "personal",
        use_demo: useDemo,
        backup_on_close: backupOnClose,
      });
      await onComplete({ openImport, openMei: country === "BR" && mode === "mei" });
    } catch {
      onToast("Erro ao finalizar configuração inicial.", "error");
    } finally {
      setBusy(false);
    }
  };

  const handleRestoreFile = async (file: File) => {
    setBusy(true);
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let bin = "";
      for (let i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      }
      await api.restoreBackup(file.name, btoa(bin));
      onToast("Backup restaurado com sucesso!");
      await onComplete({});
    } catch {
      onToast("Não foi possível restaurar o backup.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => finish(false)}
      title="Bem-vindo ao OrcFin v1.0.0"
      subtitle={`Passo ${step + 1} de 3 · 100% local e privado no seu computador`}
      widthClass="w-[500px]"
    >
      {step === 0 && (
        <div className="space-y-3">
          <p className="text-xs text-[var(--text-muted)]">
            Escolha seu país, idioma e moeda padrão:
          </p>
          {(
            [
              ["BR", "Brasil", "pt-BR · R$ (BRL) + MEI"],
              ["US", "United States", "en-US · $ (USD)"],
              ["ES", "España", "es-ES · € (EUR)"],
            ] as const
          ).map(([code, name, meta]) => (
            <button
              key={code}
              type="button"
              onClick={() => setCountry(code)}
              className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                country === code
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border-subtle)] bg-[var(--bg-surface-solid)]"
              }`}
            >
              <div>
                <div className="text-sm font-semibold text-[var(--text-primary)]">{name}</div>
                <div className="text-xs text-[var(--text-muted)]">{meta}</div>
              </div>
              <span className="rounded-lg bg-[var(--bg-elevated)] px-2.5 py-1 text-xs font-bold text-[var(--accent)]">
                {code}
              </span>
            </button>
          ))}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="rounded-xl bg-[var(--accent)] px-5 py-2 text-xs font-semibold text-white"
            >
              Continuar
            </button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          <p className="text-xs text-[var(--text-muted)]">
            Como você pretende usar o OrcFin?
          </p>
          {(
            [
              ["personal", "Finanças Pessoais / Casal", "Orçamentos, cartões, metas e investimentos", User],
              ...(country === "BR"
                ? ([
                    ["both", "Pessoal + MEI", "Controle pessoal e CNPJ MEI no mesmo app", Sparkles],
                    ["mei", "Somente MEI", "Faturamento, DAS, teto R$ 81k e notas fiscais", Building2],
                  ] as const)
                : []),
            ] as const
          ).map(([id, title, desc, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setMode(id as "personal" | "mei" | "both")}
              className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                mode === id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border-subtle)] bg-[var(--bg-surface-solid)]"
              }`}
            >
              <Icon className="h-5 w-5 text-[var(--accent)]" />
              <div>
                <div className="text-sm font-semibold text-[var(--text-primary)]">{title}</div>
                <div className="text-xs text-[var(--text-muted)]">{desc}</div>
              </div>
            </button>
          ))}
          <div className="flex justify-between pt-2">
            <button
              type="button"
              onClick={() => setStep(0)}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]"
            >
              Voltar
            </button>
            <button
              type="button"
              onClick={() => setStep(2)}
              className="rounded-xl bg-[var(--accent)] px-5 py-2 text-xs font-semibold text-white"
            >
              Continuar
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <p className="text-xs text-[var(--text-muted)]">
            Escolha como deseja começar agora:
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => finish(false, true)}
            className="flex w-full items-center gap-3 rounded-xl bg-[var(--accent)] px-4 py-3 text-left text-white shadow-lg shadow-teal-500/20"
          >
            <UploadCloud className="h-5 w-5" />
            <div>
              <div className="text-sm font-semibold">Importar meu extrato (OFX / CSV / PDF)</div>
              <div className="text-xs opacity-90">Veja seu dashboard preenchido em menos de 1 minuto</div>
            </div>
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => finish(true, false)}
            className="flex w-full items-center gap-3 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-surface-solid)] px-4 py-3 text-left"
          >
            <PlayCircle className="h-5 w-5 text-emerald-400" />
            <div>
              <div className="text-sm font-semibold text-[var(--text-primary)]">
                Explorar com dados de exemplo
              </div>
              <div className="text-xs text-[var(--text-muted)]">
                Popula lançamentos fictícios para testar gráficos e relatórios
              </div>
            </div>
          </button>

          <label className="flex w-full cursor-pointer items-center gap-3 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-surface-solid)] px-4 py-3 text-left">
            <RotateCcw className="h-5 w-5 text-indigo-400" />
            <div>
              <div className="text-sm font-semibold text-[var(--text-primary)]">
                Restaurar backup existente (.orcfin.bak)
              </div>
              <div className="text-xs text-[var(--text-muted)]">
                Trouxe seus dados de outro computador? Restaure agora
              </div>
            </div>
            <input
              type="file"
              accept=".bak,.zip"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleRestoreFile(f);
              }}
            />
          </label>

          <label className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] px-3.5 py-2 text-xs">
            <span className="text-[var(--text-secondary)]">Backup automático ao fechar</span>
            <input
              type="checkbox"
              checked={backupOnClose}
              onChange={(e) => setBackupOnClose(e.target.checked)}
            />
          </label>

          <div className="flex justify-between pt-1">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]"
            >
              Voltar
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => finish(false, false)}
              className="text-xs font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              Pular e começar vazio
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
