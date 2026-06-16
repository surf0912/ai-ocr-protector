# 🛡️ 預言家日報・防窺工坊 — AI / OCR Protection Image Processor

Upload an image and get back a version that is **harder for OCR and multimodal AI
to read or train on**, while a human can still recover it. Fully automatic —
upload, then download. Works with any image size. Traditional-Chinese,
Harry-Potter-flavoured UI.

> Intended for protecting **your own** images from being scraped / machine-extracted.

## Architecture — two repositories

| Repo | What it is | Hosting |
|------|------------|---------|
| **`ai-ocr-protector`** (this repo) | The Streamlit image processor (Python). The actual UI + pipeline. | Streamlit Community Cloud → `https://ai-ocr-protector.streamlit.app` |
| **`ai-ocr-protector-mobile`** | A PWA shell (HTML/JS/service-worker) that **iframes** the Streamlit app, adds splash screen, "add to home screen", offline shell, and app icons. | GitHub Pages |

The mobile shell is what users install on their phone. It loads
`…streamlit.app/?embed=true` in an iframe. **PWA icons / manifest / app name live
in the mobile repo**, not here.

## Protection pipeline (`processor.py`)

Applied in order; every step preserves the original pixel dimensions:

1. **Rotate 180° + horizontal mirror** (default on) — scrambles orientation for
   AI/OCR; a human flips it back. Recoverable, no information lost.
2. **Micro-warp** — a smooth displacement field distorts glyph geometry.
3. **Disruption mask** — randomized diagonal / cross-hatch / grid overlay.
4. **Gaussian noise** — breaks the clean edges OCR relies on.
5. **Optional blur** (off by default).

Parameters scale with image size. Output is always **JPG** (PNG balloons on a
noisy photo). Input: JPG / PNG / WEBP.

### Presets (`咒語強度`)

| Preset (key) | Label | Human-readable? | Stops strong AI (GPT/Claude)? |
|----|----|----|----|
| `Standard` | 標準 | yes, looks processed | not reliably |
| `Maximum` | 重度 | with effort | partly |
| `Extreme` (default) | 極限 | hard | yes — but humans struggle too |

**Honest limitation:** for clear text at readable size there is *no* setting that
is both comfortable for humans and reliably defeats modern multimodal models —
geometric flips don't stop them, and disruption strong enough to stop them also
hurts human reading. Re-screenshotting / re-compressing can also weaken it.

### Multi-image

Upload several images at once → each is processed and gets its own **numbered
one-tap download button** (no ZIP — saves straight as JPG). Originals are tucked
into a collapsed section so you can skip them.

### Title band (署名橫幅, optional)

Toggle on 署名橫幅 to stamp a parchment credit strip on top of every image with
**篇名 / 作者名稱 / 日期** (date defaults to *today in the viewer's own browser
timezone* via `st.context.timezone`, editable).
The band is drawn crisp and added *before* the flip, so it rides along and reads
upright once the viewer flips it back. Rendered with **Noto Sans CJK**, so it
works for both Traditional and Simplified Chinese. Applies to the whole batch.

## Run locally

```bash
cd ~/ai-ocr-protector
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/streamlit run app.py
```

## Deploy

- **App:** Streamlit Community Cloud → repo `surf0912/ai-ocr-protector`, branch
  `main`, file `app.py`. Auto-redeploys on push.
- **Shell:** GitHub Pages on `surf0912/ai-ocr-protector-mobile` (Settings → Pages).

## Theme & font (maintenance)

- **Background:** `assets/parchment.jpg` (a real paper photo, optimised to 1920px)
  is embedded as base64 in the CSS so it always loads same-origin.
- **Font:** `小豆`→ now **Yusei Magic**. The 6 MB source TTF
  (`assets/YuseiMagic-Regular-2.ttf`) is **subset to the glyphs the UI actually
  uses** → `assets/uifont.woff2` (~67 KB), embedded as base64. No external CDN.

Regenerate the subset after changing UI text (keeps file tiny + avoids missing
glyphs):

```bash
python - <<'PY'
import string; from pathlib import Path
chars = set(Path("app.py").read_text("utf-8")) | set(string.printable) | set("0123456789")
chars |= set("×·…—、。，！？：；「」（）『』〇±•‧σµ²³°'‘“”")
Path("/tmp/subset.txt").write_text("".join(sorted(chars)), "utf-8")
PY
pyftsubset assets/YuseiMagic-Regular-2.ttf --text-file=/tmp/subset.txt \
  --flavor=woff2 --output-file=assets/uifont.woff2 --layout-features='*' --desubroutinize
# fallback (粉圓) — covers Traditional glyphs Yusei Magic is missing (你/每/啟/…)
pyftsubset <jf-openhuninn.ttf> --text-file=/tmp/subset.txt \
  --flavor=woff2 --output-file=assets/uifont-fallback.woff2 --layout-features='*' --desubroutinize
```

> Yusei Magic is a Japanese font and lacks several common Traditional characters,
> so the CSS font stack is `'YuseiMagic', 'HuninnUI', serif`: Yusei for the glyphs
> it has, **粉圓 (`uifont-fallback.woff2`)** for the rest — no serif tofu.
> **Regenerate BOTH subsets whenever UI text changes.** Verify combined coverage
> with `fontTools` (every UI CJK char should be in one woff2 or the other).

- **Title-band font:** `assets/band-font.otf` (Noto Sans CJK, OFL) — used only
  server-side to draw the credit band, so its 16 MB never reaches the browser. It
  covers Traditional **and** Simplified, so author/title can be either.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI (parchment theme, font, controls, upload→download) |
| `processor.py` | Pure pipeline. `process_image()`, `protect_bytes()`, presets — Streamlit-free, reusable for an API |
| `assets/parchment.jpg` | Background texture (embedded) |
| `assets/uifont.woff2` | Subset Yusei Magic (embedded) |
| `assets/YuseiMagic-Regular-2.ttf` | UI font source (for re-subsetting only; not served) |
| `assets/band-font.otf` | Noto Sans CJK — draws the title band server-side (TC + SC) |
| `.streamlit/config.toml` | Upload limit + parchment theme colours |

## Reuse as a library

`processor.py` has no Streamlit dependency:

```python
from processor import protect_bytes, config_from_preset
protected = protect_bytes(raw_bytes, config_from_preset("Extreme"), "JPG")
```

## Performance

Warp and noise run in row-strips, so a 12 MP phone photo processes in ~1.5 s with
~700 MB peak RAM. `ProtectionConfig(seed=…)` makes output reproducible.

## Future ideas

ZIP download (currently per-image by design) · redact-only-sensitive-fields mode · PDF support · API endpoint.
