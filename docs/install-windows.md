# Instalação no Windows

O OrcFin pode ser usado de duas formas: **pacote portátil** (recomendado para uso diário) ou **código-fonte** (desenvolvimento).

## Pacote portátil (sem Python)

O ZIP de release é **onedir completo**: `OrcFin.exe` + pasta `_internal` com o runtime Python e **todas as dependências de execução** (Flet/desktop, Pydantic, PDF, OFX, criptografia, SDKs de IA, yfinance, etc.). O usuário final **não** roda `pip install`.

> Aviso: quem **gera** o pacote (desenvolvedor/CI) precisa de Python 3.11+ e `pip install -r requirements.txt` **uma vez no ambiente de build**. Isso não se aplica a quem só baixa a release.

### Baixar ou gerar o pacote

- **Release:** [GitHub Releases](https://github.com/jorgeespinhara/OrcFin/releases) → `OrcFin-portable.zip`.
- **Local (build):**

```powershell
cd OrcFin
pip install -r requirements.txt
python scripts/package_portable.py
```

Artefato: `dist/OrcFin-portable.zip`. Extraído: `OrcFin.exe`, `_internal\` e `LEIA-ME.txt` (lista o que está embutido).

### Instalar (usuário final)

1. Extraia o ZIP em qualquer pasta (por exemplo `C:\Programas\OrcFin` ou a Área de Trabalho).
2. **Mantenha** a pasta `_internal` ao lado de `OrcFin.exe`.
3. Execute `OrcFin.exe`.
4. Na primeira abertura, siga o assistente inicial.

Não é necessário instalador `.msi` nem Python no PC do usuário. Você pode criar um atalho para `OrcFin.exe` na Área de Trabalho.

### Dependências embutidas vs. opcionais

| Já embutido no ZIP | Opcional / fora do ZIP |
|--------------------|-------------------------|
| Runtime Python, Flet/desktop, SQLite, Pydantic, fpdf2, pandas, ofxparse, pdfplumber, cryptography, keyring, defusedxml, SDKs openai/anthropic, yfinance | API keys de IA (você cola em Configurações); rede para IA/cotações se ativar |

### Onde ficam os dados

Por padrão no Windows:

```
C:\OrcFin\
├── data\orcfin.db
├── config\settings.json
└── backups\
```

No assistente inicial você pode escolher outra pasta. A escolha fica registrada em `C:\OrcFin\config\data_root.txt`.

Os dados **não** ficam na pasta do executável; assim você pode mover ou atualizar o app sem perder o banco.

### Antivírus e SmartScreen

Executáveis gerados com `flet pack` (PyInstaller), sem assinatura digital, podem ser sinalizados pelo Windows Defender ou SmartScreen. Isso é comum em apps independentes. Se confiar na origem (build seu ou release oficial do repositório), use “Mais informações” → “Executar mesmo assim”, ou adicione exceção no antivírus.

## Código-fonte (desenvolvimento)

Requisitos: Python 3.11+, dependências em `requirements.txt`.

```powershell
git clone https://github.com/jorgeespinhara/OrcFin.git
cd OrcFin
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Atalho na Área de Trabalho (recria se o projeto mudou de pasta ou o ícone sumiu):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
```

Por padrão (`Auto`) aponta para `dist\OrcFin-portable\OrcFin.exe` se existir; senão usa `pythonw` + `main.py`. Opções: `-Mode Product`, `-Mode Dev`, ou `-ExePath "C:\caminho\OrcFin.exe"`.

## Atualizar versão

1. Feche o OrcFin.
2. Substitua a pasta do executável ou extraia o novo ZIP por cima (mantendo apenas `OrcFin.exe` e `_internal`).
3. **Não apague** `C:\OrcFin` (ou a pasta de dados que você escolheu).

## Desinstalar

1. Feche o OrcFin.
2. Apague a pasta do executável.
3. Se quiser remover todos os dados financeiros, apague também a pasta de dados (`C:\OrcFin` por padrão).