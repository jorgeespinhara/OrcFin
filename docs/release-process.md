# Release

1. Bump `APP_VERSION` em `core/branding.py` e seção em `CHANGELOG.md`
2. Atualizar `.github/release-body.md` (notas da release + aviso de dependências embutidas)
3. `pytest -q`
4. (Opcional local) `python scripts/package_portable.py` → `dist/OrcFin-portable.zip`
5. Commit na `main`, push
6. Tag e push: `git tag vX.Y.Z` e `git push origin vX.Y.Z`

CI (`.github/workflows/release.yml`) no push da tag:

- roda testes
- `flet pack` + `package_portable.py` no Windows (embute runtime + deps)
- cria GitHub Release com `OrcFin-portable.zip`

O usuário final **não** instala Python/pip; o ZIP é autocontido (`OrcFin.exe` + `_internal`).