import re
import ast
from pathlib import Path

pt_re = re.compile(
    r"(ção|ções|ão |ões |não|Não|você|Você|salvar|Salvar|cancelar|Cancelar|"
    r"erro|Erro|perfil|Perfil|lançament|despesa|receita|orçament|configura|"
    r"importar|Importar|meta |Meta|backup|Backup|relatório|cartão|Cartão|"
    r"Excluir|Novo |Nova |Confirmar|Selecione|Nenhum|Nenhuma|posição|Posição|"
    r"fatura|Fatura|Obriga|Investiment|Carteira|Análise|Provedor)",
    re.I,
)

roots = [Path("ui"), Path("core/engine"), Path("core/privacy.py"), Path("core/ai")]
hits = []
for root in roots:
    paths = [root] if root.is_file() else list(root.rglob("*.py"))
    for p in paths:
        if not p.is_file():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                s = n.value
                if (
                    4 <= len(s) < 220
                    and pt_re.search(s)
                    and not s.startswith(("http", "#", "/", "[", "_", "demo:", "{"))
                ):
                    hits.append(f"{p}:{n.lineno}:{s[:120].replace(chr(10), ' ')}")

print(len(hits))
for h in hits:
    print(h)
