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


def _measure_text(face: freetype.Face, text: str, flags: int, spacing: int) -> int:
    """Measure a line using the same advances and kerning as the renderer."""
    pen_x = 0
    previous_index = 0
    for index, char in enumerate(text):
        glyph_index = face.get_char_index(ord(char))
        if previous_index and glyph_index and face.has_kerning:
            kerning = face.get_kerning(
                previous_index, glyph_index, freetype.FT_KERNING_DEFAULT
            )
            pen_x += kerning.x >> 6
        face.load_char(ord(char), flags)
        pen_x += face.glyph.advance.x >> 6
        if index != len(text) - 1:
            pen_x += spacing
        previous_index = glyph_index
    return pen_x


def _wrap_characterwise(
    face: freetype.Face, text: str, max_width: int, flags: int, spacing: int
) -> list[str]:
    """Wrap a long unbroken run, including a single overlong English word."""
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and _measure_text(face, candidate, flags, spacing) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current or not lines:
        lines.append(current)
    return lines


def _wrap_paragraph(
    face: freetype.Face, paragraph: str, max_width: int, flags: int, spacing: int
) -> list[str]:
    if not paragraph:
        return [""]

    # Japanese text normally has no spaces: wrap at character boundaries.
    # For space-separated text, keep words intact where possible.
    if not any(char.isspace() for char in paragraph):
        return _wrap_characterwise(face, paragraph, max_width, flags, spacing)

    words = paragraph.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _measure_text(face, candidate, flags, spacing) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""

        if _measure_text(face, word, flags, spacing) <= max_width:
            current = word
        else:
            pieces = _wrap_characterwise(face, word, max_width, flags, spacing)
            lines.extend(pieces[:-1])
            current = pieces[-1]

    if current or not lines:
        lines.append(current)
    return lines


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
    align: str = "left",
    wrap: bool = True,
) -> Path:
    """Render wrapped or single-line text with FreeType antialiasing.

    Text that extends beyond the image bounds is clipped by the image canvas.
    """
    if not text:
        raise TextJpegError("text must not be empty")
    if width < 1 or height < 1 or font_size < 1:
        raise TextJpegError("width, height and font_size must be positive")
    if not 1 <= quality <= 100:
        raise TextJpegError("quality must be between 1 and 100")
    if spacing < 0:
        raise TextJpegError("spacing must be zero or greater")
    if align not in {"left", "center", "right"}:
        raise TextJpegError("align must be left, center or right")

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

        available_width = max(1, width - x)
        paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        lines: list[str] = []
        for paragraph in paragraphs:
            if wrap:
                lines.extend(
                    _wrap_paragraph(face, paragraph, available_width, flags, spacing)
                )
            else:
                lines.append(paragraph)

        line_height = max(1, face.size.height >> 6)
        ascender = face.size.ascender >> 6

        for line_index, line in enumerate(lines):
            line_width = _measure_text(face, line, flags, spacing)
            if align == "center":
                line_x = x + max(0, (available_width - line_width) // 2)
            elif align == "right":
                line_x = x + max(0, available_width - line_width)
            else:
                line_x = x

            baseline = y + line_index * line_height + ascender
            pen_x = line_x
            previous_index = 0

            for index, char in enumerate(line):
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
                    # PIL clips glyphs outside the canvas; excess text is cropped.
                    mask.paste(glyph, (glyph_left, glyph_top))

                pen_x += slot.advance.x >> 6
                if index != len(line) - 1:
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
