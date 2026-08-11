[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/UI-Flet-00B4D8.svg)](https://flet.dev)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](../LICENSE)

# OrcFin

**Orçamento financeiro local** para pessoa física e MEI. Tudo roda no seu PC (SQLite): importação de extratos sem nuvem, orçamento, relatórios e IA opcional — só com totais agregados, nunca com linhas de lançamento.

**[English](../README.md)** · **[Português](readme.pt-BR.md)** · **[Español](readme.es-ES.md)**

Repositório: [github.com/jorgeespinhara/OrcFin](https://github.com/jorgeespinhara/OrcFin)

---

## Por que OrcFin?

- **Local e privado** — importação e armazenamento no seu computador; modo offline bloqueia rede
- **Feito pro Brasil** — Nubank, Inter, C6, OFX/CSV/PDF e MEI (DAS, notas, pacote contador)
- **Interface multilíngue** — pt-BR, en-US, es-ES (país no assistente inicial)
- **Útil no primeiro dia** — dashboard, orçamentos, metas, vencimentos, relatórios, backup criptografado
- **IA opcional** — DeepSeek, Grok, Gemini, OpenAI, Claude — apenas números agregados

> Não é Open Banking em tempo real, app mobile de banco nem substituto de contador. O OrcFin organiza; as decisões oficiais ficam com você e o profissional habilitado.

---

## Telas

<img width="566" height="693" alt="Dashboard" src="https://github.com/user-attachments/assets/1d240304-c2f2-4edd-b3a7-7f160f5e9167" />
<img width="506" height="573" alt="Relatórios" src="https://github.com/user-attachments/assets/7f02a9f1-bb67-43f4-9667-9bb01bc511f6" />

---

## Começar rápido

### Windows — pacote portátil (recomendado)

1. Baixe `OrcFin-portable.zip` na [última release](https://github.com/jorgeespinhara/OrcFin/releases/latest)
2. Extraia e execute **`OrcFin.exe`**
3. Siga o assistente — use **Explorar com dados fictícios** se ainda não tiver extrato

Dados padrão em **`C:\OrcFin`** (definido no assistente, não na pasta do `.exe`).

Guias: [install-windows.md](install-windows.md) · [getting-started.md](getting-started.md)

### Código-fonte

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requisito: **Python 3.11+**. Testes: `pytest`.

Pacote portátil:

```powershell
python scripts/package_portable.py
```

---

## Funcionalidades (resumo)

| Área | Destaques |
|------|-----------|
| **Pessoal** | Multi-perfil, lançamentos, cartões, orçamentos, metas, patrimônio, relatórios/PDF |
| **Importação** | CSV / OFX / PDF, duplicatas, regras de categoria, preview antes de gravar |
| **MEI** | Vendas, DAS, notas, resultado, ZIP contador (perfil Brasil) |
| **Privacidade** | SQLite local, backup `.orcfin` criptografado, export CSV/JSON, modo offline |

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [install-windows.md](install-windows.md) | Instalação portátil, atualização, antivírus |
| [getting-started.md](getting-started.md) | Assistente, importação, demo, backup |
| [privacy.md](privacy.md) | O que fica local, limites da IA |
| [importers.md](importers.md) | Formatos de extrato |
| [CHANGELOG.md](../CHANGELOG.md) | Histórico de versões |

---

## Contribuindo

Issues e PRs são bem-vindos. Para mudanças grandes, abra uma issue antes. Rode `pytest` antes do PR.

## Licença

[GNU GPL v3.0](../LICENSE)

**OrcFin** — finanças pessoais e MEI no mesmo lugar: local, privado e sob seu controle.
