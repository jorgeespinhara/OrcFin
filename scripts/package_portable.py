"""Build OrcFin.exe and zip portable distribution.

The portable ZIP embeds Python runtime + all app dependencies via flet pack
(onedir). End users do NOT need Python, pip, or to install packages manually.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.branding import APP_VERSION  # noqa: E402

# Runtime packages shipped inside the portable build (from requirements.txt).
# Listed for LEIA-ME transparency — users do not install these separately.
EMBEDDED_RUNTIME_DEPS = (
    "Python runtime (embutido pelo flet pack / PyInstaller)",
    "Flet + flet-desktop (interface gráfica)",
    "SQLite (stdlib)",
    "Pydantic (validação)",
    "fpdf2 (PDF)",
    "pandas (tabelas/export)",
    "ofxparse (importação OFX)",
    "pdfplumber (importação PDF)",
    "cryptography + keyring (segredos/API keys)",
    "defusedxml (XML NF-e)",
    "openai + anthropic (SDKs de IA; uso só com chave e rede)",
    "yfinance (cotações opcionais; uso só com rede)",
)


def _write_readme(bundle_dir: Path) -> None:
    deps = "\n".join(f"  - {d}" for d in EMBEDDED_RUNTIME_DEPS)
    text = f"""OrcFin portátil v{APP_VERSION}
================================

O QUE É ESTE PACOTE
-------------------
Versão portátil completa para Windows. NÃO é necessário instalar Python,
pip nem nenhuma biblioteca listada abaixo — tudo já vem embutido em
OrcFin.exe e na pasta _internal (gerado com flet pack).

COMO USAR
---------
1. Extraia esta pasta em qualquer local (ex.: Área de Trabalho ou C:\\Programas\\OrcFin)
2. Execute OrcFin.exe
3. Confira na barra de título: OrcFin v{APP_VERSION}
4. Seus dados ficam em C:\\OrcFin (ou na pasta que você escolher no assistente)

NÃO apague a pasta _internal — ela contém o runtime e as dependências.

DEPENDÊNCIAS EMBUTIDAS (já incluídas — NÃO precisa instalar)
------------------------------------------------------------
{deps}

O QUE AINDA PODE PEDIR REDE / CONFIGURAÇÃO (opcional)
-----------------------------------------------------
- Análise com IA: você configura a API key em Configurações (não vem no ZIP)
- Cotações de investimentos (yfinance): só se você ativar e a rede estiver liberada
- Modo offline em Configurações bloqueia chamadas externas

Windows SmartScreen pode avisar em executáveis sem assinatura digital.
Se baixou da release oficial do repositório OrcFin, use "Mais informações"
→ "Executar mesmo assim".

Documentação: https://github.com/jorgeespinhara/OrcFin
"""
    (bundle_dir / "LEIA-ME.txt").write_text(text, encoding="utf-8")


def _verify_bundle(bundle_dir: Path) -> None:
    exe = bundle_dir / "OrcFin.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Falta OrcFin.exe em {bundle_dir}")
    internal = bundle_dir / "_internal"
    if not internal.is_dir():
        raise FileNotFoundError(
            f"Falta pasta _internal em {bundle_dir}. "
            "O build onedir deve embutir o runtime; sem isso o usuário precisaria de Python."
        )
    # flet_desktop must ship inside the frozen app (historical release breakage).
    markers = list(internal.rglob("*flet_desktop*"))
    if not markers:
        # Also accept nested module path patterns
        py_files = list(internal.rglob("flet_desktop*"))
        if not py_files:
            print(
                "AVISO: não encontrei 'flet_desktop' em _internal. "
                "Confirme que flet-desktop está instalado no ambiente de build."
            )
    size_mb = sum(f.stat().st_size for f in bundle_dir.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"Bundle verificado: {exe.name} + _internal (~{size_mb:.0f} MB)")


def main() -> int:
    if subprocess.call([sys.executable, str(ROOT / "scripts" / "build_exe.py")], cwd=str(ROOT)) != 0:
        return 1

    dist_exe = ROOT / "dist" / "OrcFin" / "OrcFin.exe"
    if not dist_exe.exists():
        dist_exe = ROOT / "dist" / "OrcFin.exe"
    if not dist_exe.exists():
        print("Executável não encontrado em dist/")
        return 1

    bundle_dir = ROOT / "dist" / "OrcFin-portable"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)

    if dist_exe.parent.name == "OrcFin":
        shutil.copytree(dist_exe.parent, bundle_dir)
    else:
        bundle_dir.mkdir(parents=True)
        shutil.copy2(dist_exe, bundle_dir / "OrcFin.exe")

    _write_readme(bundle_dir)
    try:
        _verify_bundle(bundle_dir)
    except FileNotFoundError as ex:
        print(f"ERRO: {ex}")
        return 1

    zip_path = ROOT / "dist" / "OrcFin-portable.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(bundle_dir.parent))

    print(f"Pacote: {zip_path}")
    print(f"Versão: {APP_VERSION}")
    print("Usuário final: extrair ZIP e rodar OrcFin.exe (sem pip/Python).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
