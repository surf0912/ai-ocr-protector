#!/usr/bin/env python3
"""Regenerate the UI webfont subsets for 防窺工坊 (app.py).

Run this after changing any visible UI text, so the embedded webfonts cover every
glyph the UI uses while staying tiny:

    ./.venv/bin/python regen_fonts.py

Source fonts are NOT committed (too big). Keep them in ./font-sources/:
  - YuseiMagic-Regular-2.ttf   primary UI font (Japanese; covers most Traditional)
  - jf-openhuninn.ttf          Traditional-Chinese fallback (粉圓), covers the rest

Outputs (committed):  assets/uifont.woff2  +  assets/uifont-fallback.woff2
Requires (dev only):  pip install fonttools brotli
"""
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "font-sources"
PRIMARY = SRC / "YuseiMagic-Regular-2.ttf"
FALLBACK = SRC / "jf-openhuninn.ttf"


def charset() -> str:
    chars = set((ROOT / "app.py").read_text("utf-8"))
    chars |= set(string.printable) | set("0123456789")
    chars |= set("×·…—、。，！？：；「」（）『』〇±•‧σµ²³°’‘“”　")
    return "".join(sorted(chars))


def subset(src: Path, out: Path, text_file: Path) -> None:
    if not src.exists():
        sys.exit(f"❌ missing source font: {src}\n   put it in font-sources/ (not committed).")
    subprocess.run(
        [sys.executable, "-m", "fontTools.subset", str(src),
         f"--text-file={text_file}", "--flavor=woff2",
         f"--output-file={out}", "--layout-features=*", "--desubroutinize"],
        check=True,
    )
    print(f"  {out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


def main() -> None:
    text = charset()
    tmp = ROOT / ".subset_chars.txt"
    tmp.write_text(text, "utf-8")
    print(f"subsetting to {len(set(text))} chars…")
    subset(PRIMARY, ROOT / "assets" / "uifont.woff2", tmp)
    subset(FALLBACK, ROOT / "assets" / "uifont-fallback.woff2", tmp)
    tmp.unlink(missing_ok=True)

    from fontTools.ttLib import TTFont
    a = set(TTFont(ROOT / "assets" / "uifont.woff2").getBestCmap())
    b = set(TTFont(ROOT / "assets" / "uifont-fallback.woff2").getBestCmap())
    cjk = {c for c in (ROOT / "app.py").read_text("utf-8") if "㐀" <= c <= "鿿"}
    miss = [c for c in sorted(cjk) if ord(c) not in a and ord(c) not in b]
    print("coverage:", "✅ 0 missing" if not miss else "❌ MISSING: " + "".join(miss))


if __name__ == "__main__":
    main()
