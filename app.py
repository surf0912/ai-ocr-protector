"""Streamlit UI for the AI / OCR Protection Image Processor.

Flow:  Upload  ->  Process automatically  ->  Preview  ->  Download
Goal: confuse AI / OCR while keeping the image readable to humans. The default
("Stealth") is tuned for near-zero human-visible impact. You only have to upload
and download; the controls are optional.
"""

from __future__ import annotations

import io

import streamlit as st
from PIL import Image

from processor import (
    PRESETS,
    ProtectionConfig,
    config_from_preset,
    encode_image,
    process_image,
)

st.set_page_config(page_title="AI / OCR Protection Processor", page_icon="🛡️", layout="wide")

st.title("🛡️ AI / OCR Protection Image Processor")
st.caption(
    "Upload an image. It is automatically processed to be harder for OCR and "
    "multimodal AI to read or train on, while staying readable to a human. "
    "Works with any image size. No manual editing required."
)

SUPPORTED = ["jpg", "jpeg", "png", "webp"]


@st.cache_data(show_spinner=False)
def _run(data: bytes, cfg_dict: dict, out_format: str, jpg_quality: int) -> bytes:
    cfg = ProtectionConfig(**cfg_dict)
    img = Image.open(io.BytesIO(data))
    processed = process_image(img, cfg)
    return encode_image(processed, out_format, jpg_quality)


# --------------------------------------------------------------------------- #
# Sidebar: protection settings
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Protection settings")

    preset_name = st.selectbox(
        "Preset", list(PRESETS.keys()), index=0,
        help="Stealth = practically invisible to the eye. Maximum = most "
             "disruptive but you can tell it was processed.",
    )
    out_format = st.radio(
        "Output format", ["JPG", "PNG"], horizontal=True,
        help="JPG is best for photos. PNG is lossless but, because of the noise "
             "layer, becomes very large (often 5–10× the original).",
    )
    if out_format == "JPG":
        jpg_quality = st.slider("JPG quality", 60, 100, 92, 1,
                                help="Lower = smaller file. 92 is a good balance.")
    else:
        jpg_quality = 92
        st.caption("⚠️ PNG of a noisy photo can be much larger than the original. "
                   "Use JPG for photos.")

    with st.expander("Advanced (optional)", expanded=False):
        st.caption("Override the preset. Defaults follow the chosen preset.")
        base = config_from_preset(preset_name)

        st.markdown("**Micro-warp** — low human impact, main anti-OCR effect")
        warp_enabled = st.checkbox("Enable micro-warp", value=base.warp_enabled)
        warp_amplitude = st.slider(
            "Warp strength (px)", 0.0, 6.0, float(base.warp_amplitude), 0.1,
            help="Higher = more OCR disruption but more visible distortion.",
        )

        st.markdown("**Noise**")
        noise_enabled = st.checkbox("Enable Gaussian noise", value=base.noise_enabled)
        noise_sigma = st.slider("Noise intensity (σ)", 0.0, 20.0, float(base.noise_sigma), 0.5)

        st.markdown("**Disruption overlay** — visible; off for max readability")
        mask_enabled = st.checkbox("Enable overlay mask", value=base.mask_enabled)
        mask_opacity = st.slider("Mask opacity", 0.03, 0.25, float(base.mask_opacity), 0.01)
        col_a, col_b = st.columns(2)
        with col_a:
            use_diagonal = st.checkbox("Diagonal", value=base.use_diagonal)
            use_grid = st.checkbox("Fine grid", value=base.use_grid)
        with col_b:
            use_crosshatch = st.checkbox("Cross-hatch", value=base.use_crosshatch)
        spacing = st.slider("Line spacing (px @1000px)", 6, 30,
                            (base.spacing_min, base.spacing_max))
        line_width = st.slider("Line width (px)", 1, 4,
                               (base.line_width_min, base.line_width_max))

        st.markdown("**High human-impact options** (off by default)")
        st.caption("⚠️ These noticeably affect human reading — use only if needed.")
        rotate_180 = st.checkbox("Rotate 180°", value=base.rotate_180)
        flip_horizontal = st.checkbox("Flip horizontally", value=base.flip_horizontal)
        blur_enabled = st.checkbox("Slight blur", value=base.blur_enabled)
        blur_radius = st.slider("Blur radius (px)", 0.0, 1.0, float(base.blur_radius), 0.1)

    cfg = ProtectionConfig(
        warp_enabled=warp_enabled,
        warp_amplitude=warp_amplitude,
        warp_cell=base.warp_cell,
        noise_enabled=noise_enabled,
        noise_sigma=noise_sigma,
        mask_enabled=mask_enabled,
        mask_opacity=mask_opacity,
        line_width_min=line_width[0],
        line_width_max=line_width[1],
        spacing_min=spacing[0],
        spacing_max=spacing[1],
        use_diagonal=use_diagonal,
        use_crosshatch=use_crosshatch,
        use_grid=use_grid,
        rotate_180=rotate_180,
        flip_horizontal=flip_horizontal,
        blur_enabled=blur_enabled,
        blur_radius=blur_radius,
    )


