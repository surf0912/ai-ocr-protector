"""Streamlit UI for the AI / OCR Protection Image Processor (zh-Hant, mobile-first).

All controls live on the main page (no sidebar) so it's usable on a phone without
tapping the sidebar arrow. Flow: 設定 → 上傳 → 自動處理 → 下載 / 預覽.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import streamlit as st
from PIL import Image

from processor import (
    PRESETS,
    ProtectionConfig,
    config_from_preset,
    encode_image,
    process_image,
)

st.set_page_config(
    page_title="预言家日報・防窥工坊", page_icon="🪄",
    layout="centered", initial_sidebar_state="collapsed",
)

# Parchment background from a real paper texture (embedded as base64 so it always
# loads on Streamlit Cloud), plus custom "scroll card" notices.
@st.cache_data
def _parchment_data_uri() -> str:
    img = Path(__file__).parent / "assets" / "parchment.jpg"
    return "data:image/jpeg;base64," + base64.b64encode(img.read_bytes()).decode()


@st.cache_data
def _font_data_uri() -> str:
    f = Path(__file__).parent / "assets" / "uifont.woff2"
    return "data:font/woff2;base64," + base64.b64encode(f.read_bytes()).decode()


use_magic_font = st.toggle("使用魔法字體", value=True, help="關閉後會改用系統預設字體，閱讀性比較穩定。")

font_css = """
    @font-face {
        font-family: 'XiaoDou';
        src: url("__FONT__") format('woff2');
        font-display: swap;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
    h1, h2, h3, h4, h5, h6, p, label, button, input, textarea, select,
    .stButton button, [data-testid="stWidgetLabel"], .scroll-note,
    div[data-baseweb="select"], div[data-baseweb="select"] *,
    div[data-baseweb="popover"], div[data-baseweb="popover"] *,
    div[role="listbox"], div[role="listbox"] *,
    div[role="option"], div[role="option"] *,
    ul[data-testid="stVirtualDropdown"], ul[data-testid="stVirtualDropdown"] *,
    li[data-testid="stVirtualDropdownOption"], li[data-testid="stVirtualDropdownOption"] * {
        font-family: 'XiaoDou', serif !important;
    }
""" if use_magic_font else """
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
    h1, h2, h3, h4, h5, h6, p, label, button, input, textarea, select,
    .stButton button, [data-testid="stWidgetLabel"], .scroll-note,
    div[data-baseweb="select"], div[data-baseweb="select"] *,
    div[data-baseweb="popover"], div[data-baseweb="popover"] *,
    div[role="listbox"], div[role="listbox"] *,
    div[role="option"], div[role="option"] *,
    ul[data-testid="stVirtualDropdown"], ul[data-testid="stVirtualDropdown"] *,
    li[data-testid="stVirtualDropdownOption"], li[data-testid="stVirtualDropdownOption"] * {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif !important;
    }
"""


st.markdown(
    """
    <style>
    .stApp {
        background-color: #EFE2C4;
        background-image:
            linear-gradient(rgba(244,234,208,0.30), rgba(244,234,208,0.30)),
            url("__BG__");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
    [data-testid="stHeader"] { background: transparent; }
    __FONT_CSS__
    [data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
    .material-icons-rounded {
        font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
    }
    .scroll-note {
        background-color: rgba(233,216,174,0.90);
        border: 1px solid #C2A867;
        border-left: 5px solid #7B2D26;
        border-radius: 6px;
        padding: 0.85rem 1.05rem;
        margin-bottom: 0.6rem;
        color: #3A2A17;
        line-height: 1.75;
    }
    .scroll-note .scroll-title { font-weight: 700; margin-bottom: 0.35rem; }
    .scroll-note.warn { border-left-color: #9A6B1F; background-color: rgba(236,221,176,0.90); }
    </style>
    """.replace("__BG__", _parchment_data_uri()).replace("__FONT_CSS__", font_css).replace("__FONT__", _font_data_uri()),
    unsafe_allow_html=True,
)

st.title("🪄 预言家日報・防窥工坊")

st.markdown(
    '<div class="scroll-note">'
    '<div class="scroll-title">📜 施咒須知</div>'
    '・請獻上「正向的原始卷軸」，施咒後將呈顛倒鏡像之貌。<br>'
    '・切勿將已施咒的卷軸重複投入，咒語會相互抵銷、護法盡失。'
    '</div>',
    unsafe_allow_html=True,
)

SUPPORTED = ["jpg", "jpeg", "png", "webp"]

PRESET_LABELS = {
    "Standard": "标准",
    "Maximum": "重度",
    "Extreme": "极限",
}


@st.cache_data(show_spinner=False)
def _run(data: bytes, cfg_dict: dict, jpg_quality: int) -> bytes:
    cfg = ProtectionConfig(**cfg_dict)
    img = Image.open(io.BytesIO(data))
    processed = process_image(img, cfg)
    return encode_image(processed, "JPG", jpg_quality)


# --------------------------------------------------------------------------- #
# Controls — all on the main page (mobile friendly)
# --------------------------------------------------------------------------- #
preset_name = st.selectbox(
    "咒語強度", list(PRESETS.keys()), index=len(PRESETS) - 1,  # 預設「極限」
    format_func=lambda k: PRESET_LABELS.get(k, k),
)

flip_output = st.checkbox("施展顛倒咒（旋轉+鏡像）", value=True)

with st.expander("進階魔法"):
    base = config_from_preset(preset_name)

    jpg_quality = st.slider("JPG 品質", 60, 100, 92, 1,
                            help="數字越低檔案越小；92 是不錯的平衡。")

    st.markdown("**微形變 (Micro-warp)** — 打散字形，抗 AI 的關鍵之一")
    warp_enabled = st.checkbox("啟用微形變", value=base.warp_enabled)
    warp_amplitude = st.slider("形變強度 (px)", 0.0, 15.0, float(base.warp_amplitude), 0.5,
                               help="越大越能干擾，但扭曲越明顯。")

    st.markdown("**干擾遮罩** — 對 AI 最有效，但看得見")
    mask_enabled = st.checkbox("啟用遮罩", value=base.mask_enabled)
    mask_opacity = st.slider("遮罩不透明度", 0.03, 0.40, float(base.mask_opacity), 0.01)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        use_diagonal = st.checkbox("斜線", value=base.use_diagonal)
    with col_b:
        use_crosshatch = st.checkbox("交叉斜線", value=base.use_crosshatch)
    with col_c:
        use_grid = st.checkbox("細格網", value=base.use_grid)
    spacing = st.slider("線距 (px @1000px)", 6, 30, (base.spacing_min, base.spacing_max))
    line_width = st.slider("線寬 (px)", 1, 4, (base.line_width_min, base.line_width_max))

    st.markdown("**雜訊 / 模糊**")
    noise_enabled = st.checkbox("啟用高斯雜訊", value=base.noise_enabled)
    noise_sigma = st.slider("雜訊強度 (σ)", 0.0, 20.0, float(base.noise_sigma), 0.5)
    blur_enabled = st.checkbox("輕微模糊（會降低可讀性）", value=base.blur_enabled)
    blur_radius = st.slider("模糊半徑 (px)", 0.0, 1.0, float(base.blur_radius), 0.1)

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
    rotate_180=flip_output,
    flip_horizontal=flip_output,
    blur_enabled=blur_enabled,
    blur_radius=blur_radius,
)


# --------------------------------------------------------------------------- #
# Upload -> auto-process -> download -> preview
# --------------------------------------------------------------------------- #
uploaded = st.file_uploader("獻上你的卷軸", type=SUPPORTED, accept_multiple_files=False)

if uploaded is None:
    st.markdown(
        '<div class="scroll-note">⬆️ 上傳 JPG、PNG 或 WEBP，上傳後會自動處理。</div>',
        unsafe_allow_html=True,
    )
    st.stop()

data = uploaded.getvalue()

try:
    original = Image.open(io.BytesIO(data))
    original.load()
except Exception as exc:  # noqa: BLE001
    st.error(f"無法讀取這張圖片：{exc}")
    st.stop()

megapixels = (original.width * original.height) / 1_000_000
if megapixels > 24:
    st.warning(f"圖片較大({megapixels:.0f} MP)——處理可能需要幾秒。")

with st.spinner("揮舞魔杖中…"):
    result_bytes = _run(data, cfg.to_dict(), jpg_quality)

stem = uploaded.name.rsplit(".", 1)[0]
st.download_button(
    "速速前！取回卷軸(Accio)",
    data=result_bytes,
    file_name=f"{stem}_protected.jpg",
    mime="image/jpeg",
    type="primary",
    use_container_width=True,
)

st.subheader("施咒後")
if flip_output:
    st.markdown(
        '<div class="scroll-note warn">⚠️ 下圖是<b>顛倒+鏡像</b>的，這是正常的。'
        '閱讀時把圖<b>上下翻轉（垂直翻轉）</b>即可完全還原。</div>',
        unsafe_allow_html=True,
    )
st.image(result_bytes, use_container_width=True)
st.caption(f"{original.width} × {original.height}px · JPG · "
           f"{len(result_bytes) / 1_000_000:.1f} MB · 尺寸已保留")

with st.expander("窺看原貌"):
    st.image(data, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px · "
               f"{original.format or uploaded.type} · {len(data) / 1_000_000:.1f} MB")
