# NovelAI MCP Server

[![CI](https://github.com/DesmondFox/novelai-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/DesmondFox/novelai-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Русская версия](README.ru.md)

An [MCP](https://modelcontextprotocol.io) server that lets Claude, Cursor and other MCP clients generate and edit images with [NovelAI](https://novelai.net).

Supports NovelAI Diffusion V5 (Full and Curated) and V4.5: text-to-image, img2img, inpainting, Director Tools, Vibe Transfer, upscaling and tag suggestions.

> This is an unofficial project. It is not affiliated with or endorsed by NovelAI / Anlatan.

## Tools

| Tool | What it does |
| :--- | :--- |
| `novelai_generate_image` | Text-to-image. Size presets or custom size, multi-character prompts with positions, in-image text, transparent background, comic panels, furry and background modes. |
| `novelai_img2img` | Redraws an existing image from a new prompt. `strength` (0.0–1.0) controls how much changes. |
| `novelai_inpaint` | Redraws the masked area of an image. White in the mask = repaint, black = keep. |
| `novelai_augment` | Director Tools: `bg-removal`, `lineart`, `sketch`, `colorize`, `emotion` (24 emotions), `declutter`. |
| `novelai_upscale` | Neural upscale. NovelAI chooses the factor. |
| `novelai_vibe_transfer` | Generates a new image in the style and palette of a reference image. |
| `novelai_suggest_tags` | Danbooru/NovelAI tag autocomplete. |

Generated images are saved to disk and also returned to the client, so the model can see them.

## Requirements

- A NovelAI subscription and a **Persistent API Token**: NovelAI → Settings → Account → Persistent API Tokens.
- [uv](https://docs.astral.sh/uv/getting-started/installation/). It runs the server without a manual install.

## Cost

Requests spend your Anlas the same way the NovelAI website does. Large sizes, more steps, upscale and Vibe Transfer cost more. Check your Anlas balance before running many generations. The server does not limit spending.

## Setup

### Claude Code

```bash
claude mcp add novelai -e NOVELAI_API_KEY=your_token -- uvx novelai-mcp
```

### Claude Desktop

Edit `claude_desktop_config.json`:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "novelai": {
      "command": "uvx",
      "args": ["novelai-mcp"],
      "env": {
        "NOVELAI_API_KEY": "your_token"
      }
    }
  }
}
```

Restart Claude Desktop after editing.

### Cursor

Add the same `mcpServers` block to `.cursor/mcp.json` or to Settings → MCP.

### Install from GitHub instead of PyPI

Replace `"args": ["novelai-mcp"]` with:

```json
"args": ["--from", "git+https://github.com/DesmondFox/novelai-mcp", "novelai-mcp"]
```

## Configuration

| Variable | Required | Default | Meaning |
| :--- | :--- | :--- | :--- |
| `NOVELAI_API_KEY` | yes | — | Persistent API Token. |
| `NOVELAI_OUTPUT_DIR` | no | `~/Pictures/NovelAI` | Where images are saved. Each tool also accepts `output_dir`. |

## Usage

Ask the model in plain language. It picks the tool and parameters. Examples:

- "Generate a portrait of a girl with silver hair and blue eyes in a sunflower field."
- "Make a chibi cat girl holding a coffee mug, transparent background."
- "Draw a tavern scene: a knight girl on the left, a mage boy on the right."
- "Cyberpunk storefront at night with a neon sign that says NEON DREAMS."
- "Take `~/Pictures/NovelAI/t2i_20260101_120000_abc123.png` and change her expression to smug."
- "Remove the background from that image, then upscale it."
- "Suggest tags for 'kimono'."

Useful parameters of `novelai_generate_image`:

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `model` | `nai-diffusion-5-full` | Also `nai-diffusion-5-curated`, `nai-diffusion-4-5-full`, `nai-diffusion-4-5-curated`. |
| `size` | `portrait` | `portrait` 832×1216, `landscape` 1216×832, `square` 1024×1024, `wallpaper` 1920×1088, `comic_strip` 1536×640, and others. |
| `width`, `height` | — | Custom size, rounded to a multiple of 64. Both must be set. |
| `steps` | 23 | Same default as the NovelAI website. |
| `scale` | 5.0 | Prompt guidance. |
| `seed` | random | Set it to reproduce an image. The used seed is returned. |
| `uc_preset` | `light` | `strong`, `light`, `furry_focus`, `human_focus`, `none`. |
| `characters` | — | List of `{"prompt": ..., "negative_prompt": ..., "position": [x, y]}`, x and y in 0.0–1.0. Up to 22 on V5, 6 on V4/V4.5. |
| `render_text` | — | Text to draw inside the image. |
| `transparent` | false | Transparent background. |
| `comic_panels` | false | Adds comic/manga panel tags. |

## Development

```bash
git clone https://github.com/DesmondFox/novelai-mcp
cd novelai-mcp
pip install -e ".[dev]"
pytest
ruff check .
```

For local development you can put the key in a `.env` file (see `.env.example`) instead of the client config.

## License

[MIT](LICENSE)
