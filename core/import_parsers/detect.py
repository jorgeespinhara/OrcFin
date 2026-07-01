"""Detect financial institution and file format from content."""

from pathlib import Path


def detect_format(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    head = content[:4096].decode("utf-8", errors="ignore").upper()

    if ext == ".ofx" or ext == ".qfx" or "<OFX>" in head or "OFXHEADER" in head:
        return "ofx"
    if ext == ".pdf" or content[:4] == b"%PDF":
        return "pdf"
    if ext == ".csv" or "," in head[:500]:
        return "csv"
    raise ValueError(f"Formato não suportado: {ext or 'desconhecido'}")


def detect_csv_institution(content: str, filename: str = "") -> str:
    fname = filename.lower()
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    while lines and "data" not in lines[0].lower() and "date" not in lines[0].lower():
        lines.pop(0)
    first = lines[0].lower() if lines else ""
    head = content[:3000].lower()

    for key, label in (
        ("santander", "santander"),
        ("caixa", "caixa"),
        ("inter", "inter"),
        ("c6", "c6"),
        ("bradesco", "bradesco"),
        ("itau", "itau"),
        ("itaú", "itau"),
    ):
        if key in fname:
            return label

    if "nubank" in first or all(col in first for col in ("date", "title", "amount")):
        return "nubank"
    if "banco inter" in head or ("inter" in head and "data" in first and "valor" in first):
        return "inter"
    if "c6 bank" in head or ("c6" in head and "data" in first and "valor" in first):
        return "c6"
    if "bradesco" in head or ("data" in first and ("débito" in first or "debito" in first or "crédito" in first)):
        return "bradesco"
    if "santander" in head or ("data" in first and "hist" in first and "valor" in first):
        return "santander"
    if "caixa" in head or "cef" in head:
        return "caixa"
    if "itaú" in head or "itau" in head or ("data" in first and "lançamento" in first):
        return "itau"
    if all(col in first for col in ("data", "descri", "valor")):
        return "nubank"
    return "generic_csv"