"""Unit tests for NovelAI MCP client and utilities."""

import asyncio
import base64
import io
import zipfile
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from PIL import Image

from novelai_mcp.client import NovelAIClient, NovelAIError
from novelai_mcp.models import SIZE_PRESET_MAP, CharacterPrompt
from novelai_mcp.utils import (
    extract_images_from_zip,
    image_to_base64,
    load_image,
    resolve_dimensions,
    save_image,
)


def create_dummy_png(width=64, height=64, color=(255, 0, 0)) -> bytes:
    """Create dummy PNG bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_dummy_zip(*pngs: bytes) -> bytes:
    """Create a zip archive containing png files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, png in enumerate(pngs):
            z.writestr(f"image_{i}.png", png)
    return buf.getvalue()


def ok_response(content: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=content, request=httpx.Request("POST", "https://x"))


def run_with_responses(coro_factory, responses: List[httpx.Response]):
    """Run a client call with httpx.AsyncClient.request mocked; return (result, mock)."""
    async def _run():
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = responses
            result = await coro_factory()
            return result, mock_req
    return asyncio.run(_run())


def sent_json(mock_req, call_index: int = -1) -> dict:
    return mock_req.call_args_list[call_index].kwargs["json"]


def decode_size(b64: str):
    return Image.open(io.BytesIO(base64.b64decode(b64))).size


def test_resolve_dimensions():
    assert resolve_dimensions("portrait") == SIZE_PRESET_MAP["portrait"]
    assert resolve_dimensions("landscape") == SIZE_PRESET_MAP["landscape"]
    # Explicit width/height win over the preset and round to the nearest multiple of 64.
    assert resolve_dimensions("portrait", 1000, 700) == (1024, 704)
    with pytest.raises(ValueError, match="Unknown size preset"):
        resolve_dimensions("huge")


def test_comic_presets():
    assert resolve_dimensions("comic_page") == (832, 1216)
    assert resolve_dimensions("comic_strip") == (1536, 640)
    assert resolve_dimensions("manga_page") == (832, 1216)


def test_zip_extraction():
    png = create_dummy_png()
    assert extract_images_from_zip(create_dummy_zip(png)) == [png]
    assert extract_images_from_zip(png) == [png]
    with pytest.raises(ValueError):
        extract_images_from_zip(b"not an image")


def test_load_image_and_base64(tmp_path):
    png = create_dummy_png(128, 128)
    file_path = tmp_path / "test.png"
    file_path.write_bytes(png)

    data, _, w, h = load_image(str(file_path))
    assert (w, h) == (128, 128)
    assert data == png

    _, _, w2, h2 = load_image(image_to_base64(data))
    assert (w2, h2) == (128, 128)

    with pytest.raises(ValueError, match="not found"):
        load_image(str(tmp_path / "missing.png"))


def test_save_image(tmp_path):
    saved = save_image(create_dummy_png(), output_dir=str(tmp_path), prefix="test")
    assert saved.endswith(".png")
    assert (tmp_path / saved).exists()


def test_save_image_default_dir_does_not_depend_on_cwd(tmp_path, monkeypatch):
    default_dir = tmp_path / "default"
    monkeypatch.delenv("NOVELAI_OUTPUT_DIR", raising=False)
    monkeypatch.setattr("novelai_mcp.utils.DEFAULT_OUTPUT_DIR", default_dir)
    monkeypatch.chdir(tmp_path)

    saved = save_image(create_dummy_png())
    assert Path(saved).parent == default_dir.resolve()


def test_headers_and_missing_api_key():
    assert NovelAIClient(api_key="test_token_12345")._get_headers()["Authorization"] == "Bearer test_token_12345"
    client = NovelAIClient(api_key=None)
    client.api_key = None
    with pytest.raises(NovelAIError, match="NovelAI API key is missing"):
        client._get_headers()


def test_error_response_raises_with_message():
    client = NovelAIClient(api_key="t")
    err = httpx.Response(402, json={"message": "Not enough Anlas"}, request=httpx.Request("POST", "https://x"))
    with pytest.raises(NovelAIError, match="402: Not enough Anlas"):
        run_with_responses(lambda: client.generate_image(prompt="x"), [err])


