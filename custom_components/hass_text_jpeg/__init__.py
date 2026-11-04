from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_BACKGROUND,
    DEFAULT_COLOR,
    DEFAULT_HEIGHT,
    DEFAULT_FONT_SIZE,
    DEFAULT_QUALITY,
    DEFAULT_SPACING,
    DEFAULT_WIDTH,
    DOMAIN,
    FONT_DIR,
    OUTPUT_DIR,
    SERVICE_DRAW,
)
from .renderer import (
    FontNotFoundError,
    InvalidColorError,
    InvalidFontError,
    OutputFileError,
    TextJpegError,
    render_text_jpeg,
)

_LOGGER = logging.getLogger(__name__)

# Use pos_y instead of "y": some YAML parsers interpret an unquoted y as
# a boolean key. The renderer still receives it as its internal y argument.
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Required("filename"): cv.string,
        vol.Optional("font", default=""): cv.string,
        vol.Optional("width", default=DEFAULT_WIDTH): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=4096)
        ),
        vol.Optional("height", default=DEFAULT_HEIGHT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=4096)
        ),
        vol.Optional("font_size", default=DEFAULT_FONT_SIZE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=512)
        ),
        vol.Optional("x", default=10): vol.Coerce(int),
        vol.Optional("pos_y", default=10): vol.Coerce(int),
        vol.Optional("color", default=DEFAULT_COLOR): cv.string,
        vol.Optional("background", default=DEFAULT_BACKGROUND): cv.string,
        vol.Optional("quality", default=DEFAULT_QUALITY): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional("spacing", default=DEFAULT_SPACING): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=256)
        ),
    }
)


def _resolve_font(font: str) -> Path:
    font_path = Path(font).expanduser()
    if not font_path.is_absolute():
        font_path = Path(FONT_DIR) / font_path
    return font_path


def _validate_filename(filename: str) -> str:
    if not filename or filename in {".", ".."}:
        raise HomeAssistantError("filename must be a simple filename")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise HomeAssistantError("filename must not contain a directory")
    if Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise HomeAssistantError("filename extension must be .jpg or .jpeg")
    return filename


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    async def handle_draw(call: ServiceCall) -> None:
        # ServiceCall.data is a ReadOnlyDict. Copy it before applying defaults.
        try:
            data = SERVICE_SCHEMA(dict(call.data))
        except vol.Invalid as err:
            raise HomeAssistantError(f"Invalid service data: {err}") from err

        filename = _validate_filename(data["filename"])
        font_path = _resolve_font(data["font"])
        output_path = Path(OUTPUT_DIR) / filename

        # Validate the font before creating the output directory or canvas.
        if not font_path.is_file():
            raise HomeAssistantError(f"Font file not found: {font_path}")

        def _render() -> str:
            return str(
                render_text_jpeg(
                    text=data["text"],
                    font_path=str(font_path),
                    output_path=str(output_path),
                    width=data["width"],
                    height=data["height"],
                    font_size=data["font_size"],
                    x=data["x"],
                    y=data["pos_y"],
                    color=data["color"],
                    background=data["background"],
                    quality=data["quality"],
                    spacing=data["spacing"],
                )
            )

        try:
            saved_path = await hass.async_add_executor_job(_render)
        except (FontNotFoundError, InvalidFontError, InvalidColorError, OutputFileError, TextJpegError) as err:
            # Expected input/rendering problems: show a useful service error,
            # without dumping a traceback into the HA log.
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            # Unexpected programming/runtime failures still get a traceback.
            _LOGGER.exception("Unexpected error while creating text JPEG")
            raise HomeAssistantError(
                f"Unexpected error while creating JPEG: {err}"
            ) from err

        _LOGGER.info("Created text JPEG: %s", saved_path)

    hass.services.async_register(
        DOMAIN, SERVICE_DRAW, handle_draw, schema=SERVICE_SCHEMA
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_DRAW)
    return True
