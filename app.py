"""Streamlit UI for the AI / OCR Protection Image Processor (zh-Hant interface).

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

st.set_page_config(page_title="AI／OCR 圖片保護工具", page_icon="🛡️", layout="wide")

st.title("🛡️ AI／OCR 圖片保護工具")
st.caption(
    "上傳圖片,系統會自動處理,讓 OCR 與多模態 AI 更難讀取或拿去訓練,"
    "同時盡量維持人眼可讀。支援任意尺寸,免手動編輯。"
)

SUPPORTED = ["jpg", "jpeg", "png", "webp"]

# Preset keys stay English (used by processor); only the labels are translated.
PRESET_LABELS = {
    "Stealth": "隱形(預設・人眼幾乎無感)",
    "Balanced": "平衡",
    "Maximum": "最強(較有效・看得出處理過)",
}


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
    st.header("保護設定")

    preset_name = st.selectbox(
        "保護強度", list(PRESETS.keys()), index=0,
        format_func=lambda k: PRESET_LABELS.get(k, k),
        help="隱形＝肉眼幾乎看不出來;最強＝最能干擾 AI,但看得出處理過。",
    )
    # Always JPG: PNG of a noisy photo balloons to 5-10x the original.
    out_format = "JPG"

    with st.expander("進階設定(可選)", expanded=False):
        st.caption("可覆寫預設值。預設值會跟著上面選的強度走。")
        base = config_from_preset(preset_name)

        jpg_quality = st.slider("JPG 品質", 60, 100, 92, 1,
                                help="數字越低檔案越小;92 是不錯的平衡。")

        st.markdown("**微形變 (Micro-warp)** — 對人眼影響小,主要的抗 OCR 效果")
        warp_enabled = st.checkbox("啟用微形變", value=base.warp_enabled)
        warp_amplitude = st.slider(
            "形變強度 (px)", 0.0, 6.0, float(base.warp_amplitude), 0.1,
            help="越大越能干擾 OCR,但扭曲也越明顯。",
        )

        st.markdown("**雜訊 (Noise)**")
        noise_enabled = st.checkbox("啟用高斯雜訊", value=base.noise_enabled)
        noise_sigma = st.slider("雜訊強度 (σ)", 0.0, 20.0, float(base.noise_sigma), 0.5)

        st.markdown("**干擾遮罩** — 看得見;追求最高可讀性請關閉")
        mask_enabled = st.checkbox("啟用遮罩", value=base.mask_enabled)
        mask_opacity = st.slider("遮罩不透明度", 0.03, 0.25, float(base.mask_opacity), 0.01)
        col_a, col_b = st.columns(2)
        with col_a:
            use_diagonal = st.checkbox("斜線", value=base.use_diagonal)
            use_grid = st.checkbox("細格網", value=base.use_grid)
        with col_b:
            use_crosshatch = st.checkbox("交叉斜線", value=base.use_crosshatch)
        spacing = st.slider("線距 (px @1000px)", 6, 30,
                            (base.spacing_min, base.spacing_max))
        line_width = st.slider("線寬 (px)", 1, 4,
                               (base.line_width_min, base.line_width_max))

        st.markdown("**高人眼影響選項**(預設關閉)")
        st.caption("⚠️ 這些會明顯影響人眼閱讀,非必要請勿開啟。")
        rotate_180 = st.checkbox("旋轉 180°", value=base.rotate_180)
        flip_horizontal = st.checkbox("水平翻轉", value=base.flip_horizontal)
        blur_enabled = st.checkbox("輕微模糊", value=base.blur_enabled)
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
        rotate_180=rotate_180,
        flip_horizontal=flip_horizontal,
        blur_enabled=blur_enabled,
        blur_radius=blur_radius,
    )


# --------------------------------------------------------------------------- #
# Main: upload -> auto-process -> preview -> download
# --------------------------------------------------------------------------- #
uploaded = st.file_uploader("上傳圖片", type=SUPPORTED, accept_multiple_files=False)

if uploaded is None:
    st.info("⬆️ 上傳 JPG、PNG 或 WEBP 開始。上傳後會自動處理。")
    st.stop()

data = uploaded.getvalue()

try:
    original = Image.open(io.BytesIO(data))
    original.load()
except Exception as exc:  # noqa: BLE001
    st.error(f"無法讀取這張圖片:{exc}")
    st.stop()

megapixels = (original.width * original.height) / 1_000_000
if megapixels > 24:
    st.warning(f"圖片較大({megapixels:.0f} MP)——處理可能需要幾秒。")

with st.spinner("自動處理中…"):
    result_bytes = _run(data, cfg.to_dict(), out_format, jpg_quality)

left, right = st.columns(2)
with left:
    st.subheader("原圖")
    st.image(data, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px · {original.format or uploaded.type} "
               f"· {len(data) / 1_000_000:.1f} MB")
with right:
    st.subheader("保護後")
    st.image(result_bytes, use_container_width=True)
    out_mb = len(result_bytes) / 1_000_000
    st.caption(f"{original.width} × {original.height}px · JPG · {out_mb:.1f} MB · 尺寸已保留")

ext = "jpg" if out_format == "JPG" else "png"
stem = uploaded.name.rsplit(".", 1)[0]
st.download_button(
    "⬇️ 下載保護後的圖片",
    data=result_bytes,
    file_name=f"{stem}_protected.{ext}",
    mime="image/jpeg" if out_format == "JPG" else "image/png",
    type="primary",
)

with st.expander("運作原理與誠實的限制"):
    st.markdown(
        """
**預設(隱形)——調校成對人眼幾乎無感:**
- **微形變**:以平滑的 1–2px 位移輕微扭曲字形幾何。OCR 的字元辨識與影像
  embedding 會變差,但因整體輪廓保留,肉眼幾乎察覺不到。
- **輕微雜訊**:低強度高斯雜訊,干擾 OCR 依賴的乾淨邊緣。

**更強的預設**會再加上淡淡的線條遮罩(也可手動開啟旋轉／翻轉／模糊),
用部分人眼可讀性換取更強的干擾。

**誠實的限制:**沒有任何處理能「對人眼隱形」又「可靠擋住現代強大的多模態
模型」。輕微的擾動也可能因為重新截圖或重新壓縮而被削弱。需要最強效果、
且能接受看得出處理痕跡時,請用「最強」。
        """
    )
