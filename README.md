<div align="center">

# OrcFin

**Local-first desktop personal finance & MEI management app.**  
Private by design. Fast native desktop UI. Zero cloud lock-in, zero subscriptions, zero telemetry.

[![Release](https://img.shields.io/badge/release-v1.0.0-14B8A6.svg?style=flat-square)](https://github.com/jorgeespinhara/OrcFin/releases/latest)
[![Frontend](https://img.shields.io/badge/UI-React%2019%20%2B%20Tailwind%20v4-38BDF8.svg?style=flat-square)](frontend/)
[![Backend](https://img.shields.io/badge/Core-Python%203.11%2B%20%2B%20FastAPI%20%2B%20SQLite-22C55E.svg?style=flat-square)](api/)
[![License](https://img.shields.io/badge/license-GPL--3.0-6366F1.svg?style=flat-square)](LICENSE)

**[English](README.md)** · **[Português (Brasil)](docs/readme.pt-BR.md)** · **[Español](docs/readme.es-ES.md)**

[Download for Windows (v1.0.0)](https://github.com/jorgeespinhara/OrcFin/releases/latest) · [Changelog](CHANGELOG.md) · [Privacy Architecture](docs/privacy.md)

</div>

---

## Why OrcFin?

Most finance apps force a trade-off: either upload your entire bank history to a paid cloud SaaS, or wrestle with brittle spreadsheets. **OrcFin** delivers a modern, fluid desktop experience while keeping **100% of your financial data on your own machine**.

- **100% Local & Private** — Local SQLite (WAL mode) storage, AES-GCM encrypted `.orcfin.bak` backups, OS-protected secrets, strict offline switch, and sanitized support diagnostics with zero telemetry.
- **Modern Native Desktop UI** — Built with **React 19, TypeScript, Tailwind CSS v4, Framer Motion, and Recharts** running inside Windows' native **WebView2** (`pywebview`) over a local `127.0.0.1` FastAPI engine.
- **Built for Speed** — Global Command Palette (`Ctrl+K`), quick entry (`Ctrl+N`), instant search (`Ctrl+F`), category/card/sort filters, batch recategorization, and 5-second **Undo** on delete.
- **Personal, Couples & MEI (Brazil)** — Manage individual or consolidated household budgets alongside a dedicated **MEI** workspace (R$ 81,000 annual limit tracker, monthly DAS confirmation, clients, invoices, and NF-e XML import).
- **Optional Privacy-Safe AI** — Connect DeepSeek, Grok, Gemini, OpenAI, or Claude. The AI **only receives aggregated monthly totals**, never individual transaction descriptions, names, or tax IDs.

> OrcFin is a local organization and decision-support tool — not an Open Banking sync app or a substitute for a licensed accountant.

---

## Download & Install (Windows)

Both packages bundle the Python runtime and compiled UI — **no Python, Node.js, or manual setup required**.

| Option | File | Size | Best for |
| :--- | :--- | :---: | :--- |
| **Installer (Recommended)** | [`OrcFin-Setup.exe`](https://github.com/jorgeespinhara/OrcFin/releases/latest) | ~58 MB | Per-user install (no admin required), Start Menu & Desktop shortcuts, clean uninstaller |
| **Portable ZIP** | [`OrcFin-portable.zip`](https://github.com/jorgeespinhara/OrcFin/releases/latest) | ~76 MB | Extract anywhere and run `OrcFin.exe` (keep `_internal` folder intact) |

On first launch, the **3-step onboarding** lets you:
1. Pick your country, language, and currency (`BR / BRL`, `US / USD`, `ES / EUR`);
2. Choose **Personal**, **Personal + MEI**, or **MEI only**;
3. **Import a bank statement** (`OFX`, `CSV`, or `PDF`), **Explore with sample data**, or **Restore an existing `.orcfin.bak` backup**.

> Default data folder: `C:\OrcFin` (stored outside the app directory so updates never touch your data).

---

## Feature Overview

| Module | Highlights |
| :--- | :--- |
| **Dashboard** | Responsive KPI cards with animated sparklines, spendable balance, upcoming bills strip, 12-month Income vs. Expense bar chart, interactive Category Donut (click to drill down), Balance Evolution area chart, and monthly budgets |
| **Transactions** | Instant debounced search, type/category/card/sort filters, date-grouped rows with tabular figures, batch category update, batch delete, and instant **5s Undo** |
| **Statement Import** | Drag-and-drop `OFX`, `CSV` (Nubank, Inter, C6, generic), and `PDF` import with automatic duplicate detection, editable category preview, and credit card linking |
| **Credit Cards** | Monthly invoice tracking, animated credit limit usage bars, available limit, and closing/due date management |
| **Investments** | Local portfolio (stocks, FIIs, fixed income, ETFs, CVM funds, crypto), allocation donut chart, PnL tracking, and optional 1-click quote refresh |
| **Reports & AI** | Local insights, expense seasonality chart, automatic recurrence detection, interactive scenario simulator, PDF report export, and optional AI insights |
| **MEI (Brazil)** | CNPJ & activity setup, R$ 81k annual limit bar with risk alerts, 1-click DAS payment confirmation, clients, invoices with payment reconciliation, and **NF-e XML** import |
| **Privacy & Settings** | Multi-profile & custom categories, goals, budgets, auto-categorization rules, net worth (assets/liabilities), encrypted `.orcfin.bak` backup/restore, CSV/JSON export, sanitized diagnostics `.txt`, manual update check, and strict offline toggle |

---

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│  Native Desktop Window (pywebview / Windows WebView2)    │
│  React 19 · TypeScript · Tailwind v4 · Motion · Recharts │
└──────────────────────────┬───────────────────────────────┘
                           │ Local HTTP (127.0.0.1, ephemeral port)
┌──────────────────────────▼───────────────────────────────┐
│  Local API Layer (FastAPI + Uvicorn in-process thread)   │
├──────────────────────────────────────────────────────────┤
│  Core Engine (Python 3.11+ · Pydantic v2 · SQLite WAL)   │
│  Parsers (OFX/CSV/PDF/XML) · MEI · Portfolio · Crypto    │
└──────────────────────────────────────────────────────────┘
```

---

## Running from Source

Requirements: **Python 3.11+** and **Node.js 20+**.

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin

# 1. Backend dependencies
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the React frontend
cd frontend
npm ci
npm run build
cd ..

# 3. Launch the native desktop app
python main.py
```

### Tests & Packaging

```powershell
# Run full test suite (215+ tests, fully isolated)
pytest -q

# Build Windows portable bundle (dist/OrcFin-portable.zip)
python scripts/package_portable.py
```

---

## Documentation

- [Windows Installation & Updates](docs/install-windows.md)
- [Getting Started](docs/getting-started.md)
- [Privacy & LGPD Architecture](docs/privacy.md)
- [Supported Statement Importers](docs/importers.md)
- [Data Model (Schema v15)](docs/data-model.md)
- [Changelog](CHANGELOG.md)

---

## Contributing & License

Issues and pull requests are welcome. Run `pytest -q` and `npm --prefix frontend run build` before submitting a PR.

Licensed under the [GNU General Public License v3.0](LICENSE).
