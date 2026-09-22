# NovelAI MCP Server

[English version](README.md)

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
claude mcp add novelai -e NOVELAI_API_KEY=ваш_токен -- uvx novelai-mcp
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
      "args": ["novelai-mcp"],
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

Замените `"args": ["novelai-mcp"]` на:

```json
"args": ["--from", "git+https://github.com/DesmondFox/novelai-mcp", "novelai-mcp"]
```

## Настройки

| Переменная | Обязательна | По умолчанию | Что задаёт |
| :--- | :--- | :--- | :--- |
| `NOVELAI_API_KEY` | да | — | Persistent API Token. |
| `NOVELAI_OUTPUT_DIR` | нет | `~/Pictures/NovelAI` | Папка для изображений. Каждый инструмент также принимает `output_dir`. |

## Использование

Пишите модели обычным текстом, инструмент и параметры она выберет сама. Примеры:

- «Нарисуй портрет девушки с серебряными волосами и голубыми глазами в поле подсолнухов.»
- «Чиби кошкодевочка с кружкой кофе, прозрачный фон.»
- «Сцена в таверне: слева девушка-рыцарь, справа парень-маг.»
- «Киберпанк-витрина ночью с неоновой вывеской NEON DREAMS.»
- «Возьми `~/Pictures/NovelAI/t2i_20260101_120000_abc123.png` и смени эмоцию на smug.»
- «Убери фон с этой картинки и сделай апскейл.»
- «Подскажи теги для 'kimono'.»

Основные параметры `novelai_generate_image` описаны в [английском README](README.md#usage).

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
