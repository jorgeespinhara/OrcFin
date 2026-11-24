# Instalação no Windows

O OrcFin v1.0.0 pode ser instalado de três formas: **Instalador Windows** (recomendado), **Pacote portátil (ZIP)** ou **Código-fonte** (desenvolvimento).

## 1. Instalador Windows (`OrcFin-Setup.exe`) — Recomendado

- Baixe **`OrcFin-Setup.exe`** (~58 MB) na [última release](https://github.com/jorgeespinhara/OrcFin/releases/latest).
- Instalação **por usuário** (não exige privilégios de administrador).
- Cria atalhos no Menu Iniciar e (opcionalmente) na Área de Trabalho, com desinstalador limpo no Windows.
- Já inclui o runtime Python e a interface compilada (**React + WebView2**) — **não** exige instalar Python nem Node.js.

## 2. Pacote portátil (`OrcFin-portable.zip`)

O ZIP de release (~76 MB) é **onedir completo**: `OrcFin.exe` + pasta `_internal` com o runtime Python, o build do frontend React e todas as dependências embutidas via PyInstaller.

1. Baixe `OrcFin-portable.zip` em [GitHub Releases](https://github.com/jorgeespinhara/OrcFin/releases/latest).
2. Extraia em qualquer pasta (ex.: `C:\Programas\OrcFin`).
3. **Mantenha** a pasta `_internal` ao lado de `OrcFin.exe`.
4. Execute `OrcFin.exe`.

### Dependências embutidas vs. opcionais

| Já embutido no Instalador / ZIP | Opcional / fora do pacote |
|---|---|
| Runtime Python, `pywebview` (WebView2 nativo), FastAPI/Uvicorn, frontend React compilado, SQLite, Pydantic, fpdf2, pandas, ofxparse, pdfplumber, cryptography, keyring, defusedxml, SDKs openai/anthropic, yfinance | API keys de IA (configuradas no app); acesso à rede para IA, cotações ou checagem manual de atualizações |

### Onde ficam os dados

Por padrão no Windows:

```text
C:\OrcFin\
├── data\orcfin.db
├── config\settings.json
└── backups\
```

Os dados **não** ficam na pasta do executável; assim você pode atualizar ou reinstalar o OrcFin sem perder seu banco financeiro.

### Antivírus e SmartScreen

Executáveis sem assinatura digital comercial podem ser sinalizados pelo Windows Defender ou SmartScreen. Ao baixar da release oficial deste repositório, use **“Mais informações” → “Executar mesmo assim”**.

---

## 3. Código-fonte (desenvolvimento)

Requisitos: **Python 3.11+** e **Node.js 20+**.

```powershell
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin

# Backend Python
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend React
cd frontend
npm ci
npm run build
cd ..

# Abrir aplicativo desktop
python main.py
```

### Gerar pacote portátil e instalador localmente

```powershell
# 1. Compilar o frontend
npm --prefix frontend run build

# 2. Gerar dist/OrcFin-portable/ e dist/OrcFin-portable.zip
python scripts/package_portable.py

# 3. (Opcional, com Inno Setup 6) Gerar dist/OrcFin-Setup.exe
iscc scripts\installer\orcfin.iss
```

Atalho na Área de Trabalho:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
```

## Atualizar versão

1. Feche o OrcFin.
2. Execute o novo **`OrcFin-Setup.exe`** (ou extraia o novo `OrcFin-portable.zip` por cima).
3. **Não apague** `C:\OrcFin` (seus dados são preservados automaticamente).

## Desinstalar

- **Se usou o instalador:** desinstale por *Configurações do Windows → Aplicativos → OrcFin*.
- **Se usou o portátil:** feche o app e apague a pasta extraída.
- Para apagar também os dados financeiros, remova manualmente `C:\OrcFin`.
