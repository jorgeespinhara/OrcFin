# Instalação no Windows

O OrcFin pode ser usado de duas formas: **pacote portátil** (recomendado para uso diário) ou **código-fonte** (desenvolvimento).

## Pacote portátil (sem Python)

### Baixar ou gerar o pacote

- **Release:** quando disponível em [GitHub Releases](https://github.com/jorgeespinhara/OrcFin/releases), baixe `OrcFin-portable.zip`.
- **Local:** após clonar o repositório, gere o pacote:

```powershell
cd OrcFin
pip install -r requirements.txt
python scripts/package_portable.py
```

O arquivo ficará em `dist/OrcFin-portable.zip`. A pasta extraída contém `OrcFin.exe` e `LEIA-ME.txt`.

### Instalar

1. Extraia o ZIP em qualquer pasta (por exemplo `C:\Programas\OrcFin` ou a Área de Trabalho).
2. Execute `OrcFin.exe`.
3. Na primeira abertura, siga o assistente inicial.

Não é necessário instalador `.msi`: o app é portátil. Você pode criar um atalho para `OrcFin.exe` na Área de Trabalho.

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

Atalho opcional na Área de Trabalho (modo desenvolvimento, usa `pythonw`):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
```

## Atualizar versão

1. Feche o OrcFin.
2. Substitua a pasta do executável ou extraia o novo ZIP por cima (mantendo apenas `OrcFin.exe` e `_internal`).
3. **Não apague** `C:\OrcFin` (ou a pasta de dados que você escolheu).

## Desinstalar

1. Feche o OrcFin.
2. Apague a pasta do executável.
3. Se quiser remover todos os dados financeiros, apague também a pasta de dados (`C:\OrcFin` por padrão).