def test_character_captions_payload():
    client = NovelAIClient(api_key="test_token")
    chars = [
        CharacterPrompt(prompt="1girl, silver hair, knight armor", negative_prompt="blurry", position=(0.25, 0.5)),
        {"prompt": "1boy, black hair, mage robes", "position": (0.75, 0.5)},
    ]
    (images, _), mock_req = run_with_responses(
        lambda: client.generate_image(prompt="fantasy battle", characters=chars, cfg_rescale=0.3, dynamic_thresholding=True),
        [ok_response(create_dummy_zip(create_dummy_png()))],
    )
    assert len(images) == 1
    params = sent_json(mock_req)["parameters"]
    v4_prompt = params["v4_prompt"]
    assert v4_prompt["use_coords"] is True
    captions = v4_prompt["caption"]["char_captions"]
    assert captions[0] == {"char_caption": "1girl, silver hair, knight armor", "centers": [{"x": 0.25, "y": 0.5}]}
    assert captions[1] == {"char_caption": "1boy, black hair, mage robes", "centers": [{"x": 0.75, "y": 0.5}]}
    assert params["v4_negative_prompt"]["caption"]["char_captions"][0]["char_caption"] == "blurry"
    assert params["cfg_rescale"] == 0.3
    assert params["dynamic_thresholding"] is True


def test_too_many_characters_for_v4():
    client = NovelAIClient(api_key="t")
    chars = [{"prompt": f"char {i}"} for i in range(7)]
    with pytest.raises(NovelAIError, match="at most 6"):
        asyncio.run(client.generate_image(prompt="x", model="nai-diffusion-4-5-full", characters=chars))


def test_quality_and_uc_preset_applied_to_prompts():
    client = NovelAIClient(api_key="t")
    _, mock_req = run_with_responses(
        lambda: client.generate_image(prompt="1girl", negative_prompt="bad hands", uc_preset="light"),
        [ok_response(create_dummy_png())],
    )
    payload = sent_json(mock_req)
    params = payload["parameters"]
    assert params["v4_prompt"]["caption"]["base_caption"] == "1girl, very aesthetic, masterpiece, no text"
    neg = params["v4_negative_prompt"]["caption"]["base_caption"]
    assert neg.startswith("bad hands, lowres, artistic error")
    assert params["ucPreset"] == 1
    assert payload["action"] == "generate"


def test_render_text_removes_text_suppression():
    client = NovelAIClient(api_key="t")
    _, mock_req = run_with_responses(
        lambda: client.generate_image(prompt="coffee shop facade", render_text="CAFE VOLTA", negative_prompt="text, blurry"),
        [ok_response(create_dummy_zip(create_dummy_png()))],
    )
    payload = sent_json(mock_req)
    assert 'text: "CAFE VOLTA"' in payload["input"]
    assert "no text" not in payload["input"]
    neg = payload["parameters"]["v4_negative_prompt"]["caption"]["base_caption"]
    assert "text" not in [t.strip().lower() for t in neg.split(",")]


def test_transparent_sets_hint_and_prompt():
    client = NovelAIClient(api_key="t")
    _, mock_req = run_with_responses(
        lambda: client.generate_image(prompt="chibi girl", transparent=True, quality_toggle=False),
        [ok_response(create_dummy_png())],
    )
    payload = sent_json(mock_req)
    assert payload["input"] == "chibi girl, transparent background"
    assert payload["parameters"]["tag_hint_transparent_background"] is True
    assert "transparent" not in payload["parameters"]


def test_img2img_resizes_source_and_sets_action(tmp_path):
    src = tmp_path / "src.png"
    src.write_bytes(create_dummy_png(1000, 700))
    client = NovelAIClient(api_key="t")
    _, mock_req = run_with_responses(
        lambda: client.generate_image(prompt="x", size=None, width=1000, height=700, i2i_image=str(src), i2i_strength=0.4),
        [ok_response(create_dummy_png())],
    )
    payload = sent_json(mock_req)
    params = payload["parameters"]
    assert payload["action"] == "img2img"
    assert (params["width"], params["height"]) == (1024, 704)
    assert decode_size(params["image"]) == (1024, 704)
    assert params["strength"] == 0.4


