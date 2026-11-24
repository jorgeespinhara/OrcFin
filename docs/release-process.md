# Processo de Release

1. Atualizar `APP_VERSION` em `core/branding.py`, `#define AppVersion` em `scripts/installer/orcfin.iss` e adicionar a seção em `CHANGELOG.md`.
2. Atualizar `.github/release-body.md` com os destaques da versão.
3. Validar localmente:
   - `npm --prefix frontend run build`
   - `pytest -q`
   - (Opcional) `python scripts/package_portable.py` → gera `dist/OrcFin-portable/` e `dist/OrcFin-portable.zip`.
4. Commit na `main` e `git push origin main`.
5. Criar e enviar a tag:
   ```powershell
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

## Automação no CI (`.github/workflows/release.yml`)

Ao receber uma tag `v*`, o GitHub Actions executa automaticamente:

1. **Testes & Segurança (Ubuntu):** `pytest -q` + `gitleaks`.
2. **Build Windows:**
   - Compila o frontend React (`cd frontend && npm ci && npm run build`);
   - Empacota o executável desktop (`python scripts/package_portable.py` via PyInstaller + `pywebview`, sem Flet/Flutter) → `dist/OrcFin-portable.zip`;
   - Compila o instalador Windows com Inno Setup 6 (`scripts/installer/orcfin.iss`) → `dist/OrcFin-Setup.exe`.
3. **Publicação:** cria a GitHub Release anexando **`OrcFin-Setup.exe`** e **`OrcFin-portable.zip`** com o texto de `.github/release-body.md`.
