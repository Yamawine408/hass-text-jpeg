# Hass Text JPEG

Home Assistant custom integration for rendering one line of text to JPEG.

- FreeType `FT_LOAD_TARGET_NORMAL` rasterizes glyphs with grayscale antialiasing.
- Pillow is used for the canvas, mask compositing and JPEG encoding.
- Output: `/media`
- Default font directory: `/config/www/fonts`
- Single-line text only; no shapes, PNG or transparency.

## Install

Copy `custom_components/hass_text_jpeg` into `/config/custom_components/`,
restart Home Assistant, then add **Hass Text JPEG** from Settings → Devices & services.

Place TTF/OTF font files in `/config/www/fonts/`.

## Example

```yaml
action: hass_text_jpeg.draw
data:
  text: "緊急地震速報 深度5"
  filename: "alert.jpg"
  font: "NotoSansJP-Regular.ttf"
  width: 800
  height: 300
  font_size: 64
  x: 20
  pos_y: 20
  color: white
  background: "#202020"
  quality: 95
```

The file is saved as `/media/alert.jpg`. `pos_x` and `pos_y` specify the
top-left of the font line box. `pos_y` is used instead of `y` to avoid
YAML parsers that interpret an unquoted `y` as a boolean key.

## Error handling

Expected problems (missing/invalid font, invalid color, invalid text,
and output write failures) are returned as readable Home Assistant service
errors. Unexpected failures are logged with a traceback.
\nColor values accept Pillow color names such as `white`, `black`, `red`, and `navy`, as well as hex values.\n