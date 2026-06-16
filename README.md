# 🛡️ AI / OCR Protection Image Processor

A web tool that automatically processes an uploaded image to make it **harder for
OCR systems and multimodal AI to read or train on**, while keeping it reasonably
understandable to a human. Fully automatic — upload, then download. No manual
editing, drawing, or positioning.

Intended for protecting your own screenshots / text-heavy images from being
scraped and machine-extracted.

## Pipeline

Applied in order, always preserving the original pixel dimensions:

1. **Rotate 180°**
2. **Flip horizontally**
3. **OCR-disruption mask** — randomized diagonal lines, cross-hatching and a fine
   grid (opacity 10–20%, 1–2 px lines, 10–20 px spacing). Per-line jitter on
   position, width, grey value and alpha makes it hard to remove with a single
   filter.
4. **Gaussian noise** — light by default, intensity configurable.
5. **Optional slight blur** — radius 0.3–0.5 px, off by default.

Output: **PNG** or **JPG**, same dimensions as the input.
Input: **JPG / PNG / WEBP**.

## Run

```bash
cd ~/ai-ocr-protector
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/streamlit run app.py
```

Streamlit opens at <http://localhost:8501>. Drop in an image; it is processed
automatically. Pick a preset (**Light / Medium / Strong**), optionally tweak the
advanced sliders, then **Download protected image**.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI (upload → auto-process → preview → download) |
| `processor.py` | Pure pipeline. `process_image()`, `protect_bytes()`, presets — reusable for a future FastAPI endpoint |
| `requirements.txt` | Dependencies |

## Reuse as a library / future API

`processor.py` has no Streamlit dependency, so the same logic can back a FastAPI
endpoint later:

```python
from processor import protect_bytes, config_from_preset

protected_png = protect_bytes(raw_bytes, config_from_preset("Strong"), "PNG")
```

## Notes & limitations

- This **reduces** OCR/AI extraction accuracy — it does not guarantee zero
  extraction. Use the **Strong** preset for maximum disruption.
- The 180° + horizontal-flip step mirrors the image vertically. A human can
  reorient it; many automated pipelines assume upright text.
- Set `ProtectionConfig(seed=...)` for reproducible output (mask + noise).

## Future features (not yet built)

Custom watermark · batch processing · PDF support · ZIP download · API endpoint.
The processor is already structured to make these straightforward to add.
