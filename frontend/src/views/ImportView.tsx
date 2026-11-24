import { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  CheckSquare,
  FileSpreadsheet,
  Square,
  UploadCloud,
} from "lucide-react";
import {
  api,
  type Category,
  type CreditCard,
  type ImportPreviewLine,
  type Profile,
} from "../lib/api";
import { formatMoney } from "../lib/format";

interface ImportViewProps {
  profiles: Profile[];
  categories: Category[];
  cards: CreditCard[];
  defaultProfileId: number | null;
  currency: string;
  locale: string;
  onToast: (msg: string, kind?: "success" | "error") => void;
  onImported: () => void;
}

interface EditableLine extends ImportPreviewLine {
  selected: boolean;
  category_id: number;
}

export function ImportView({
  profiles,
  categories,
  cards,
  defaultProfileId,
  currency,
  locale,
  onToast,
  onImported,
}: ImportViewProps) {
  const [profileId, setProfileId] = useState<number>(
    defaultProfileId || profiles[0]?.id || 1
  );
  const [cardId, setCardId] = useState<string>("");
  const [dragging, setDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);

  const [filename, setFilename] = useState("");
  const [source, setSource] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [lines, setLines] = useState<EditableLine[]>([]);

  const fallbackCat = (type: "income" | "expense") =>
    categories.find((c) => c.type === type)?.id || categories[0]?.id || 1;

  const processFile = async (file: File) => {
    setParsing(true);
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = "";
      const chunk = 0x8000;
      for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
      }
      const b64 = btoa(binary);
      const res = await api.importPreview({
        filename: file.name,
        content_b64: b64,
        profile_id: profileId,
      });
      setFilename(file.name);
      setSource(res.source || "file");
      setWarnings(res.warnings || []);
      setLines(
        res.lines.map((l) => ({
          ...l,
          selected: !l.is_duplicate,
          category_id: l.suggested_category_id || fallbackCat(l.type),
        }))
      );
      onToast(
        `${res.total} linha(s) lida(s) de ${file.name}${
          res.duplicates ? ` (${res.duplicates} duplicata(s) desmarcada(s))` : ""
        }.`
      );
    } catch (err) {
      onToast(
        err instanceof Error ? err.message : "Não foi possível ler o arquivo.",
        "error"
      );
    } finally {
      setParsing(false);
    }
  };

  const handleCommit = async () => {
    const selected = lines.filter((l) => l.selected);
    if (selected.length === 0) {
      onToast("Selecione pelo menos uma linha para importar.", "error");
      return;
    }
    setCommitting(true);
    try {
      const res = await api.importCommit({
        profile_id: profileId,
        filename,
        source,
        credit_card_id: cardId ? Number(cardId) : null,
        lines: selected.map((l) => ({
          date: l.date,
          description: l.description,
          amount: l.amount,
          type: l.type,
          category_id: l.category_id,
          selected: true,
        })),
      });
      onToast(`${res.imported} lançamento(s) importado(s) com sucesso!`);
      setLines([]);
      setFilename("");
      onImported();
    } catch {
      onToast("Erro ao gravar importação.", "error");
    } finally {
      setCommitting(false);
    }
  };

  const selectedCount = lines.filter((l) => l.selected).length;

  return (
    <div className="space-y-5">
      {/* Options + Drag & Drop Zone */}
      <div className="surface-card space-y-4 rounded-2xl p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Importação local de extratos (OFX, CSV e PDF)
            </h2>
            <p className="text-xs text-[var(--text-muted)]">
              Todo o processamento acontece na sua máquina. Duplicatas são detectadas automaticamente.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={profileId}
              onChange={(e) => setProfileId(Number(e.target.value))}
              className="input-pro px-3 py-1.5 text-xs"
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  Perfil: {p.name}
                </option>
              ))}
            </select>
            {cards.length > 0 && (
              <select
                value={cardId}
                onChange={(e) => setCardId(e.target.value)}
                className="input-pro px-3 py-1.5 text-xs"
              >
                <option value="">Sem vínculo de cartão</option>
                {cards.map((cd) => (
                  <option key={cd.id} value={cd.id}>
                    Cartão: {cd.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (f) processFile(f);
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-[var(--accent)] bg-[var(--accent-soft)]"
              : "border-[var(--border-strong)] bg-[var(--bg-canvas)]/50 hover:border-[var(--accent)]"
          }`}
        >
          <UploadCloud className="h-9 w-9 text-[var(--accent)]" />
          <span className="mt-2.5 text-sm font-semibold text-[var(--text-primary)]">
            {parsing
              ? "Analisando extrato..."
              : "Arraste seu arquivo OFX, CSV ou PDF aqui"}
          </span>
          <span className="mt-1 text-xs text-[var(--text-muted)]">
            ou clique para escolher do computador (Nubank, Inter, C6, Itaú, Bradesco, genérico)
          </span>
          <input
            type="file"
            accept=".ofx,.csv,.pdf,.txt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) processFile(f);
              e.target.value = "";
            }}
          />
        </label>
      </div>

      {warnings.length > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-300">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Preview Table */}
      {lines.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="surface-card overflow-hidden rounded-2xl"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] px-5 py-3.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
              <FileSpreadsheet className="h-4 w-4 text-[var(--accent)]" />
              {filename} · {selectedCount} de {lines.length} selecionada(s)
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setLines([])}
                className="rounded-xl border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)]"
              >
                Descartar
              </button>
              <button
                type="button"
                disabled={committing || selectedCount === 0}
                onClick={handleCommit}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-1.5 text-xs font-semibold text-white shadow-lg shadow-teal-500/20 disabled:opacity-50"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {committing
                  ? "Importando..."
                  : `Confirmar importação (${selectedCount})`}
              </button>
            </div>
          </div>

          <div className="max-h-[460px] divide-y divide-[var(--border-subtle)] overflow-y-auto">
            {lines.map((line, idx) => (
              <div
                key={idx}
                className={`flex flex-wrap items-center gap-3 px-5 py-2.5 text-xs ${
                  line.selected ? "" : "opacity-50"
                }`}
              >
                <button
                  type="button"
                  onClick={() =>
                    setLines((prev) =>
                      prev.map((l, i) =>
                        i === idx ? { ...l, selected: !l.selected } : l
                      )
                    )
                  }
                  className="text-[var(--text-muted)] hover:text-[var(--accent)]"
                >
                  {line.selected ? (
                    <CheckSquare className="h-4 w-4 text-[var(--accent)]" />
                  ) : (
                    <Square className="h-4 w-4" />
                  )}
                </button>
                <span className="tabular-nums w-20 text-[var(--text-muted)]">
                  {line.date}
                </span>
                <span className="min-w-[160px] flex-1 truncate font-medium text-[var(--text-primary)]">
                  {line.description}
                </span>
                {line.is_duplicate && (
                  <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                    Duplicata
                  </span>
                )}
                <select
                  value={line.category_id}
                  onChange={(e) =>
                    setLines((prev) =>
                      prev.map((l, i) =>
                        i === idx
                          ? { ...l, category_id: Number(e.target.value) }
                          : l
                      )
                    )
                  }
                  className="input-pro w-40 px-2 py-1 text-xs"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <span
                  className={`tabular-nums w-24 text-right font-semibold ${
                    line.type === "income"
                      ? "text-emerald-400"
                      : "text-[var(--text-primary)]"
                  }`}
                >
                  {line.type === "income" ? "+" : "-"}{" "}
                  {formatMoney(line.amount, currency, locale)}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
