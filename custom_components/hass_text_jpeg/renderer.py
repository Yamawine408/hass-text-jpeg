from __future__ import annotations

from pathlib import Path

import freetype
from PIL import Image, ImageColor


class TextJpegError(Exception):
    """Base class for expected text-to-JPEG errors."""


class FontNotFoundError(TextJpegError):
    """The requested font file does not exist."""


class InvalidFontError(TextJpegError):
    """FreeType could not load the requested font."""


class InvalidColorError(TextJpegError):
    """A color value is not in #RRGGBB format."""


class OutputFileError(TextJpegError):
    """The JPEG could not be written."""


def _parse_color(value: str) -> tuple[int, int, int]:
    """Accept Pillow color names and color strings such as #RRGGBB."""
    if not isinstance(value, str):
        raise InvalidColorError("Color must be a color name or color string")
    try:
        return ImageColor.getrgb(value.strip())[:3]
    except (ValueError, TypeError) as err:
        raise InvalidColorError(
            f"Unknown color '{value}'. Use a recognized color name or color value."
        ) from err


def _glyph_mask(bitmap) -> Image.Image:
    width, rows, pitch = bitmap.width, bitmap.rows, bitmap.pitch
    if width == 0 or rows == 0:
        return Image.new("L", (width, rows), 0)

    # Copy immediately because FreeType reuses its glyph slot on the next load.
    raw = bytes(bitmap.buffer)

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

    raise TextJpegError(
        f"Unsupported FreeType bitmap pixel mode: {bitmap.pixel_mode}"
    )


def render_text_jpeg(
    *,
    text: str,
    font_path: str,
    output_path: str,
    width: int,
    height: int,
    font_size: int,
    x: int,
    y: int,
    color: str,
    background: str,
    quality: int,
    spacing: int = 0,
) -> Path:
    """Render one line using FreeType NORMAL grayscale antialiasing."""
    if not text:
        raise TextJpegError("text must not be empty")
    if "\n" in text or "\r" in text:
        raise TextJpegError("Only single-line text is supported")
    if width < 1 or height < 1 or font_size < 1:
        raise TextJpegError("width, height and font_size must be positive")
    if not 1 <= quality <= 100:
        raise TextJpegError("quality must be between 1 and 100")
    if spacing < 0:
        raise TextJpegError("spacing must be zero or greater")

    font_file = Path(font_path)
    if not font_file.is_file():
        raise FontNotFoundError(f"Font file not found: {font_file}")

    try:
        face = freetype.Face(str(font_file))
        face.set_pixel_sizes(0, font_size)
    except Exception as err:
        raise InvalidFontError(
            f"Cannot load font file '{font_file}': {err}"
        ) from err

    flags = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL

    try:
        canvas = Image.new("RGB", (width, height), _parse_color(background))
        ink = Image.new("RGB", (width, height), _parse_color(color))
        mask = Image.new("L", (width, height), 0)

        # x/y specify the top-left of the font line box.
        baseline = y + (face.size.ascender >> 6)
        pen_x = x
        previous_index = 0

        for index, char in enumerate(text):
            glyph_index = face.get_char_index(ord(char))
            if previous_index and glyph_index and face.has_kerning:
                kerning = face.get_kerning(
                    previous_index, glyph_index, freetype.FT_KERNING_DEFAULT
                )
                pen_x += kerning.x >> 6

            face.load_char(ord(char), flags)
            slot = face.glyph
            glyph = _glyph_mask(slot.bitmap)

            glyph_left = pen_x + slot.bitmap_left
            glyph_top = baseline - slot.bitmap_top
            if glyph.width and glyph.height:
                mask.paste(glyph, (glyph_left, glyph_top))

            pen_x += slot.advance.x >> 6
            if index != len(text) - 1:
                pen_x += spacing
            previous_index = glyph_index

        canvas.paste(ink, (0, 0), mask)

    except (InvalidColorError, TextJpegError):
        raise
    except Exception as err:
        raise TextJpegError(f"Text rendering failed: {err}") from err

    destination = Path(output_path)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(
            destination,
            format="JPEG",
            quality=quality,
            subsampling=0,
            optimize=True,
        )
    except OSError as err:
        raise OutputFileError(
            f"Cannot write JPEG file '{destination}': {err}"
        ) from err
    except Exception as err:
        raise OutputFileError(
            f"Failed to encode JPEG file '{destination}': {err}"
        ) from err

    return destination
