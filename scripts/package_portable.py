"""Build OrcFin.exe and zip portable distribution."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(ROOT))
from core.branding import APP_VERSION


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
    shutil.copytree(dist_exe.parent, bundle_dir) if dist_exe.parent.name == "OrcFin" else None
    if not bundle_dir.exists():
        bundle_dir.mkdir(parents=True)
        shutil.copy2(dist_exe, bundle_dir / "OrcFin.exe")

    readme = bundle_dir / "LEIA-ME.txt"
    readme.write_text(
        f"OrcFin portátil v{APP_VERSION}\n\n"
        "1. Extraia esta pasta em qualquer local\n"
        "2. Execute OrcFin.exe\n"
        "3. Confira na barra de título: OrcFin v" + APP_VERSION + "\n"
        "4. Seus dados ficam em C:\\OrcFin (ou na pasta que você escolher no assistente)\n",
        encoding="utf-8",
    )

    zip_path = ROOT / "dist" / "OrcFin-portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(bundle_dir.parent))

    print(f"Pacote: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())