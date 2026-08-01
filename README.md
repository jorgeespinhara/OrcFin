<img width="1920" height="1032" alt="2026-08-01_18h08_04" src="https://github.com/user-attachments/assets/fb720e21-f423-4af7-a236-ac07d2266737" /># OrcFin

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/UI-Flet-00B4D8.svg)](https://flet.dev)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

**Orçamento financeiro local para pessoa física e MEI**

OrcFin é um aplicativo desktop em Python para controle financeiro pessoal e gestão de MEI. Tudo roda no seu computador: banco SQLite local, importação de extratos sem envio à nuvem e integração com IA opcional — apenas com resumos agregados, nunca com linhas individuais de transação.

Repositório: [github.com/jorgeespinhara/OrcFin](https://github.com/jorgeespinhara/OrcFin)

---

## Índice

- [Para quem é](#para-quem-é)
- [Como funciona na prática](#como-funciona-na-prática)
- [Por que OrcFin?](#por-que-orcfin)
- [Funcionalidades](#funcionalidades)
- [Privacidade e dados](#privacidade-e-dados)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Documentação](#documentação)
- [Importação de extratos](#importação-de-extratos)
- [Integração com IA](#integração-com-ia-opcional)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Stack técnica](#stack-técnica)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## Para quem é

**Para quem é:** pessoa física, casal, freelancer ou MEI que quer organizar finanças **localmente**, importar extratos brasileiros, acompanhar orçamento e vencimentos, gerar relatórios e exportar backup — sem depender de nuvem para os seus lançamentos.

**Para quem não é:** quem precisa de sincronização bancária automática em tempo real, app mobile completo ou software que substitua assessoria contábil, fiscal ou jurídica. O OrcFin organiza; decisões oficiais continuam com um profissional habilitado.

---

## Como funciona na prática

Em vez de decorar menus, pense no fluxo:

1. **Importe** seu extrato ou fatura (CSV, OFX, PDF) — tudo processado no PC.
2. **Revise** o preview: duplicatas sinalizadas, categorias sugeridas, alertas de orçamento.
3. **Categorize** e ajuste o que faltar em Lançamentos.
4. **Veja o mês** no Dashboard: saldo, *quanto posso gastar*, vencimentos e decisões.
5. **Gere relatórios** (YTD, tendências, PDF) e, se quiser, análise com IA — só totais agregados.
6. **Exporte** backup `.orcfin`, CSV/JSON ou pacote contador (MEI) quando precisar sair ou arquivar.

**Quer só experimentar?** No último passo do assistente inicial, use **Explorar com dados fictícios**: o app preenche lançamentos de exemplo para você ver dashboards e relatórios sem expor dados reais. Depois apague em Lançamentos ou use **Instalação limpa** em Configurações.

---

## Por que OrcFin?

Porque minha esposa pediu 😊

Brincadeiras à parte: faltava um lugar simples para ver o mês, importar extratos brasileiros sem mandar nada pra nuvem, cuidar do MEI e ainda ter backup e exportação quando a gente quiser sair. Planilhas espalhadas e apps que misturam tudo não resolviam.

O OrcFin junta finanças pessoais e MEI no mesmo app, com dados no seu computador. Você importa faturas localmente, acompanha orçamento e vencimentos, gera pacote pro contador e decide se quer IA — só com totais agregados, nunca linha por linha.

---

## Funcionalidades

Referência rápida por área (o fluxo acima costuma ser o caminho mais natural no dia a dia).

### Modo Pessoal

| Área | O que você pode fazer |
|------|------------------------|
| **Dashboard** | KPIs, decisões do mês com ações, central de insights, projeção, orçamentos, patrimônio, *quanto posso gastar* e calendário de vencimentos |
| **Lançamentos** | CRUD, busca, recorrências, parcelamentos, split de despesas e transferências entre perfis |
| **Cartões** | Cadastro, resumo e importação de faturas |
| **Importação** | Preview antes de confirmar, detecção de duplicatas, regras de categorização e alertas de orçamento |
| **Relatórios & IA** | YTD, tendências, comparação sazonal, simulador de cenários, detecção de recorrências, exportação PDF e análises com IA por provedor |
| **Configurações** | Perfis, categorias, metas, patrimônio, orçamentos, aparência (tema claro/escuro), backup agendado com restauração guiada e exportação CSV/JSON |

### Modo MEI

| Área | O que você pode fazer |
|------|------------------------|
| **Início** | KPIs, alertas de limite e DAS, gráficos de faturamento |
| **Vendas & clientes** | Receitas e cadastro de tomadores |
| **Obrigações** | DAS mensal, checklist, limite anual, simulação ME e exportação de lembretes `.ics` |
| **Notas** | Controle de NFs, aging de recebíveis, recibo PDF, importação de XML NF-e/NFS-e e baixa com lançamento de receita |
| **Resultado** | Relatório mensal simplificado, PDF e pacote contador (ZIP com PDF + CSVs) |
| **Lançamentos** | Despesas dedutíveis e não dedutíveis |

---
## Telas

<img width="1920" height="1032" alt="2026-08-01_18h09_47" src="https://github.com/user-attachments/assets/39318862-c328-4476-b0eb-4f59920863a6" />

<img width="1920" height="1032" alt="2026-08-01_18h09_39" src="https://github.com/user-attachments/assets/e5620c22-6647-4dba-b6a2-ac3c68d4bafa" />

<img width="1920" height="1032" alt="2026-08-01_18h09_03" src="https://github.com/user-attachments/assets/382e4789-e982-4d33-991e-b89b20f09896" />

<img width="1920" height="1032" alt="2026-08-01_18h08_24" src="https://github.com/user-attachments/assets/f592dade-a238-4e68-82ab-a9a96493aa9a" />

<img width="1920" height="1032" alt="2026-08-01_18h07_55" src="https://github.com/user-attachments/assets/5c7f3b6e-6157-49f2-9a26-e0230830efd1" />

<img width="506" height="573" alt="image" src="https://github.com/user-attachments/assets/617f8881-c59a-45fa-a46f-acc481ef38f0" />

<img width="506" height="573" alt="image" src="https://github.com/user-attachments/assets/f2cb7b24-544e-49c9-a728-2465a173e88c" />

<img width="1920" height="1032" alt="2026-08-01_18h10_10" src="https://github.com/user-attachments/assets/83c16c75-488b-4150-8159-055c094de163" />

<img width="1920" height="1032" alt="2026-08-01_18h09_54" src="https://github.com/user-attachments/assets/5787a6dc-250f-4572-9cfe-3bfb81b99c26" />

---
## Privacidade e dados

OrcFin foi pensado para quem prefere manter dados financeiros sob controle próprio.

| Aspecto | Comportamento |
|---------|---------------|
| **Armazenamento** | SQLite na pasta de dados do usuário (`C:\OrcFin` no Windows por padrão; configurável no assistente inicial) |
| **Importação** | Processamento 100% local — extratos e faturas não saem do PC |
| **IA (opcional)** | Provedores externos recebem apenas totais agregados (sem descrições nem linhas de transação); preview obrigatório antes do envio |
| **Modo offline** | Switch em Configurações → Privacidade e dados bloqueia qualquer chamada externa |
| **Transparência** | Tela de privacidade mostra caminhos locais, tamanho do banco e registro de eventos externos |
| **Credenciais** | API keys por provedor, criptografadas com `cryptography` e keyring do sistema operacional |
| **Portabilidade** | Exportação CSV/JSON; backup `.orcfin` criptografado; pacote contador MEI em ZIP |

> **Aviso:** OrcFin é uma ferramenta de organização financeira. Não substitui assessoria contábil, fiscal ou jurídica. Valide obrigações MEI e declarações com um profissional habilitado.

---

## Requisitos

**Uso com executável (Windows):** nenhum pré-requisito; extraia o pacote portátil e execute `OrcFin.exe`.

**Desenvolvimento:** Python **3.11+**, Windows, macOS ou Linux (desktop); ambiente virtual recomendado.

---

## Instalação

### Windows — pacote portátil (recomendado)

1. Baixe `OrcFin-portable.zip` na [última release](https://github.com/jorgeespinhara/OrcFin/releases/latest) ou gere localmente (abaixo).
2. Extraia a pasta e execute **`OrcFin.exe`**.
3. Siga o **assistente de primeira execução** — recomendamos **Explorar com dados fictícios** na primeira vez, se ainda não tiver extrato em mãos.

Seus dados ficam em **`C:\OrcFin`** por padrão (ou na pasta que você escolher no assistente), não na pasta do `.exe`.

Guia completo: [docs/install-windows.md](docs/install-windows.md) · [Primeiros passos](docs/getting-started.md)

### Gerar o pacote portátil

```powershell
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
pip install -r requirements.txt
python scripts/package_portable.py
```

Artefatos: `dist/OrcFin-portable.zip` e `dist/OrcFin-portable/OrcFin.exe`.

### Código-fonte (desenvolvimento)

```bash
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python main.py
```

Atalho na Área de Trabalho (modo dev, requer Python):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
```

Na primeira execução o app cria o banco, perfis padrão (**Usuário 1** e **Usuário 2**) e categorias comuns.

### Testes automatizados

```bash
pytest
```

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [install-windows.md](docs/install-windows.md) | Pacote portátil, atualização, desinstalação, antivírus |
| [getting-started.md](docs/getting-started.md) | Assistente inicial, importação, backup, dados fictícios |
| [privacy.md](docs/privacy.md) | O que fica local, IA opcional, exportação e exclusão |
| [privacy-model.md](docs/privacy-model.md) | Modelo de privacidade e limites de rede |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |

---

## Importação de extratos

Disponível em **Cartões** ou em **Lançamentos → Importar**.

| Formato | Instituições / observações |
|---------|----------------------------|
| **CSV** | Nubank (detecção automática), Inter, C6, Bradesco, Itaú e CSV genérico |
| **OFX / QFX** | Extratos bancários no padrão OFX |
| **PDF** | Nubank e parsing genérico de texto (BTG, Itaú, entre outros) |

O preview lista todas as linhas parseadas antes da confirmação. Duplicatas (data + valor + descrição) são sinalizadas e desmarcadas por padrão.

---

## Integração com IA (opcional)

A IA é **opcional** e usa a **API** de cada provedor (não o chat gratuito do site). Sem chave configurada, o app mantém análises locais no dashboard e fallback offline nos relatórios.

### Provedores suportados

| Provedor | Observação |
|----------|------------|
| **DeepSeek** | Créditos gratuitos no cadastro em [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| **Grok (xAI)** | Chave em [console.x.ai](https://console.x.ai/) |
| **Gemini (Google)** | Camada gratuita com API key em [aistudio.google.com](https://aistudio.google.com/apikey) |
| **ChatGPT (OpenAI)** | API paga; `gpt-4o-mini` é o modelo padrão mais econômico |
| **Claude (Anthropic)** | API paga; Haiku é o modelo padrão mais barato |

### Como configurar

1. Abra **Configurações → Integração com IA**
2. Informe a API key de cada provedor que deseja usar (cada um tem card próprio)
3. Use **Testar conexão** para validar antes de gerar análises
4. Em **Relatórios & IA**, escolha o provedor pelo botão correspondente

Cada provedor envia apenas um resumo numérico agregado do período — nunca descrições de lançamentos nem dados pessoais identificáveis.

---

## Estrutura do projeto

```
OrcFin/
├── main.py                 # Ponto de entrada (Flet)
├── requirements.txt
├── core/
│   ├── db/                 # SQLite: schema, migrations, repositories
│   ├── domain/             # Enums, entidades, formatação (ex.: Jan/2026)
│   ├── engine/             # Reporting, projeções, sazonalidade, spendable, due dates
│   ├── import_parsers/     # CSV, OFX, PDF e parsers por banco
│   ├── services/           # Importação, MEI, cartões
│   ├── ai_gateway.py       # Multi-provedor (DeepSeek, Grok, Gemini, OpenAI, Claude) + fallback local
│   ├── paths.py            # Pasta de dados do usuário e migração
│   ├── settings_store.py   # Preferências e chaves de IA criptografadas
│   ├── backup.py           # Backup e restauração criptografados
│   ├── copy.py             # Textos e constantes de UI compartilhados
│   ├── data_export.py      # Exportação CSV/JSON
│   ├── mei_nfe_xml.py      # Importação NF-e XML
│   ├── mei_pack.py         # Pacote contador MEI
│   ├── mei_calendar.py     # Lembretes DAS (.ics)
│   └── pdf_generator.py    # Relatórios PDF
├── ui/
│   ├── theme.py            # Paletas claro/escuro e helpers de componentes
│   ├── settings/           # Configurações (view + seções por domínio)
│   ├── transactions/       # Lançamentos (data, table, form, actions)
│   ├── dashboard/          # Dashboard pessoal (cards + sections)
│   ├── reports/            # Relatórios & IA (sections + ai)
│   ├── onboarding/         # Assistente de primeira execução
│   ├── personal/charts/    # Gráficos reutilizáveis (bars, series, analysis)
│   └── ...                 # MEI, shell, theme
├── docs/                   # Guias de instalação, uso e privacidade
├── scripts/                # build_exe.py, package_portable.py, atalho desktop
├── assets/                 # Ícone e logo do app
├── data/                   # Legado local (migrado para pasta do usuário; não versionar .db)
├── exports/                # PDFs, ZIPs e CSVs exportados (gerados em runtime)
└── tests/                  # Suíte pytest
```

---
## Stack técnica

| Camada | Tecnologia |
|--------|------------|
| Interface | [Flet](https://flet.dev) 0.85.x |
| Dados | SQLite (schema v8, migrations versionadas) |
| Modelos | Pydantic 2 |
| Relatórios | fpdf2 |
| Importação | pandas, ofxparse, pdfplumber |
| Segurança | cryptography, keyring |
| Empacotamento | `flet pack` + `flet-desktop` (opcional) |

---

## Contribuindo

Contribuições são bem-vindas. Sugestões de fluxo:

1. Abra uma [issue](https://github.com/jorgeespinhara/OrcFin/issues) para discutir mudanças maiores
2. Faça fork do repositório e crie um branch descritivo
3. Mantenha o escopo focado e adicione testes quando aplicável
4. Execute `pytest` antes de abrir o pull request
5. Descreva o que mudou e por quê no PR

Para bugs, inclua passos para reproduzir, sistema operacional e versão do Python.

---

## Licença

Este projeto é software livre sob a [GNU General Public License v3.0](LICENSE) (GPL-3.0).

---

**OrcFin** — Controle financeiro pessoal e MEI no mesmo lugar: local, privado e sob seu controle.
