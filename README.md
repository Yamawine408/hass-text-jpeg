# hass_text_jpeg

A Home Assistant custom integration that renders text as JPEG images.

Generated images are saved under Home Assistant's `/media`
directory. The integration is intended for use cases such as
displaying Home Assistant text or status information on ESPHome- or
ESP32-based devices.

## Motivation

This integration was developed to diplay Japanese text on an ESP32
display which has small memory to hold entire Japanese font set, by
converting text to image file. This can also be used for 
languages other than English, or displaying text with a preferred
font. 

## Features

- Render text as JPEG image.
- Wrap text if needed. 
- Support explicit line breaks using newline (`\n`).
- Support left, center, and right alignment.
- Enable or disable automatic wrapping.
- Configure the font, text color, background color, character spacing, and JPEG quality.
- Include **Noto Sans CJK JP Regular** (Google font) as the default font. The bundled font is used when no font is specified.

## Service

The integration registers the following service:

```yaml
hass_text_jpeg.draw
```

### Minimal example

```yaml
action: hass_text_jpeg.draw
data:
  text: "Hello, world!"
  filename: greeting.jpg
```

This creates `/media/greeting.jpg` using the default settings.

### Example with options

```yaml
action: hass_text_jpeg.draw
data:
  text: |-
    Living Room
    Temperature: 24.5 C
    Humidity: 48 %
  filename: room_status.jpg
  width: 400
  height: 160
  font_size: 32
  pos_x: 10
  pos_y: 10
  align: left
  wrap: true
  color: "#202020"
  background: "#ffffff"
  quality: 95
  spacing: 0
```

## Service fields

| Field | Required | Default | Description |
|---|---:|---:|---|
| `text` | Yes | — | Text to render. Explicit line breaks are supported. |
| `filename` | Yes | — | JPEG filename to save under `/media`. Directory paths are not allowed. |
| `font` | No | Bundled Noto Sans CJK JP | Font file to use. If omitted, the bundled font is used. Relative paths are resolved from `/config/www/fonts`. |
| `width` | No | `400` | Image width in pixels (1–4096). |
| `height` | No | `240` | Image height in pixels (1–4096). |
| `font_size` | No | `32` | Font size in pixels (1–512). |
| `pos_x` | No | `10` | Left edge of the text layout area, in pixels. |
| `pos_y` | No | `10` | Top edge of the first line, in pixels. |
| `align` | No | `left` | Horizontal alignment: `left`, `center`, or `right`. |
| `wrap` | No | `true` | Enable or disable automatic text wrapping. |
| `color` | No | `#000000` | Text color. |
| `background` | No | `#ffffff` | Background color. |
| `quality` | No | `95` | JPEG quality (1–100). |
| `spacing` | No | `0` | Character spacing in pixels (0–256). |

## Text layout

### Automatic wrapping

When `wrap: true`, text is wrapped within the available horizontal area from `pos_x` to the right edge of the image.

- Japanese text and paragraphs without whitespace are wrapped character by character.
- English and other whitespace-separated text are wrapped at word boundaries.
- If a single word is wider than the available area, that word is wrapped character by character.
- Explicit line breaks in the input are preserved.

This is normal word wrapping, not hyphenation. No hyphens are inserted into words.

### Alignment

The `align` option controls the alignment of each line within the area from `pos_x` to the right edge of the image.

- `left`: Align to the left.
- `center`: Center the line.
- `right`: Align to the right.

### Clipping

Text that extends beyond the right or bottom edge of the image is clipped to the image boundaries. It does not cause an overflow error.

When `wrap: false`, automatic wrapping is disabled. Explicit line breaks are still honored.

## Fonts

If `font` is omitted, the integration uses the bundled font:

```text
fonts/NotoSansCJK-Regular.ttc
```

To use another font, specify its path:

```yaml
font: "MyFont.ttf"
```

Relative paths are resolved from `/config/www/fonts`. Absolute paths are also accepted.

See `fonts/OFL-LICENSE.txt` for the bundled font's license.

## Output

Images are always saved under `/media`. Specify only a filename in `filename`; directory paths are not accepted. The filename must have a `.jpg` or `.jpeg` extension.

JPEG encoding uses Pillow. The `quality` option controls JPEG quality, and images are currently saved with `subsampling=0` (4:4:4).

## Requirements

The runtime environment requires the Python packages used by the integration:

- Pillow
- freetype-py
- Home Assistant

Installation of these dependencies and Home Assistant version requirements should be defined according to the integration's distribution method and target environment.

## Installation

1. Copy the `hass_text_jpeg` directory into Home Assistant's custom integrations directory:

   ```text
   <config>/
   └── custom_components/
       └── hass_text_jpeg/
           ├── __init__.py
           ├── const.py
           ├── renderer.py
           ├── services.yaml
           └── fonts/
               ├── NotoSansCJK-Regular.ttc
               └── OFL-LICENSE.txt
   ```

2. Restart Home Assistant.
3. Confirm that `hass_text_jpeg.draw` is available in the service list.
4. Call the service and check that the JPEG is created under `/media`.

> Note: This README describes the files and behavior covered by this integration package. Additional files required by the final distribution, such as `manifest.json`, should be provided as appropriate for the complete integration package.

## License

- `hass_text_jpeg` source code: subject to the license specified separately by this repository.
- Bundled font: distributed under the SIL Open Font License. See `fonts/OFL-LICENSE.txt` for details.
