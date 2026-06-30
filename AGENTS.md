# OrcFin — agent guidelines

## Principles (prefer the simplest option that works)

1. Does this need to exist? (YAGNI)
2. Already in this codebase? Reuse it.
3. Stdlib does it? Use it.
4. Installed dependency already solves it? Use it — do not add packages for a few lines.
5. Smallest diff that works? Ship that.

## OrcFin conventions

- **State:** views use `app.field` / `app.method()` via `StateProxyMixin` — not `app.state.*` (except shell internals that override state methods).
- **Large screens:** package with `view.py` as entry — `ui/settings/`, `ui/transactions/`, `ui/dashboard/`, `ui/reports/`, `ui/personal/charts/`.
- **UI:** theme colors from `ui.theme.active()`; no hardcoded greys in new code.
- **Data:** SQLite local only; AI gets aggregated totals, never transaction lines.
- **Tests:** non-trivial logic gets one small `test_*.py` check; run `pytest` before PR.

## Never simplify away

Input validation at trust boundaries, backup/error paths that prevent data loss, encrypted secrets, accessibility basics, and anything the user explicitly requested.

## Stack

Python 3.11+, Flet 0.85.x, SQLite, Pydantic 2. Entry: `python main.py`.