# --------------------------------------------------------------------------- #
# Main: upload -> auto-process -> preview -> download
# --------------------------------------------------------------------------- #
uploaded = st.file_uploader("Upload an image", type=SUPPORTED, accept_multiple_files=False)

if uploaded is None:
    st.info("⬆️ Upload a JPG, PNG, or WEBP to begin. Processing starts automatically.")
    st.stop()

data = uploaded.getvalue()

try:
    original = Image.open(io.BytesIO(data))
    original.load()
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not read that image: {exc}")
    st.stop()

megapixels = (original.width * original.height) / 1_000_000
if megapixels > 24:
    st.warning(f"Large image ({megapixels:.0f} MP) — processing may take a few seconds.")

with st.spinner("Processing automatically…"):
    result_bytes = _run(data, cfg.to_dict(), out_format, jpg_quality)

left, right = st.columns(2)
with left:
    st.subheader("Original")
    st.image(data, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px · {original.format or uploaded.type} "
               f"· {len(data) / 1_000_000:.1f} MB")
with right:
    st.subheader("Protected")
    st.image(result_bytes, use_container_width=True)
    out_mb = len(result_bytes) / 1_000_000
    note = ""
    if out_format == "PNG" and len(result_bytes) > 2 * len(data):
        note = " — try JPG for a much smaller file"
    st.caption(f"{original.width} × {original.height}px · {out_format} · {out_mb:.1f} MB"
               f" · dimensions preserved{note}")

ext = "jpg" if out_format == "JPG" else "png"
stem = uploaded.name.rsplit(".", 1)[0]
st.download_button(
    "⬇️ Download protected image",
    data=result_bytes,
    file_name=f"{stem}_protected.{ext}",
    mime="image/jpeg" if out_format == "JPG" else "image/png",
    type="primary",
)

with st.expander("How it works & honest limitations"):
    st.markdown(
        """
**Default (Stealth) — tuned for near-zero human-visible impact:**
- **Micro-warp**: a smooth 1–2px displacement field gently distorts glyph
  geometry. OCR character recognition and image embeddings degrade; the eye
  barely notices because overall shapes are preserved.
- **Light noise**: low-amplitude Gaussian noise disturbs the clean edges OCR
  relies on.

**Stronger presets** add a faint line overlay (and you can enable rotate/flip/blur
manually), trading some human readability for more disruption.

**Honest limitation:** no transform is both invisible to humans *and* able to
reliably defeat modern robust multimodal models. Subtle perturbations can also be
weakened by re-screenshotting or re-compressing the protected image. Use **Maximum**
when you need the strongest effect and can accept that it looks processed.
        """
    )