def test_inpaint_uses_source_size_not_preset(tmp_path):
    src = tmp_path / "src.png"
    src.write_bytes(create_dummy_png(1216, 832))
    mask = tmp_path / "mask.png"
    mask.write_bytes(create_dummy_png(608, 416, color=(255, 255, 255)))

    from novelai_mcp import server
    client = NovelAIClient(api_key="t")

    async def _run():
        with patch.object(server, "get_client", return_value=client), \
             patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = ok_response(create_dummy_png(1216, 832))
            await server.novelai_inpaint(image_path=str(src), mask_path=str(mask), prompt="x", output_dir=str(tmp_path))
            return mock_req

    mock_req = asyncio.run(_run())
    payload = sent_json(mock_req)
    params = payload["parameters"]
    assert payload["action"] == "infill"
    assert (params["width"], params["height"]) == (1216, 832)
    assert decode_size(params["mask"]) == (1216, 832)
    assert params["add_original_image"] is True


def test_vibe_transfer_encodes_with_model():
    client = NovelAIClient(api_key="t")
    vibe_bytes = b"\x01\x02vibe"
    ref = image_to_base64(create_dummy_png())
    _, mock_req = run_with_responses(
        lambda: client.generate_image(prompt="x", model="nai-diffusion-4-5-full", vibe_reference=ref, vibe_strength=0.5, vibe_info_extracted=0.8),
        [ok_response(vibe_bytes, 201), ok_response(create_dummy_png())],
    )
    assert mock_req.call_args_list[0].args[1].endswith("/ai/encode-vibe")
    encode = sent_json(mock_req, 0)
    assert encode["model"] == "nai-diffusion-4-5-full"
    assert encode["information_extracted"] == 0.8
    params = sent_json(mock_req, 1)["parameters"]
    assert params["reference_image_multiple"] == [base64.b64encode(vibe_bytes).decode()]
    assert params["reference_strength_multiple"] == [0.5]
    assert params["reference_information_extracted_multiple"] == [0.8]


def test_augment_emotion_payload():
    client = NovelAIClient(api_key="t")
    ref = image_to_base64(create_dummy_png(96, 128))
    (images, meta), mock_req = run_with_responses(
        lambda: client.augment_image(ref, tool="emotion", emotion="smug", prompt="closed eyes", defry=2),
        [ok_response(create_dummy_zip(create_dummy_png(96, 128)), 201)],
    )
    payload = sent_json(mock_req)
    assert payload["req_type"] == "emotion"
    assert payload["prompt"] == "smug;;closed eyes"
    assert payload["defry"] == 2
    assert (payload["width"], payload["height"]) == (96, 128)
    assert len(images) == 1

    with pytest.raises(NovelAIError, match="Unknown emotion"):
        asyncio.run(client.augment_image(ref, tool="emotion", emotion="furious"))


def test_augment_bg_removal_returns_all_images():
    client = NovelAIClient(api_key="t")
    ref = image_to_base64(create_dummy_png())
    pngs = [create_dummy_png(color=c) for c in [(1, 1, 1), (2, 2, 2), (3, 3, 3)]]
    (images, _), mock_req = run_with_responses(
        lambda: client.augment_image(ref, tool="bg-removal"),
        [ok_response(create_dummy_zip(*pngs), 201)],
    )
    assert images == pngs
    assert "prompt" not in sent_json(mock_req)


def test_upscale_payload_matches_schema():
    client = NovelAIClient(api_key="t")
    ref = image_to_base64(create_dummy_png(64, 64))
    (_, meta), mock_req = run_with_responses(
        lambda: client.upscale(ref, model="nai-diffusion-4-5-full"),
        [ok_response(create_dummy_zip(create_dummy_png(256, 256)))],
    )
    assert set(sent_json(mock_req)) == {"image", "model"}
    assert (meta["target_width"], meta["target_height"]) == (256, 256)
