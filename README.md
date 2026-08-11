[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/UI-Flet-00B4D8.svg)](https://flet.dev)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

# OrcFin

**Local-first personal finance desktop app** — household budgets, Brazilian bank imports, and optional MEI tools. Your data stays on your PC (SQLite). AI is optional and only receives aggregated totals, never individual transaction lines.

**[English](README.md)** · **[Português](docs/readme.pt-BR.md)** · **[Español](docs/readme.es-ES.md)**

Repo: [github.com/jorgeespinhara/OrcFin](https://github.com/jorgeespinhara/OrcFin)

---

## Why OrcFin?

- **Local & private** — imports and storage run on your machine; optional offline mode blocks network calls
- **Built for Brazil** — Nubank, Inter, C6, OFX/CSV/PDF, and MEI (DAS, invoices, accountant pack)
- **Multilingual UI** — pt-BR, en-US, es-ES (country profile at onboarding)
- **Useful day one** — dashboard, budgets, goals, due dates, reports, encrypted backup
- **Optional AI** — DeepSeek, Grok, Gemini, OpenAI, Claude — aggregated numbers only

> Not a bank sync app, mobile bank, or substitute for an accountant. It organizes; you (and your professional) decide.

---

## Screenshots

<img width="566" height="693" alt="Dashboard" src="https://github.com/user-attachments/assets/1d240304-c2f2-4edd-b3a7-7f160f5e9167" />
<img width="506" height="573" alt="Reports" src="https://github.com/user-attachments/assets/7f02a9f1-bb67-43f4-9667-9bb01bc511f6" />

---

## Quick start

### Windows portable (recommended)

1. Download `OrcFin-portable.zip` from the [latest release](https://github.com/jorgeespinhara/OrcFin/releases/latest)
2. Extract and run **`OrcFin.exe`**
3. Complete the setup wizard — try **Explore with sample data** if you have no statement yet

Default data folder: **`C:\OrcFin`** (chosen at first run, not next to the `.exe`).

Full guide: [docs/install-windows.md](docs/install-windows.md) · [Getting started](docs/getting-started.md)

### From source

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requirements: **Python 3.11+**. Tests: `pytest`.

Build portable zip:

```powershell
python scripts/package_portable.py
```

---

## Features (short)

| Area | Highlights |
|------|------------|
| **Personal** | Multi-profile, transactions, cards, budgets, goals, net worth, reports/PDF |
| **Import** | CSV / OFX / PDF, duplicate detection, category rules, preview before save |
| **MEI** | Sales, DAS obligations, invoices, result report, accountant ZIP (BR country) |
| **Privacy** | Local SQLite, encrypted `.orcfin` backup, export CSV/JSON, offline switch |

---

## Documentation

| Doc | Content |
|-----|---------|
| [install-windows.md](docs/install-windows.md) | Portable install, update, antivirus |
| [getting-started.md](docs/getting-started.md) | Onboarding, import, demo data, backup |
| [privacy.md](docs/privacy.md) | What stays local, AI limits |
| [importers.md](docs/importers.md) | Statement formats |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

---

## Contributing

Issues and PRs welcome. For larger changes, open an issue first. Run `pytest` before submitting.

## License

[GNU GPL v3.0](LICENSE)

**OrcFin** — personal finance (and MEI) on your computer: local, private, under your control.
