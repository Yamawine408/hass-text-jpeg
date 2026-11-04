# Hass Text JPEG

Home Assistant custom integration for rendering one line of text to JPEG.

- FreeType `FT_LOAD_TARGET_NORMAL` rasterizes glyphs with grayscale antialiasing.
- Pillow is used for the canvas, mask compositing and JPEG encoding.
- Output directory: `/media`
- Default font directory: `/config/www/fonts`
- Single-line text only; no shapes, PNG output or transparency.

## Install

Copy `custom_components/hass_text_jpeg` into `/config/custom_components/`,
restart Home Assistant, then add **Hass Text JPEG** from Settings → Devices & services.

Put TTF/OTF fonts in `/config/www/fonts/`.

## Example service call

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
  y: 20
  color: "#ffffff"
  background: "#202020"
  quality: 95
```

The file is saved as `/media/alert.jpg`. `x` and `y` specify the top-left
of the font line box.
