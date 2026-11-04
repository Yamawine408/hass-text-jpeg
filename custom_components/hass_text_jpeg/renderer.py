from __future__ import annotations

from pathlib import Path

import freetype
from PIL import Image


def _parse_color(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ValueError("Color must be #RRGGBB")
    value = value.strip()
    if len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"Invalid color: {value}. Expected #RRGGBB")
    try:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError as err:
        raise ValueError(f"Invalid color: {value}. Expected #RRGGBB") from err


def _glyph_mask(bitmap) -> Image.Image:
    width, rows, pitch = bitmap.width, bitmap.rows, bitmap.pitch
    if width == 0 or rows == 0:
        return Image.new("L", (width, rows), 0)

    raw = bytes(bitmap.buffer)  # Copy: FreeType reuses its glyph slot.
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_GRAY:
        if pitch == width:
            return Image.frombytes("L", (width, rows), raw)
        return Image.frombytes("L", (width, rows), raw, "raw", "L", pitch, 1)

    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_MONO:
        result = Image.new("L", (width, rows), 0)
        pixels = result.load()
        for row in range(rows):
            offset = row * pitch
            for col in range(width):
                if raw[offset + col // 8] & (0x80 >> (col % 8)):
                    pixels[col, row] = 255
        return result

    raise ValueError(f"Unsupported FreeType pixel mode: {bitmap.pixel_mode}")


def render_text_jpeg(
    *, text: str, font_path: str, output_path: str, width: int, height: int,
    font_size: int, x: int, y: int, color: str, background: str,
    quality: int, spacing: int = 0,
) -> Path:
    """Render one line using FreeType NORMAL grayscale antialiasing."""
    if not text:
        raise ValueError("text must not be empty")
    if "\n" in text or "\r" in text:
        raise ValueError("Only single-line text is supported")
    if width < 1 or height < 1 or font_size < 1:
        raise ValueError("width, height and font_size must be positive")
    if not 1 <= quality <= 100 or spacing < 0:
        raise ValueError("quality must be 1..100 and spacing must be >= 0")

    font_file = Path(font_path)
    if not font_file.is_file():
        raise FileNotFoundError(f"Font file not found: {font_file}")

    face = freetype.Face(str(font_file))
    face.set_pixel_sizes(0, font_size)
    flags = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL

    canvas = Image.new("RGB", (width, height), _parse_color(background))
    ink = Image.new("RGB", (width, height), _parse_color(color))
    mask = Image.new("L", (width, height), 0)

    # x/y specifies the top-left of the font line box.
    baseline = y + (face.size.ascender >> 6)
    pen_x = x
    previous_index = 0

    for i, char in enumerate(text):
        glyph_index = face.get_char_index(ord(char))
        if previous_index and glyph_index and face.has_kerning:
            kern = face.get_kerning(previous_index, glyph_index, freetype.FT_KERNING_DEFAULT)
            pen_x += kern.x >> 6

        face.load_char(ord(char), flags)
        slot = face.glyph
        glyph = _glyph_mask(slot.bitmap)
        left = pen_x + slot.bitmap_left
        top = baseline - slot.bitmap_top
        if glyph.width and glyph.height:
            mask.paste(glyph, (left, top))

        pen_x += slot.advance.x >> 6
        if i != len(text) - 1:
            pen_x += spacing
        previous_index = glyph_index

    canvas.paste(ink, (0, 0), mask)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="JPEG", quality=quality, subsampling=0, optimize=True)
    return destination
