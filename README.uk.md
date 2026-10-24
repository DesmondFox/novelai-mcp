# NovelAI MCP Server

[English version](README.md) · [Русская версия](README.ru.md)

[MCP](https://modelcontextprotocol.io)-сервер, через який Claude, Cursor та інші MCP-клієнти генерують і редагують зображення в [NovelAI](https://novelai.net).

Підтримує NovelAI Diffusion V5 (Full і Curated) та V4.5: text-to-image, img2img, inpainting, Director Tools, Vibe Transfer, апскейл і підказки тегів.

> Неофіційний проєкт. Не пов'язаний з NovelAI / Anlatan і не схвалений ними.

## Інструменти

| Інструмент | Що робить |
| :--- | :--- |
| `novelai_generate_image` | Генерація за текстом. Пресети розміру або власний розмір, кілька персонажів із позиціями, текст на зображенні, прозорий фон, комікс-панелі, режими furry і background. |
| `novelai_img2img` | Перемальовує наявне зображення за новим промптом. `strength` (0.0–1.0) задає силу змін. |
| `novelai_inpaint` | Перемальовує область за маскою. Біле в масці перемальовується, чорне лишається. |
| `novelai_augment` | Director Tools: `bg-removal`, `lineart`, `sketch`, `colorize`, `emotion` (24 емоції), `declutter`. |
| `novelai_upscale` | Нейромережевий апскейл. Коефіцієнт обирає NovelAI. |
| `novelai_vibe_transfer` | Нове зображення в стилі та палітрі референсу. |
| `novelai_suggest_tags` | Автодоповнення тегів Danbooru/NovelAI. |

Зображення зберігаються на диск і повертаються клієнту, тож модель їх бачить.

## Що потрібно

- Підписка NovelAI і **Persistent API Token**: NovelAI → Settings → Account → Persistent API Tokens.
- [uv](https://docs.astral.sh/uv/getting-started/installation/). Він запускає сервер без ручного встановлення.

## Вартість

Запити витрачають Anlas так само, як сайт NovelAI. Великі розміри, більше steps, апскейл і Vibe Transfer коштують дорожче. Перевірте баланс Anlas перед великою кількістю генерацій. Сервер витрати не обмежує.

## Підключення

### Claude Code

```bash
claude mcp add novelai -e NOVELAI_API_KEY=ваш_токен -- uvx mcp-server-novelai
```

### Claude Desktop

Файл `claude_desktop_config.json`:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "novelai": {
      "command": "uvx",
      "args": ["mcp-server-novelai"],
      "env": {
        "NOVELAI_API_KEY": "ваш_токен"
      }
    }
  }
}
```

Після зміни перезапустіть Claude Desktop.

### Cursor

Той самий блок `mcpServers` у `.cursor/mcp.json` або в Settings → MCP.

### Встановлення з GitHub замість PyPI

Замініть `"args": ["mcp-server-novelai"]` на:

```json
"args": ["--from", "git+https://github.com/DesmondFox/novelai-mcp", "mcp-server-novelai"]
```

## Налаштування

| Змінна | Обов'язкова | За замовчуванням | Що задає |
| :--- | :--- | :--- | :--- |
| `NOVELAI_API_KEY` | так | — | Persistent API Token. |
| `NOVELAI_OUTPUT_DIR` | ні | `~/Pictures/NovelAI` | Тека для зображень. Кожен інструмент також приймає `output_dir`. |

## Використання

Пишіть моделі звичайним текстом, інструмент і параметри вона обере сама. Приклади:

- «Намалюй портрет дівчини зі срібним волоссям і блакитними очима в полі соняшників.»
- «Чібі дівчина-кішка з горнятком кави, прозорий фон.»
- «Сцена в таверні: ліворуч дівчина-лицар, праворуч хлопець-маг.»
- «Кіберпанк-вітрина вночі з неоновою вивіскою NEON DREAMS.»
- «Візьми `~/Pictures/NovelAI/t2i_20260101_120000_abc123.png` і зміни емоцію на smug.»
- «Прибери фон із цього зображення і зроби апскейл.»
- «Підкажи теги для 'kimono'.»

Корисні параметри `novelai_generate_image`:

| Параметр | За замовчуванням | Примітка |
| :--- | :--- | :--- |
| `model` | `nai-diffusion-5-full` | Також `nai-diffusion-5-curated`, `nai-diffusion-4-5-full`, `nai-diffusion-4-5-curated`. |
| `size` | `portrait` | `portrait` 832×1216, `landscape` 1216×832, `square` 1024×1024, `wallpaper` 1920×1088, `comic_strip` 1536×640 та інші. |
| `width`, `height` | — | Власний розмір, округлюється до кратного 64. Потрібно задати обидва. |
| `steps` | 23 | Як на сайті NovelAI. |
| `scale` | 5.0 | Сила дотримання промпту. |
| `seed` | випадковий | Задайте, щоб повторити зображення. Використаний seed повертається у відповіді. |
| `uc_preset` | `light` | `strong`, `light`, `furry_focus`, `human_focus`, `none`. |
| `characters` | — | Список `{"prompt": ..., "negative_prompt": ..., "position": [x, y]}`, x і y в діапазоні 0.0–1.0. До 22 на V5, до 6 на V4/V4.5. |
| `render_text` | — | Текст, який треба намалювати на зображенні. |
| `transparent` | false | Прозорий фон. |
| `comic_panels` | false | Додає теги комікс/манга-панелей. |

## Розробка

```bash
git clone https://github.com/DesmondFox/novelai-mcp
cd novelai-mcp
pip install -e ".[dev]"
pytest
ruff check .
```

Для локальної розробки ключ можна покласти в `.env` (див. `.env.example`) замість конфігу клієнта.

## Ліцензія

[MIT](LICENSE)
