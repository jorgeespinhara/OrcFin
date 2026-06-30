"""Build OrcFin Windows executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Instale PyInstaller: pip install pyinstaller")
        return 1

    sep = ";" if sys.platform.startswith("win") else ":"
    assets = f"assets{sep}assets"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ROOT / "main.py"),
        "--name=OrcFin",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--add-data={assets}",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT / 'scripts'}",
        "--hidden-import=sqlite3",
        "--hidden-import=keyring.backends.Windows",
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())