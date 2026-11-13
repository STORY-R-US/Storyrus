"""Valida as fontes incluídas no projeto, sem rede (nome preservado para builds)."""

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "assets" / "fonts"


def main() -> int:
    from reportlab.pdfbase.ttfonts import TTFont

    for name in (
        "Andika-Regular",
        "Andika-Bold",
        "Andika-Italic",
        "PlayfairDisplay-Regular",
        "Fredoka-Bold",
    ):
        TTFont(name, str(OUT_DIR / f"{name}.ttf"))
    if not (OUT_DIR / "Andika-OFL.txt").is_file():
        raise FileNotFoundError("Licença da Andika ausente")
    print("[fonts] Fontes locais validadas; nenhum download necessário.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
