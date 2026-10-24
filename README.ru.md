# NovelAI MCP Server

[English version](README.md) · [Українська версія](README.uk.md)

[MCP](https://modelcontextprotocol.io)-сервер, через который Claude, Cursor и другие MCP-клиенты генерируют и редактируют изображения в [NovelAI](https://novelai.net).

Поддерживает NovelAI Diffusion V5 (Full и Curated) и V4.5: text-to-image, img2img, inpainting, Director Tools, Vibe Transfer, апскейл и подсказки тегов.

> Неофициальный проект. Не связан с NovelAI / Anlatan.

## Инструменты

| Инструмент | Что делает |
| :--- | :--- |
| `novelai_generate_image` | Генерация по тексту. Пресеты размера или свой размер, несколько персонажей с позициями, текст на картинке, прозрачный фон, комикс-панели, режимы furry и background. |
| `novelai_img2img` | Перерисовка готового изображения по новому промпту. `strength` (0.0–1.0) задаёт силу изменений. |
| `novelai_inpaint` | Перерисовка области по маске. Белое в маске перерисовывается, чёрное остаётся. |
| `novelai_augment` | Director Tools: `bg-removal`, `lineart`, `sketch`, `colorize`, `emotion` (24 эмоции), `declutter`. |
| `novelai_upscale` | Нейросетевой апскейл. Коэффициент выбирает NovelAI. |
| `novelai_vibe_transfer` | Новое изображение в стиле и палитре референса. |
| `novelai_suggest_tags` | Автодополнение тегов Danbooru/NovelAI. |

Изображения сохраняются на диск и возвращаются клиенту, так что модель их видит.

## Что нужно

- Подписка NovelAI и **Persistent API Token**: NovelAI → Settings → Account → Persistent API Tokens.
- [uv](https://docs.astral.sh/uv/getting-started/installation/). Он запускает сервер без ручной установки.

## Стоимость

Запросы тратят Anlas так же, как сайт NovelAI. Большие размеры, больше steps, апскейл и Vibe Transfer стоят дороже. Сервер расход не ограничивает.

## Подключение

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

После правки перезапустите Claude Desktop.

### Cursor

Тот же блок `mcpServers` в `.cursor/mcp.json` или в Settings → MCP.

### Установка из GitHub вместо PyPI

Замените `"args": ["mcp-server-novelai"]` на:

```json
"args": ["--from", "git+https://github.com/DesmondFox/novelai-mcp", "mcp-server-novelai"]
```

## Настройки

| Переменная | Обязательна | По умолчанию | Что задаёт |
| :--- | :--- | :--- | :--- |
| `NOVELAI_API_KEY` | да | — | Persistent API Token. |
| `NOVELAI_OUTPUT_DIR` | нет | `~/Pictures/NovelAI` | Папка для изображений. Каждый инструмент также принимает `output_dir`. |
| `NOVELAI_DEFAULT_MODEL` | нет | `nai-diffusion-5-full` | `model` по умолчанию для `novelai_generate_image`. Укажите `nai-diffusion-5-full-medium`, чтобы тратить меньше. У остальных инструментов свои значения по умолчанию. |

## Использование

Пишите модели обычным текстом, инструмент и параметры она выберет сама. Примеры:

- «Нарисуй портрет девушки с серебряными волосами и голубыми глазами в поле подсолнухов.»
- «Чиби кошкодевочка с кружкой кофе, прозрачный фон.»
- «Сцена в таверне: слева девушка-рыцарь, справа парень-маг.»
- «Киберпанк-витрина ночью с неоновой вывеской NEON DREAMS.»
- «Возьми `~/Pictures/NovelAI/t2i_20260101_120000_abc123.png` и смени эмоцию на smug.»
- «Убери фон с этой картинки и сделай апскейл.»
- «Подскажи теги для 'kimono'.»

Полезные параметры `novelai_generate_image`:

| Параметр | По умолчанию | Примечание |
| :--- | :--- | :--- |
| `model` | `nai-diffusion-5-full` | Также `nai-diffusion-5-full-medium`, `nai-diffusion-5-curated`, `nai-diffusion-4-5-full`, `nai-diffusion-4-5-curated`. |
| `size` | `portrait` | `portrait` 832×1216, `landscape` 1216×832, `square` 1024×1024, `wallpaper` 1920×1088, `comic_strip` 1536×640 и другие. |
| `width`, `height` | — | Свой размер, округляется до кратного 64. Нужно задать оба. |
| `steps` | 23 | Как на сайте NovelAI. |
| `scale` | 5.0 | Сила следования промпту. |
| `seed` | случайный | Задайте, чтобы повторить изображение. Использованный seed возвращается в ответе. |
| `uc_preset` | `light` | `strong`, `light`, `furry_focus`, `human_focus`, `none`. |
| `characters` | — | Список `{"prompt": ..., "negative_prompt": ..., "position": [x, y]}`, x и y в диапазоне 0.0–1.0. До 22 на V5, до 6 на V4/V4.5. |
| `render_text` | — | Текст, который нужно нарисовать на изображении. |
| `transparent` | false | Прозрачный фон. |
| `comic_panels` | false | Добавляет теги комикс/манга-панелей. |

`nai-diffusion-5-full-medium` — V5 Full на уровне Medium effort: примерно на 40% дешевле при похожем качестве. NovelAI фиксирует для него настройки: 14 steps, `k_euler_ancestral`, UC preset `strong`, без `cfg_rescale`. Сервер выставляет их сам. Negative prompt не поддерживается и возвращает ошибку.

## Разработка

```bash
git clone https://github.com/DesmondFox/novelai-mcp
cd novelai-mcp
pip install -e ".[dev]"
pytest
ruff check .
```

Для локальной разработки ключ можно положить в `.env` (см. `.env.example`) вместо конфига клиента.

## Лицензия

[MIT](LICENSE)
