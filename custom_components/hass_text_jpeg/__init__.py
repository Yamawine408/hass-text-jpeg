from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_BACKGROUND, DEFAULT_COLOR, DEFAULT_HEIGHT, DEFAULT_FONT_SIZE,
    DEFAULT_QUALITY, DEFAULT_SPACING, DEFAULT_WIDTH, DOMAIN, FONT_DIR,
    OUTPUT_DIR, SERVICE_DRAW,
)
from .renderer import render_text_jpeg

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema({
    vol.Required("text"): cv.string,
    vol.Required("filename"): cv.string,
    vol.Optional("font", default=""): cv.string,
    vol.Optional("width", default=DEFAULT_WIDTH): vol.All(vol.Coerce(int), vol.Range(min=1, max=4096)),
    vol.Optional("height", default=DEFAULT_HEIGHT): vol.All(vol.Coerce(int), vol.Range(min=1, max=4096)),
    vol.Optional("font_size", default=DEFAULT_FONT_SIZE): vol.All(vol.Coerce(int), vol.Range(min=1, max=512)),
    vol.Optional("x", default=10): vol.Coerce(int),
    vol.Optional("y", default=10): vol.Coerce(int),
    vol.Optional("color", default=DEFAULT_COLOR): cv.string,
    vol.Optional("background", default=DEFAULT_BACKGROUND): cv.string,
    vol.Optional("quality", default=DEFAULT_QUALITY): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional("spacing", default=DEFAULT_SPACING): vol.All(vol.Coerce(int), vol.Range(min=0, max=256)),
})


def _resolve_font(font: str) -> str:
    path = Path(font).expanduser()
    return str(path if path.is_absolute() else Path(FONT_DIR) / path)


def _validate_filename(filename: str) -> str:
    if not filename or filename in {".", ".."}:
        raise ValueError("filename must be a simple filename")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("filename must not contain a directory")
    if Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("filename extension must be .jpg or .jpeg")
    return filename


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    async def handle_draw(call: ServiceCall) -> None:
        data = SERVICE_SCHEMA(dict(call.data))
        filename = _validate_filename(data["filename"])
        font_path = _resolve_font(data["font"])
        output_dir = Path(OUTPUT_DIR)
        output_path = output_dir / filename

        def _render() -> str:
            output_dir.mkdir(parents=True, exist_ok=True)
            return str(render_text_jpeg(
                text=data["text"], font_path=font_path, output_path=str(output_path),
                width=data["width"], height=data["height"], font_size=data["font_size"],
                x=data["x"], y=data["y"], color=data["color"],
                background=data["background"], quality=data["quality"],
                spacing=data["spacing"],
            ))

        try:
            saved = await hass.async_add_executor_job(_render)
        except Exception:
            _LOGGER.exception("Failed to create text JPEG")
            raise
        _LOGGER.info("Created text JPEG: %s", saved)

    hass.services.async_register(DOMAIN, SERVICE_DRAW, handle_draw, schema=SERVICE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_DRAW)
    return True
