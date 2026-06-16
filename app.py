"""Streamlit UI for the Automated AI/OCR Protection Image Processor.

Flow:  Upload  ->  Process automatically  ->  Preview  ->  Download
The user only has to drop a file in and click download; everything in between
runs without manual editing. Controls are optional refinements.
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
    "Upload an image (usually a screenshot or text-heavy image). It is automatically "
    "transformed to be harder for OCR and multimodal AI to read or train on, while "
    "staying understandable to a human. No manual editing required."
)

SUPPORTED = ["jpg", "jpeg", "png", "webp"]


# --------------------------------------------------------------------------- #
# Cached processing so moving sliders is snappy
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _run(data: bytes, cfg_dict: dict, out_format: str) -> bytes:
    cfg = ProtectionConfig(**cfg_dict)
    img = Image.open(io.BytesIO(data))
    processed = process_image(img, cfg)
    return encode_image(processed, out_format)


# --------------------------------------------------------------------------- #
# Sidebar: protection settings
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Protection settings")

    preset_name = st.selectbox(
        "Preset", list(PRESETS.keys()), index=1,
        help="Light = subtle, Strong = most disruptive. Start with Medium.",
    )
    out_format = st.radio("Output format", ["PNG", "JPG"], horizontal=True)

    with st.expander("Advanced (optional)", expanded=False):
        st.caption("Override the preset. Defaults follow the chosen preset.")
        base = config_from_preset(preset_name)

        rotate_180 = st.checkbox("Rotate 180°", value=base.rotate_180)
        flip_horizontal = st.checkbox("Flip horizontally", value=base.flip_horizontal)

        st.markdown("**OCR-disruption mask**")
        mask_enabled = st.checkbox("Enable mask", value=base.mask_enabled)
        mask_opacity = st.slider(
            "Mask opacity", 0.05, 0.30, float(base.mask_opacity), 0.01
        )
        col_a, col_b = st.columns(2)
        with col_a:
            use_diagonal = st.checkbox("Diagonal", value=base.use_diagonal)
            use_grid = st.checkbox("Fine grid", value=base.use_grid)
        with col_b:
            use_crosshatch = st.checkbox("Cross-hatch", value=base.use_crosshatch)
        spacing = st.slider(
            "Line spacing (px)", 6, 30,
            (base.spacing_min, base.spacing_max),
        )
        line_width = st.slider(
            "Line width (px)", 1, 4, (base.line_width_min, base.line_width_max)
        )

        st.markdown("**Noise**")
        noise_enabled = st.checkbox("Enable Gaussian noise", value=base.noise_enabled)
        noise_sigma = st.slider("Noise intensity (σ)", 0.0, 30.0, float(base.noise_sigma), 0.5)

        st.markdown("**Blur (optional)**")
        blur_enabled = st.checkbox("Enable slight blur", value=base.blur_enabled)
        blur_radius = st.slider("Blur radius (px)", 0.0, 1.0, float(base.blur_radius), 0.1)

    # Build the effective config from the controls.
    cfg = ProtectionConfig(
        rotate_180=rotate_180,
        flip_horizontal=flip_horizontal,
        mask_enabled=mask_enabled,
        mask_opacity=mask_opacity,
        line_width_min=line_width[0],
        line_width_max=line_width[1],
        spacing_min=spacing[0],
        spacing_max=spacing[1],
        use_diagonal=use_diagonal,
        use_crosshatch=use_crosshatch,
        use_grid=use_grid,
        noise_enabled=noise_enabled,
        noise_sigma=noise_sigma,
        blur_enabled=blur_enabled,
        blur_radius=blur_radius,
    )


# --------------------------------------------------------------------------- #
# Main: upload -> auto-process -> preview -> download
# --------------------------------------------------------------------------- #
uploaded = st.file_uploader(
    "Upload an image", type=SUPPORTED, accept_multiple_files=False
)

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

with st.spinner("Processing automatically…"):
    result_bytes = _run(data, cfg.to_dict(), out_format)

left, right = st.columns(2)
with left:
    st.subheader("Original")
    st.image(data, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px · {original.format or uploaded.type}")
with right:
    st.subheader("Protected")
    st.image(result_bytes, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px · {out_format} · dimensions preserved")

ext = "jpg" if out_format == "JPG" else "png"
stem = uploaded.name.rsplit(".", 1)[0]
st.download_button(
    "⬇️ Download protected image",
    data=result_bytes,
    file_name=f"{stem}_protected.{ext}",
    mime="image/jpeg" if out_format == "JPG" else "image/png",
    type="primary",
)

with st.expander("How does this work / is it readable?"):
    st.markdown(
        """
- **Rotate 180° + flip horizontally** changes the geometry so models that expect
  upright, correctly-oriented text have to work harder; a human can still reorient it.
- **OCR-disruption mask** lays randomized diagonal, cross-hatch and fine-grid lines
  over the text. The randomization (jittered spacing, width, grey value and alpha)
  makes it hard to remove with a single notch/frequency filter.
- **Gaussian noise** breaks up the clean edges character recognition relies on.
- **Optional slight blur** softens glyph boundaries a touch more.

This *reduces* extraction accuracy rather than guaranteeing zero extraction.
Use the **Strong** preset for maximum disruption, **Light** if readability matters most.
        """
    )
