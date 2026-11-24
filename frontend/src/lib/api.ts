export interface Profile {
  id: number;
  name: string;
  color: string;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  slug: string | null;
  icon: string;
  color: string;
  type: "income" | "expense";
}

export interface CreditCard {
  id: number;
  name: string;
  profile_id: number | null;
  limit: number;
  due_day: number;
}

export interface MetaResponse {
  app_name: string;
  version: string;
  schema_version: number;
  theme_mode: "dark" | "light";
  locale: string;
  currency: string;
  strict_offline: boolean;
  onboarding_completed?: boolean;
  mei_available?: boolean;
  profiles: Profile[];
  categories: Category[];
  credit_cards: CreditCard[];
}

export interface DashboardData {
  current_month: {
    total_income: number;
    total_expense: number;
    net_savings: number;
    savings_rate: number;
  };
  comparison: {
    income_change_pct: number;
    expense_change_pct: number;
  };
  spendable: {
    spendable: number;
    committed?: number;
    budget_total?: number;
  };
  category_breakdown: Array<{
    category_id?: number;
    name: string;
    total: number;
    color?: string;
    icon?: string;
    percentage?: number;
  }>;
  monthly_series: Array<{
    label: string;
    income: number;
    expense: number;
    net_savings: number;
  }>;
  balance_evolution: Array<{
    label: string;
    cumulative_balance: number;
    net_savings?: number;
  }>;
  budgets: Array<{
    id?: number;
    category_name: string;
    icon?: string;
    spent: number;
    limit: number;
    percentage: number;
  }>;
  due_dates: Array<{
    label?: string;
    date?: string;
    kind?: string;
    title?: string;
    description?: string;
    due_date?: string;
    amount?: number | null;
    days_until?: number;
    urgency?: string;
  }>;
}

export interface TransactionItem {
  id: number;
  profile_id: number;
  profile_name: string;
  profile_color: string;
  date: string;
  description: string;
  amount: number;
  category_id: number;
  category_name: string;
  category_icon: string;
  category_color: string;
  type: "income" | "expense";
  credit_card_id: number | null;
  credit_card_name: string | null;
  notes: string | null;
  is_recurring: boolean;
}

export interface TransactionsResponse {
  items: TransactionItem[];
  totals: {
    income: number;
    expense: number;
    net: number;
    count: number;
  };
}

