[![Release](https://img.shields.io/badge/release-v1.0.0-14B8A6.svg)](https://github.com/jorgeespinhara/OrcFin/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/UI-Flet-00B4D8.svg)](https://flet.dev)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](../LICENSE)

# OrcFin

**Finanzas personales en local** — presupuestos del hogar, importación de extractos y herramientas MEI (Brasil) opcionales. Los datos viven en tu PC (SQLite). La IA es opcional y solo recibe totales agregados, nunca líneas de movimientos.

**[English](../README.md)** · **[Português](readme.pt-BR.md)** · **[Español](readme.es-ES.md)**

Repositorio: [github.com/jorgeespinhara/OrcFin](https://github.com/jorgeespinhara/OrcFin)

---

## ¿Por qué OrcFin?

- **Local y privado** — importación y almacenamiento en tu equipo; modo offline bloquea la red
- **Pensado para Brasil** — Nubank, Inter, C6, OFX/CSV/PDF y MEI (DAS, facturas, paquete contable)
- **UI multilingüe** — pt-BR, en-US, es-ES (país en el asistente inicial)
- **Útil desde el día uno** — panel, presupuestos, metas, vencimientos, informes, copia de seguridad cifrada
- **IA opcional** — DeepSeek, Grok, Gemini, OpenAI, Claude — solo cifras agregadas

> No es banca en tiempo real, app móvil bancaria ni sustituto de un contable. OrcFin organiza; las decisiones oficiales son tuyas y de un profesional.

---

## Capturas

<img width="566" height="693" alt="Panel" src="https://github.com/user-attachments/assets/1d240304-c2f2-4edd-b3a7-7f160f5e9167" />
<img width="506" height="573" alt="Informes" src="https://github.com/user-attachments/assets/7f02a9f1-bb67-43f4-9667-9bb01bc511f6" />

---

## Inicio rápido

### Windows — Instalador o Portable (recomendado)

1. Descarga **`OrcFin-Setup.exe`** (instalador por usuario, sin permisos de administrador) o **`OrcFin-portable.zip`** en la [última release](https://github.com/jorgeespinhara/OrcFin/releases/latest)
2. Ejecuta el instalador (o extrae el ZIP y ejecuta **`OrcFin.exe`**)
3. Completa el asistente de 3 pasos — elige **Importar extracto**, **Explorar con datos de ejemplo** o **Restaurar copia de seguridad (`.orcfin.bak`)**

Carpeta de datos por defecto: **`C:\OrcFin`** (se elige al inicio, no junto al `.exe`).

Guías: [install-windows.md](install-windows.md) · [getting-started.md](getting-started.md)

### Desde el código

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requisito: **Python 3.11+**. Tests: `pytest`.

Generar zip portable:

```powershell
python scripts/package_portable.py
```

---

## Funciones (resumen)

| Área | Destacados |
|------|------------|
| **Personal** | Multi-perfil, movimientos (filtros por categoría/tarjeta/orden, edición en lote, Deshacer 5s, `Ctrl+N`/`Ctrl+F`), tarjetas, presupuestos, metas, patrimonio, informes/PDF |
| **Importación** | CSV / OFX / PDF, duplicados, reglas de categoría, vista previa antes de guardar |
| **MEI** | Ventas, DAS, facturas/NF-e XML, pedidos, recurrentes, inventario, resultado, ZIP contable (perfil Brasil) |
| **Inversiones** | Cartera local (acciones, FIIs, fondos, ETFs, cripto) con cotizaciones opcionales |
| **Privacidad y Soporte** | SQLite local (WAL), backup `.orcfin.bak` cifrado, export CSV/JSON, diagnóstico sanitizado `.txt`, comprobación opcional de actualizaciones, modo offline |

---

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [install-windows.md](install-windows.md) | Instalación portable, actualización, antivirus |
| [getting-started.md](getting-started.md) | Onboarding, importación, demo, backup |
| [privacy.md](privacy.md) | Qué se queda en local, límites de la IA |
| [importers.md](importers.md) | Formatos de extracto |
| [CHANGELOG.md](../CHANGELOG.md) | Historial de versiones |

---

## Contribuir

Issues y PRs bienvenidos. Para cambios grandes, abre un issue antes. Ejecuta `pytest` antes del PR.

## Licencia

[GNU GPL v3.0](../LICENSE)

**OrcFin** — finanzas personales (y MEI) en tu ordenador: local, privado y bajo tu control.
