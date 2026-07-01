# OrcFin

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/UI-Flet-00B4D8.svg)](https://flet.dev)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

**Orçamento financeiro local para pessoa física e MEI**

OrcFin é um aplicativo desktop em Python para controle financeiro pessoal e gestão de MEI. Tudo roda no seu computador: banco SQLite local, importação de extratos sem envio à nuvem e integração com IA opcional — apenas com resumos agregados, nunca com linhas individuais de transação.

Repositório: [github.com/jorgeespinhara/OrcFin](https://github.com/jorgeespinhara/OrcFin)

---

## Índice

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
- [Roadmap](#roadmap)
- [Licença](#licença)

---

## Por que OrcFin?

| Necessidade | Como o OrcFin atende |
|-------------|----------------------|
| Finanças pessoais e MEI no mesmo lugar | Dois modos integrados, com categorias e relatórios separados |
| Casal ou múltiplas contas | Perfis individuais e visão consolidada |
| Extratos brasileiros | Parsers para Nubank, Inter, C6, Bradesco, Itaú, OFX e PDF |
| Obrigações MEI | DAS, limite de faturamento, notas, pacote para contador, lembretes `.ics` |
| Sem dependência de nuvem | Motor de projeções, orçamentos e análises 100% offline |
| Portabilidade | Backup criptografado e exportação aberta em CSV/JSON |
| Conforto visual | Tema escuro e claro com contrastes legíveis em toda a interface |

---

## Funcionalidades

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

1. Baixe `OrcFin-portable.zip` em [Releases](https://github.com/jorgeespinhara/OrcFin/releases) ou gere localmente (abaixo).
2. Extraia a pasta e execute **`OrcFin.exe`**.
3. Siga o **assistente de primeira execução** (modo de uso, pasta dos dados, backup, importação ou dados fictícios).

Seus dados ficam em **`C:\OrcFin`** por padrão (ou na pasta que você escolher no assistente), não na pasta do `.exe`.

Guia completo: [docs/install-windows.md](docs/install-windows.md) · [Primeiros passos](docs/getting-started.md)

### Gerar o pacote portátil

```powershell
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
pip install -r requirements.txt
pip install pyinstaller
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
| Empacotamento | PyInstaller (opcional) |

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

## Roadmap

**Concluído**

- [x] Backup agendado e restauração guiada
- [x] Detecção de duplicatas na importação
- [x] Busca em lançamentos, split e transferências entre perfis
- [x] Calendário de vencimentos e *quanto posso gastar*
- [x] Parsers Inter, C6, Bradesco e Itaú
- [x] Importação NF-e XML, pacote contador e calendário DAS (`.ics`)
- [x] Análises locais offline e exportação CSV/JSON
- [x] Empacotamento PyInstaller
- [x] Tema claro e escuro com contrastes legíveis
- [x] IA multi-provedor (DeepSeek, Grok, Gemini, ChatGPT, Claude)
- [x] Pasta de dados do usuário fora do repositório (`C:\OrcFin` no Windows)
- [x] Assistente de primeira execução e dados fictícios de demonstração
- [x] Pacote portátil Windows (`OrcFin-portable.zip`) e CI de release

**Planejado**

- [x] Tela de privacidade verificável (dados locais, modo offline, preview de IA)
- [x] Importação com histórico, confiança por linha e desfazer lote (soft-delete)
- [x] Score de backup, testar backup e pasta configurável
- [x] Decisões do mês com ações e insights MEI
- [x] Auditoria local (`change_log`) e histórico de análises IA
- [x] Mapeador CSV com templates salvos e preview de backup em sandbox
- [x] Detalhe de lançamento com origem e trilha local
- [ ] Mais layouts de PDF por banco (Santander/Caixa em modo genérico)
- [ ] Companion mobile (leitura de export/backup)

---

## Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para os termos completos.

---

**OrcFin** — Controle financeiro pessoal e MEI no mesmo lugar: local, privado e sob seu controle.