export interface TransactionPayload {
  profile_id: number;
  date: string;
  description: string;
  amount: number;
  category_id: number;
  type: "income" | "expense";
  credit_card_id?: number | null;
  notes?: string | null;
  is_recurring?: boolean;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => request<MetaResponse>("/api/meta"),
  setTheme: (theme_mode: "dark" | "light") =>
    request<{ theme_mode: string }>("/api/settings/theme", {
      method: "POST",
      body: JSON.stringify({ theme_mode }),
    }),
  seedDemo: () =>
    request<{ seeded: number }>("/api/demo-seed", { method: "POST" }),
  dashboard: (params: {
    profile_id?: number | null;
    consolidated: boolean;
    year: number;
    month: number | null;
  }) => {
    const qs = new URLSearchParams({
      consolidated: String(params.consolidated),
      year: String(params.year),
    });
    if (params.profile_id) qs.set("profile_id", String(params.profile_id));
    if (params.month) qs.set("month", String(params.month));
    return request<DashboardData>(`/api/dashboard?${qs.toString()}`);
  },
  transactions: (params: {
    profile_id?: number | null;
    consolidated: boolean;
    year: number;
    month: number | null;
    q?: string;
    type_filter?: "all" | "income" | "expense";
    category_id?: number | null;
    card_id?: number | null;
    sort?: "date_desc" | "date_asc" | "amount_desc" | "amount_asc";
  }) => {
    const qs = new URLSearchParams({
      consolidated: String(params.consolidated),
      year: String(params.year),
      type_filter: params.type_filter || "all",
      sort: params.sort || "date_desc",
    });
    if (params.profile_id) qs.set("profile_id", String(params.profile_id));
    if (params.month) qs.set("month", String(params.month));
    if (params.q) qs.set("q", params.q);
    if (params.category_id) qs.set("category_id", String(params.category_id));
    if (params.card_id) qs.set("card_id", String(params.card_id));
    return request<TransactionsResponse>(`/api/transactions?${qs.toString()}`);
  },
  createTransaction: (payload: TransactionPayload) =>
    request<{ id: number }>("/api/transactions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTransaction: (id: number, payload: TransactionPayload) =>
    request<{ updated: boolean }>(`/api/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  softDeleteTransaction: (id: number) =>
    request<{ deleted: number; id: number }>(`/api/transactions/${id}`, {
      method: "DELETE",
    }),
  restoreTransactions: (ids: number[]) =>
    request<{ restored: number }>("/api/transactions/restore", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  batchCategory: (ids: number[], category_id: number) =>
    request<{ updated: number }>("/api/transactions/batch-category", {
      method: "POST",
      body: JSON.stringify({ ids, category_id }),
    }),
  batchDelete: (ids: number[]) =>
    request<{ deleted: number }>("/api/transactions/batch-delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  // --- Phase 2: Cards, Import, Investments, Reports/AI, Settings ---
  cards: (params: { profile_id?: number | null; consolidated: boolean; year: number; month: number | null }) => {
    const qs = new URLSearchParams({
      consolidated: String(params.consolidated),
      year: String(params.year),
    });
    if (params.profile_id) qs.set("profile_id", String(params.profile_id));
    if (params.month) qs.set("month", String(params.month));
    return request<{ items: CardSummary[]; year: number; month: number }>(`/api/cards?${qs.toString()}`);
  },
  createCard: (payload: { profile_id: number; name: string; credit_limit: number; due_day: number; closing_day: number }) =>
    request<{ id: number }>("/api/cards", { method: "POST", body: JSON.stringify(payload) }),
  deleteCard: (id: number) => request<{ deleted: boolean }>(`/api/cards/${id}`, { method: "DELETE" }),

  importPreview: (payload: { filename: string; content_b64: string; profile_id: number }) =>
    request<ImportPreviewResponse>("/api/import/preview", { method: "POST", body: JSON.stringify(payload) }),
  importCommit: (payload: {
    profile_id: number;
    filename: string;
    source: string;
    credit_card_id: number | null;
    lines: Array<{ date: string; description: string; amount: number; type: "income" | "expense"; category_id: number; selected: boolean }>;
  }) => request<{ imported: number; batch_id: number | null }>("/api/import/commit", { method: "POST", body: JSON.stringify(payload) }),

  investments: (profile_id: number) =>
    request<PortfolioSummary>(`/api/investments?profile_id=${profile_id}`),
  createHolding: (payload: {
    profile_id: number;
    name: string;
    ticker: string;
    asset_class: string;
    quantity: number;
    avg_price: number;
    institution: string;
  }) => request<{ id: number }>("/api/investments", { method: "POST", body: JSON.stringify(payload) }),
  deleteHolding: (id: number) => request<{ deleted: boolean }>(`/api/investments/${id}`, { method: "DELETE" }),
  refreshQuotes: (profile_id: number) =>
    request<Record<string, unknown>>(`/api/investments/refresh-quotes?profile_id=${profile_id}`, { method: "POST" }),

  reports: (params: { profile_id?: number | null; consolidated: boolean; year: number; month: number | null }) => {
    const qs = new URLSearchParams({ consolidated: String(params.consolidated), year: String(params.year) });
    if (params.profile_id) qs.set("profile_id", String(params.profile_id));
    if (params.month) qs.set("month", String(params.month));
    return request<ReportsResponse>(`/api/reports?${qs.toString()}`);
  },
  simulate: (payload: { profile_id: number | null; consolidated: boolean; months_ahead: number; kind: string; value: number }) =>
    request<Record<string, unknown>>("/api/reports/simulate", { method: "POST", body: JSON.stringify(payload) }),
  exportPdf: (payload: { profile_id: number | null; consolidated: boolean; year: number; month: number }) =>
    request<{ path: string }>("/api/reports/pdf", { method: "POST", body: JSON.stringify(payload) }),
  runAi: (payload: { profile_id: number | null; consolidated: boolean; provider?: string }) =>
    request<{ summary?: string; insights?: string[]; recommendations?: string[]; alerts?: string[]; error?: string; provider?: string }>(
      "/api/reports/ai",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  settings: () => request<SettingsResponse>("/api/settings"),
  updateSettings: (payload: Record<string, unknown>) =>
    request<{ saved: boolean }>("/api/settings", { method: "PUT", body: JSON.stringify(payload) }),
  createProfile: (name: string, color: string) =>
    request<{ id: number }>("/api/profiles", { method: "POST", body: JSON.stringify({ name, color }) }),
  deleteProfile: (id: number) => request<{ deleted: boolean }>(`/api/profiles/${id}`, { method: "DELETE" }),
  createCategory: (name: string, type: "income" | "expense", icon: string) =>
    request<{ id: number }>("/api/categories", { method: "POST", body: JSON.stringify({ name, type, icon }) }),
  deleteCategory: (id: number) => request<{ deleted: boolean }>(`/api/categories/${id}`, { method: "DELETE" }),

  goals: (profile_id?: number | null) =>
    request<{ items: GoalItem[] }>(profile_id ? `/api/goals?profile_id=${profile_id}` : "/api/goals"),
  createGoal: (name: string, target_amount: number, profile_id?: number | null) =>
    request<{ id: number }>("/api/goals", { method: "POST", body: JSON.stringify({ name, target_amount, profile_id }) }),
  progressGoal: (id: number, add_amount: number) =>
    request<{ updated: boolean }>(`/api/goals/${id}/progress`, { method: "POST", body: JSON.stringify({ add_amount }) }),
  deleteGoal: (id: number) => request<{ deleted: boolean }>(`/api/goals/${id}`, { method: "DELETE" }),

  budgets: (year: number, month: number, consolidated: boolean, profile_id?: number | null) => {
    const qs = new URLSearchParams({ year: String(year), month: String(month), consolidated: String(consolidated) });
    if (profile_id) qs.set("profile_id", String(profile_id));
    return request<{ items: Array<{ id: number; category_name: string; spent: number; limit: number; percentage: number }> }>(`/api/budgets?${qs.toString()}`);
  },
  setBudget: (payload: { profile_id: number | null; category_id: number; year: number; month: number; limit_amount: number }) =>
    request<{ saved: boolean }>("/api/budgets", { method: "POST", body: JSON.stringify(payload) }),
  deleteBudget: (id: number) => request<{ deleted: boolean }>(`/api/budgets/${id}`, { method: "DELETE" }),

  rules: () => request<{ items: Array<{ id: number; pattern: string; category_id: number; match_type: string }> }>("/api/rules"),
  createRule: (pattern: string, category_id: number, match_type: string = "contains") =>
    request<{ id: number }>("/api/rules", { method: "POST", body: JSON.stringify({ pattern, category_id, match_type }) }),
  deleteRule: (id: number) => request<{ deleted: boolean }>(`/api/rules/${id}`, { method: "DELETE" }),

  netWorth: (profile_id: number) => request<NetWorthResponse>(`/api/net-worth?profile_id=${profile_id}`),
  createAsset: (profile_id: number, name: string, value: number) =>
    request<{ id: number }>("/api/assets", { method: "POST", body: JSON.stringify({ profile_id, name, value }) }),
  deleteAsset: (id: number) => request<{ deleted: boolean }>(`/api/assets/${id}`, { method: "DELETE" }),
  createLiability: (profile_id: number, name: string, balance: number) =>
    request<{ id: number }>("/api/liabilities", { method: "POST", body: JSON.stringify({ profile_id, name, balance }) }),
  deleteLiability: (id: number) => request<{ deleted: boolean }>(`/api/liabilities/${id}`, { method: "DELETE" }),

  createBackup: () => request<{ path: string }>("/api/backup/create", { method: "POST" }),
  exportCsv: (profile_id?: number | null) =>
    request<{ path: string }>(profile_id ? `/api/export/csv?profile_id=${profile_id}` : "/api/export/csv", { method: "POST" }),
  exportJson: (profile_id?: number | null) =>
    request<{ path: string }>(profile_id ? `/api/export/json?profile_id=${profile_id}` : "/api/export/json", { method: "POST" }),
  exportDiagnostics: () => request<{ path: string }>("/api/diagnostics/export", { method: "POST" }),
  checkUpdates: () => request<{ status: string; current: string; latest?: string; url?: string }>("/api/updates/check"),
  resetFinancial: () => request<{ reset: boolean }>("/api/reset/financial", { method: "POST" }),

  // --- Phase 3: MEI & Onboarding ---
  meiOverview: () => request<MeiOverviewResponse>("/api/mei/overview"),
  meiSetup: (payload: {
    razao_social: string;
    cnpj: string;
    activity_type: "comercio" | "servico" | "misto";
    operational_profile: "on_demand" | "recurring" | "inventory" | "hybrid";
    das_day: number;
  }) => request<{ profile_id: number }>("/api/mei/setup", { method: "POST", body: JSON.stringify(payload) }),
  meiConfirmDas: () => request<{ confirmed: boolean }>("/api/mei/das/confirm", { method: "POST" }),
  meiCreateClient: (payload: { name: string; document?: string; email?: string; phone?: string }) =>
    request<{ id: number }>("/api/mei/clients", { method: "POST", body: JSON.stringify(payload) }),
  meiDeleteClient: (id: number) => request<{ deleted: boolean }>(`/api/mei/clients/${id}`, { method: "DELETE" }),
  meiCreateInvoice: (payload: {
    invoice_number: string;
    issue_date: string;
    amount: number;
    description?: string;
    client_id?: number | null;
  }) => request<{ id: number }>("/api/mei/invoices", { method: "POST", body: JSON.stringify(payload) }),
  meiReceiveInvoice: (id: number) =>
    request<{ received: boolean }>(`/api/mei/invoices/${id}/receive`, { method: "POST" }),
  meiDeleteInvoice: (id: number) => request<{ deleted: boolean }>(`/api/mei/invoices/${id}`, { method: "DELETE" }),
  meiImportNfeXml: (content_b64: string) =>
    request<{ id: number; invoice_number: string }>("/api/mei/nfe-xml", {
      method: "POST",
      body: JSON.stringify({ content_b64 }),
    }),
  completeOnboarding: (payload: {
    country: "BR" | "US" | "ES";
    setup_mode: "personal" | "mei" | "both";
    use_demo: boolean;
    backup_on_close: boolean;
  }) => request<{ completed: boolean; seeded_personal: number; seeded_mei: number }>("/api/onboarding/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  restoreBackup: (filename: string, content_b64: string) =>
    request<{ restored: boolean }>("/api/backup/restore", {
      method: "POST",
      body: JSON.stringify({ filename, content_b64 }),
    }),
};

export interface MeiOverviewResponse {
  configured: boolean;
  profile_id?: number;
  config?: {
    razao_social: string;
    cnpj: string;
    activity_type: "comercio" | "servico" | "misto";
    operational_profile: "on_demand" | "recurring" | "inventory" | "hybrid";
    das_day: number;
    annual_limit: number;
  };
  dashboard?: {
    month_income: number;
    month_expense: number;
    ticket_medio: number;
  };
  limit_status?: {
    ytd_revenue: number;
    annual_limit: number;
    percentage: number;
    at_risk: boolean;
  };
  report?: {
    simplified_result?: number;
    total_revenue?: number;
  };
  das?: {
    paid: boolean;
    amount: number;
    info: { days_left?: number; is_urgent?: boolean; due_date?: string };
  };
  clients?: Array<{ id: number; name: string; document?: string; email?: string }>;
  invoices?: Array<{
    id: number;
    invoice_number: string;
    issue_date: string;
    amount: number;
    description?: string;
    paid?: boolean;
    paid_at?: string | null;
    client_name?: string;
  }>;
}

export interface CardSummary {
  id: number;
  profile_id: number;
  name: string;
  credit_limit: number;
  due_day: number;
  closing_day: number;
  spent: number;
  available: number;
  usage_pct: number;
  tx_count: number;
}

export interface ImportPreviewLine {
  index: number;
  date: string;
  description: string;
  amount: number;
  type: "income" | "expense";
  suggested_category_id: number | null;
  is_duplicate: boolean;
  confidence: number;
}

export interface ImportPreviewResponse {
  source: string;
  institution: string;
  warnings: string[];
  lines: ImportPreviewLine[];
  total: number;
  duplicates: number;
}

export interface PortfolioSummary {
  total_market_value?: number;
  total_invested?: number;
  total_pnl?: number;
  total_pnl_pct?: number;
  by_class?: Array<{ asset_class: string; label?: string; value: number; pct: number }>;
  items?: Array<{
    id: number;
    name: string;
    ticker?: string;
    asset_class: string;
    quantity: number;
    avg_price: number;
    current_price?: number;
    market_value: number;
    pnl: number;
    pnl_pct: number;
    institution?: string;
  }>;
}

export interface ReportsResponse {
  seasonal: { months?: Array<{ month_label?: string; label?: string; current?: number; average?: number }> };
  top_trends: Array<{ name: string; total?: number; change_pct?: number }>;
  recurrences: Array<{ description: string; average_amount: number; distinct_months: number }>;
  local_insights: string[];
  ai_provider: string;
  providers: Array<{ id: string; name: string }>;
}

export interface GoalItem {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  progress_pct?: number;
}

export interface NetWorthResponse {
  totals: { total_assets?: number; total_liabilities?: number; net_worth?: number };
  assets: Array<{ id: number; name: string; value: number; asset_type?: string }>;
  liabilities: Array<{ id: number; name: string; balance: number; liability_type?: string }>;
}

export interface SettingsResponse {
  locale: string;
  country_profile: string;
  currency: string;
  theme_mode: "dark" | "light";
  strict_offline: boolean;
  backup_on_close: boolean;
  ai_provider: string;
  ai_model: string;
  ai_base_url: string;
  ai_has_key: boolean;
  backups: string[];
  providers: Array<{ id: string; name: string }>;
}
