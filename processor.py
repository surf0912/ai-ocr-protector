"""Core image-protection pipeline.

Pure, dependency-light functions so the same logic can power the Streamlit UI
today and a FastAPI endpoint later. The public entry point is `process_image`.

Pipeline (in order):
    1. Rotate 180 degrees
    2. Flip horizontally
    3. OCR-disruption mask (diagonal + cross-hatch + fine grid, randomized)
    4. Gaussian noise layer
    5. Optional very-slight blur

Every step preserves the original pixel dimensions.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class ProtectionConfig:
    """All knobs for the pipeline. Defaults = the 'Medium' preset."""

    # Geometry
    rotate_180: bool = True
    flip_horizontal: bool = True

    # OCR-disruption mask
    mask_enabled: bool = True
    mask_opacity: float = 0.15          # 0.10 - 0.20 per spec
    line_width_min: int = 1             # px
    line_width_max: int = 2             # px
    spacing_min: int = 10               # px
    spacing_max: int = 20               # px
    use_diagonal: bool = True
    use_crosshatch: bool = True
    use_grid: bool = True

    # Noise
    noise_enabled: bool = True
    noise_sigma: float = 8.0            # std-dev in 0-255 space; "light" by default

    # Blur (optional, off by default)
    blur_enabled: bool = False
    blur_radius: float = 0.4            # 0.3 - 0.5 per spec

    # Reproducibility (None = fresh randomness each run)
    seed: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Protection presets ---------------------------------------------------------
PRESETS: dict[str, dict] = {
    "Light": dict(
        mask_opacity=0.10,
        noise_sigma=4.0,
        blur_enabled=False,
        blur_radius=0.3,
        use_diagonal=True,
        use_crosshatch=False,
        use_grid=True,
    ),
    "Medium": dict(
        mask_opacity=0.15,
        noise_sigma=8.0,
        blur_enabled=True,
        blur_radius=0.4,
        use_diagonal=True,
        use_crosshatch=True,
        use_grid=True,
    ),
    "Strong": dict(
        mask_opacity=0.20,
        noise_sigma=14.0,
        blur_enabled=True,
        blur_radius=0.5,
        use_diagonal=True,
        use_crosshatch=True,
        use_grid=True,
    ),
}


def config_from_preset(name: str, **overrides) -> ProtectionConfig:
    """Build a config from a named preset, with optional field overrides."""
    base = PRESETS.get(name, {})
    return ProtectionConfig(**{**base, **overrides})


# --------------------------------------------------------------------------- #
# Individual pipeline steps
# --------------------------------------------------------------------------- #
def _rotate_180(img: Image.Image) -> Image.Image:
    return img.transpose(Image.ROTATE_180)


def _flip_horizontal(img: Image.Image) -> Image.Image:
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def _draw_line_set(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    rng: random.Random,
    orientation: str,
    cfg: ProtectionConfig,
    alpha: int,
) -> None:
    """Draw one family of evenly-ish-spaced lines with per-line jitter.

    `orientation` is one of: 'diag', 'anti', 'vert', 'horiz'.
    Jitter on position, width, alpha and grey value keeps the pattern from
    being a single uniform colour/frequency that a notch filter could remove.
    """
    w, h = size
    spacing = rng.randint(cfg.spacing_min, cfg.spacing_max)

    # Iterate a band wide enough to cover the whole canvas for diagonals.
    start = -h
    end = w + h
    c = start
    while c < end:
        jitter = rng.randint(-spacing // 3 or -1, spacing // 3 or 1)
        pos = c + jitter
        width = rng.randint(cfg.line_width_min, cfg.line_width_max)
        # Slightly vary grey + alpha per line.
        grey = rng.randint(40, 110)
        a = max(0, min(255, alpha + rng.randint(-20, 20)))
        colour = (grey, grey, grey, a)

        if orientation == "diag":          # slope +1
            draw.line([(pos, 0), (pos + h, h)], fill=colour, width=width)
        elif orientation == "anti":        # slope -1
            draw.line([(pos, 0), (pos - h, h)], fill=colour, width=width)
        elif orientation == "vert":
            if 0 <= pos <= w:
                draw.line([(pos, 0), (pos, h)], fill=colour, width=width)
        elif orientation == "horiz":
            if 0 <= pos <= h:
                draw.line([(0, pos), (w, pos)], fill=colour, width=width)
        c += spacing


def _build_mask_overlay(
    size: tuple[int, int], cfg: ProtectionConfig, rng: random.Random
) -> Image.Image:
    """Transparent RGBA overlay holding the disruption pattern."""
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = int(round(255 * cfg.mask_opacity))

    if cfg.use_diagonal:
        _draw_line_set(draw, size, rng, "diag", cfg, alpha)
    if cfg.use_crosshatch:
        _draw_line_set(draw, size, rng, "anti", cfg, alpha)
    if cfg.use_grid:
        # Finer spacing for the grid texture.
        grid_cfg = ProtectionConfig(
            **{**cfg.to_dict(),
               "spacing_min": max(6, cfg.spacing_min // 2),
               "spacing_max": max(8, cfg.spacing_max // 2)}
        )
        _draw_line_set(draw, size, rng, "vert", grid_cfg, alpha)
        _draw_line_set(draw, size, rng, "horiz", grid_cfg, alpha)

    return overlay


def _apply_mask(img: Image.Image, cfg: ProtectionConfig, rng: random.Random) -> Image.Image:
    overlay = _build_mask_overlay(img.size, cfg, rng)
    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay)


def _apply_noise(img: Image.Image, cfg: ProtectionConfig, rng: random.Random) -> Image.Image:
    """Add Gaussian noise to the RGB channels (alpha untouched)."""
    has_alpha = img.mode == "RGBA"
    rgb = img.convert("RGBA") if has_alpha else img.convert("RGB")
    arr = np.asarray(rgb).astype(np.float32)

    np_rng = np.random.default_rng(cfg.seed if cfg.seed is not None else None)
    channels = 3  # only perturb colour, keep alpha crisp
    noise = np_rng.normal(0.0, cfg.noise_sigma, size=(*arr.shape[:2], channels))
    arr[..., :3] = np.clip(arr[..., :3] + noise, 0, 255)

    return Image.fromarray(arr.astype(np.uint8), mode=rgb.mode)


def _apply_blur(img: Image.Image, cfg: ProtectionConfig) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=cfg.blur_radius))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def process_image(img: Image.Image, cfg: ProtectionConfig) -> Image.Image:
    """Run the full protection pipeline and return the processed image.

    Output dimensions always equal the input dimensions.
    """
    original_size = img.size

    # EXIF orientation is baked in so the geometry steps are predictable.
    img = _normalise_orientation(img)

    rng = random.Random(cfg.seed)

    if cfg.rotate_180:
        img = _rotate_180(img)
    if cfg.flip_horizontal:
        img = _flip_horizontal(img)
    if cfg.mask_enabled:
        img = _apply_mask(img, cfg, rng)
    if cfg.noise_enabled:
        img = _apply_noise(img, cfg, rng)
    if cfg.blur_enabled:
        img = _apply_blur(img, cfg)

    assert img.size == original_size, "pipeline must preserve dimensions"
    return img


def _normalise_orientation(img: Image.Image) -> Image.Image:
    """Apply any EXIF rotation, then drop EXIF so it isn't re-applied."""
    try:
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img


def encode_image(img: Image.Image, fmt: str = "PNG", jpg_quality: int = 90) -> bytes:
    """Serialise to bytes in the requested format ('PNG' or 'JPG'/'JPEG')."""
    fmt = fmt.upper()
    buf = io.BytesIO()
    if fmt in ("JPG", "JPEG"):
        # JPEG has no alpha channel — flatten onto white.
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=jpg_quality, optimize=True)
    else:
        img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def protect_bytes(
    data: bytes, cfg: ProtectionConfig, out_format: str = "PNG"
) -> bytes:
    """Convenience: bytes in -> protected bytes out (handy for an API layer)."""
    img = Image.open(io.BytesIO(data))
    processed = process_image(img, cfg)
    return encode_image(processed, out_format)
