# 🛡️ AI / OCR Protection Image Processor

A web tool that automatically processes an uploaded image to make it **harder for
OCR and multimodal AI to read or train on, while keeping it readable to a human**.
Fully automatic — upload, then download. Works with any image size.

Intended for protecting your own images from being scraped and machine-extracted.

## Approach (revised for "fool AI, not humans")

The default is tuned for **near-zero human-visible impact**:

1. **Micro-warp** — a smooth 1–2px displacement field gently distorts glyph
   geometry. OCR character recognition and image embeddings degrade, while the eye
   barely notices because overall shapes are preserved. This is the main effect.
2. **Light Gaussian noise** — low-amplitude noise disturbs the clean edges OCR
   relies on.

Stronger presets additionally add a faint line overlay, and the high-impact
options from the original spec (**rotate 180°, horizontal flip, blur**) are still
available as **manual, off-by-default** toggles.

All parameters **scale with image size**, so varying photo dimensions are handled
consistently. Every step **preserves the original pixel dimensions**.

| Preset | Human-visible impact | Use when |
|--------|---------------------|----------|
| **Stealth** (default) | practically none | you don't want to affect reading at all |
| **Balanced** | slight texture if you look | a bit more disruption is OK |
| **Maximum** | clearly processed, still readable | you need the strongest effect |

Input: **JPG / PNG / WEBP**.  Output: **PNG** or **JPG**, same dimensions.

## Honest limitation

No transform is both invisible to humans *and* able to reliably defeat modern
robust multimodal models. Subtle perturbations can also be weakened by
re-screenshotting or re-compressing the protected image. This **reduces**
extraction quality and training usefulness; it is not a guarantee.

## Run locally

```bash
cd ~/ai-ocr-protector
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/streamlit run app.py
```

Opens at <http://localhost:8501>. Drop in an image; it processes automatically.
Pick a preset, optionally tweak the advanced sliders, then **Download**.

## Deploy (so phone / friends abroad can use it)

Hosted free on **Streamlit Community Cloud**:

1. Push this repo to GitHub (public).
2. Go to <https://share.streamlit.io> → sign in with GitHub → **New app**.
3. Pick the repo, branch `main`, main file `app.py` → **Deploy**.
4. You get a permanent HTTPS URL like `https://<name>.streamlit.app` that works on
   mobile and anywhere.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI (upload → auto-process → preview → download) |
| `processor.py` | Pure pipeline. `process_image()`, `protect_bytes()`, presets — reusable for a future FastAPI endpoint |
| `requirements.txt` | Dependencies |
| `.streamlit/config.toml` | Upload size limit + theme |

## Reuse as a library / future API

`processor.py` has no Streamlit dependency:

```python
from processor import protect_bytes, config_from_preset

protected = protect_bytes(raw_bytes, config_from_preset("Stealth"), "JPG")
```

## Performance / memory

Warp and noise run in row-strips, so a 12MP phone photo processes in ~1.5s with a
peak of ~700MB RAM — safe on free hosting. `ProtectionConfig(seed=...)` makes
output reproducible.

## Future features (not yet built)

Custom watermark · batch processing · PDF support · ZIP download · API endpoint.
The processor is already structured to make these straightforward to add.
