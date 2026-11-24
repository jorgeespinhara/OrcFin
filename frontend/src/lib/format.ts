export function formatMoney(
  value: number,
  currency: string = "BRL",
  locale: string = "pt-BR"
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: currency || "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(value) ? value : 0);
  } catch {
    return `R$ ${(value || 0).toFixed(2)}`;
  }
}

export function formatShortMoney(value: number, currency: string = "BRL"): string {
  const abs = Math.abs(value);
  const sym = currency === "USD" ? "$" : currency === "EUR" ? "€" : "R$";
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}${sym} ${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${sym} ${(abs / 1_000).toFixed(1)}k`;
  return `${sign}${sym} ${abs.toFixed(0)}`;
}

export function formatPct(value: number): string {
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return "0,0%";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1).replace(".", ",")}%`;
}

const MONTH_SHORT = [
  "",
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

const MONTH_FULL = [
  "Ano inteiro",
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

export function monthName(month: number | null): string {
  return MONTH_FULL[month ?? 0] ?? "";
}

export function formatDateGroup(isoDate: string): string {
  const today = new Date();
  const isoToday = today.toISOString().slice(0, 10);
  const yest = new Date(today);
  yest.setDate(today.getDate() - 1);
  const isoYest = yest.toISOString().slice(0, 10);
  if (isoDate === isoToday) return "Hoje";
  if (isoDate === isoYest) return "Ontem";
  const [y, m, d] = isoDate.split("-").map(Number);
  if (!y || !m || !d) return isoDate;
  return `${String(d).padStart(2, "0")} ${MONTH_SHORT[m]} ${y}`;
}
