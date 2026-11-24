<div align="center">

# OrcFin

**Aplicativo desktop de finanças pessoais e gestão MEI 100% local.**  
Privado por padrão. Interface desktop moderna e fluida. Sem nuvem obrigatória, sem mensalidade e sem telemetria.

[![Release](https://img.shields.io/badge/release-v1.0.0-14B8A6.svg?style=flat-square)](https://github.com/jorgeespinhara/OrcFin/releases/latest)
[![Frontend](https://img.shields.io/badge/UI-React%2019%20%2B%20Tailwind%20v4-38BDF8.svg?style=flat-square)](../frontend/)
[![Backend](https://img.shields.io/badge/Core-Python%203.11%2B%20%2B%20FastAPI%20%2B%20SQLite-22C55E.svg?style=flat-square)](../api/)
[![License](https://img.shields.io/badge/license-GPL--3.0-6366F1.svg?style=flat-square)](../LICENSE)

**[English](../README.md)** · **[Português (Brasil)](readme.pt-BR.md)** · **[Español](readme.es-ES.md)**

[Baixar para Windows (v1.0.0)](https://github.com/jorgeespinhara/OrcFin/releases/latest) · [Changelog](../CHANGELOG.md) · [Arquitetura de Privacidade](privacy.md)

</div>

---

## Por que o OrcFin?

A maioria dos apps financeiros obriga você a escolher entre enviar todo o seu histórico bancário para um SaaS pago na nuvem ou manter planilhas frágeis. O **OrcFin** entrega acabamento de software desktop moderno mantendo **100% dos seus dados financeiros no seu próprio computador**.

- **100% Local e Privado** — Banco SQLite local (modo WAL), backup `.orcfin.bak` criptografado (AES-GCM), segredos protegidos pelo sistema, chave de modo offline estrito e exportação de diagnóstico sanitizado sem telemetria.
- **Interface Desktop Moderna (PRO)** — Construída com **React 19, TypeScript, Tailwind CSS v4, Framer Motion e Recharts** rodando em janela nativa **WebView2** (`pywebview`) sobre um motor local FastAPI (`127.0.0.1`).
- **Feito para Agilidade** — Paleta de Comandos (`Ctrl+K`), novo lançamento global (`Ctrl+N`), busca instantânea (`Ctrl+F`), filtros por categoria/cartão/ordenação, alteração de categoria em lote e **Desfazer (5s)** ao excluir.
- **Pessoal, Casal e MEI no Mesmo App** — Gerencie perfis individuais ou visão consolidada junto a um módulo **MEI** completo (teto anual de R$ 81.000, confirmação do DAS mensal, clientes, notas fiscais e importação de **NF-e XML**).
- **IA Opcional com Privacidade (LGPD)** — Conecte DeepSeek, Grok, Gemini, OpenAI ou Claude. A IA **recebe apenas totais mensais agregados** — nunca descrições individuais, nomes ou CPF/CNPJ.

> O OrcFin é uma ferramenta local de organização e apoio à decisão — não é Open Finance em tempo real nem substitui um contador habilitado.

---

## Baixar e Instalar (Windows)

Ambos os pacotes já incluem Python e a interface compilada — **não é preciso instalar Python, Node.js nem dependências**.

| Opção | Arquivo | Tamanho | Ideal para |
| :--- | :--- | :---: | :--- |
| **Instalador (Recomendado)** | [`OrcFin-Setup.exe`](https://github.com/jorgeespinhara/OrcFin/releases/latest) | ~58 MB | Instalação por usuário (sem exigir administrador), atalhos no Menu Iniciar/Desktop e desinstalador limpo |
| **Portátil (ZIP)** | [`OrcFin-portable.zip`](https://github.com/jorgeespinhara/OrcFin/releases/latest) | ~76 MB | Extrair em qualquer pasta e executar `OrcFin.exe` (sem apagar `_internal`) |

Na primeira abertura, o **assistente em 3 passos** permite:
1. Escolher país, idioma e moeda (`BR / R$`, `US / $`, `ES / €`);
2. Escolher **Pessoal**, **Pessoal + MEI** ou **Somente MEI**;
3. **Importar seu extrato** (`OFX`, `CSV` ou `PDF`), **Explorar com dados de exemplo** ou **Restaurar um backup `.orcfin.bak` existente**.

> Pasta padrão de dados: `C:\OrcFin` (armazenada fora da pasta do programa para que atualizações nunca apaguem seus dados).

---

## Funcionalidades

| Módulo | Destaques |
| :--- | :--- |
| **Dashboard** | KPIs responsivos com sparklines animados, disponível para gastar, próximos vencimentos, Receitas × Despesas (12 meses), Donut interativo por categoria (clique para filtrar), evolução de saldo e orçamentos |
| **Transações** | Busca com debounce, filtros por tipo/categoria/cartão/ordenação, agrupamento por data com números tabulares, edição de categoria em lote, exclusão em lote e **Desfazer (5s)** |
| **Importação** | *Drag-and-drop* de `OFX`, `CSV` (Nubank, Inter, C6, genérico) e `PDF` com detecção automática de duplicatas, preview editável de categorias e vínculo com cartão |
| **Cartões de Crédito** | Fatura mensal, barra animada de limite utilizado/disponível e controle de fechamento/vencimento |
| **Investimentos** | Carteira local (ações, FIIs, renda fixa, ETFs, fundos CVM, cripto), gráfico donut de alocação, PnL e atualização opcional de cotações com 1 clique |
| **Relatórios & IA** | Insights locais, gráfico de sazonalidade, detecção automática de recorrências, simulador de cenários, exportação em **PDF** e análise opcional com IA |
| **MEI (Brasil)** | Cadastro de CNPJ e atividade, barra do teto anual (R$ 81.000) com alerta de risco, confirmação de DAS com 1 clique, clientes, notas com recebimento no caixa e importação de **NF-e XML** |
| **Privacidade & Ajustes** | Multi-perfil, categorias, metas, orçamentos, regras automáticas, patrimônio (ativos/passivos), backup/restore `.orcfin.bak` criptografado, export CSV/JSON, diagnóstico sanitizado `.txt`, verificação manual de atualizações e modo offline estrito |

---

## Arquitetura

```text
┌──────────────────────────────────────────────────────────┐
│  Janela Desktop Nativa (pywebview / Windows WebView2)    │
│  React 19 · TypeScript · Tailwind v4 · Motion · Recharts │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP Local (127.0.0.1, porta livre)
┌──────────────────────────▼───────────────────────────────┐
│  API Local (FastAPI + Uvicorn em thread interna)         │
├──────────────────────────────────────────────────────────┤
│  Motor Core (Python 3.11+ · Pydantic v2 · SQLite WAL)    │
│  Parsers (OFX/CSV/PDF/XML) · MEI · Carteira · Cripto     │
└──────────────────────────────────────────────────────────┘
```

---

## Rodar a partir do código-fonte

Requisitos: **Python 3.11+** e **Node.js 20+**.

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin

# 1. Dependências Python
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 2. Build do frontend React
cd frontend
npm ci
npm run build
cd ..

# 3. Abrir o aplicativo desktop nativo
python main.py
```

### Testes e Empacotamento

```powershell
# Rodar suíte completa de testes (215+ testes isolados)
pytest -q

# Gerar pacote portátil Windows (dist/OrcFin-portable.zip)
python scripts/package_portable.py
```

---

## Documentação

- [Instalação no Windows e Atualizações](install-windows.md)
- [Primeiros Passos](getting-started.md)
- [Privacidade e LGPD](privacy.md)
- [Importadores de Extrato](importers.md)
- [Modelo de Dados (Schema v15)](data-model.md)
- [Changelog](../CHANGELOG.md)

---

## Contribuição e Licença

Issues e pull requests são bem-vindos. Rode `pytest -q` e `npm --prefix frontend run build` antes de abrir um PR.

Licenciado sob [GNU General Public License v3.0](../LICENSE).
