"""Test server tools registration and execution."""

import asyncio

import pytest

from novelai_mcp.server import server


def test_server_tools_registered():
    """Check that all 7 expected tools are registered on the MCPServer."""
    expected_tools = {
        "novelai_generate_image",
        "novelai_img2img",
        "novelai_inpaint",
        "novelai_augment",
        "novelai_upscale",
        "novelai_vibe_transfer",
        "novelai_suggest_tags",
    }
    tools = asyncio.run(server.list_tools())
    registered = {tool.name for tool in tools}
    assert expected_tools.issubset(registered), f"Missing tools: {expected_tools - registered}"


def test_tool_signatures():
    """Verify parameters of key tools."""
    tools_list = asyncio.run(server.list_tools())
    tools = {t.name: t for t in tools_list}

    gen_tool = tools["novelai_generate_image"]
    assert "prompt" in gen_tool.input_schema.get("properties", {})
    assert "model" in gen_tool.input_schema.get("properties", {})
    assert "transparent" in gen_tool.input_schema.get("properties", {})

    aug_tool = tools["novelai_augment"]
    assert "tool" in aug_tool.input_schema.get("properties", {})
    assert "emotion" in aug_tool.input_schema.get("properties", {})


def test_default_model_is_v5_full():
    """Verify nai-diffusion-5-full is default and V3 is removed."""
    from novelai_mcp.models import ImageModel
    # V3 removed
    model_values = [m.value for m in ImageModel]
    assert "nai-diffusion-3" not in model_values
    assert "nai-diffusion-furry-3" not in model_values
    assert ImageModel.V5_FULL.value == "nai-diffusion-5-full"

    tools_list = asyncio.run(server.list_tools())
    tools = {t.name: t for t in tools_list}
    gen_model_prop = tools["novelai_generate_image"].input_schema["properties"]["model"]
    assert gen_model_prop.get("default") == "nai-diffusion-5-full"


def test_v5_new_tool_parameters():
    """Verify newly added V5 parameters exist in novelai_generate_image schema."""
    tools_list = asyncio.run(server.list_tools())
    tools = {t.name: t for t in tools_list}
    gen_props = tools["novelai_generate_image"].input_schema["properties"]

    assert "characters" in gen_props
    assert "render_text" in gen_props
    assert "allow_text" in gen_props
    assert "comic_panels" in gen_props
    assert "cfg_rescale" in gen_props
    assert "dynamic_thresholding" in gen_props

    # Vibe transfer should default to nai-diffusion-4-5-full
    vibe_props = tools["novelai_vibe_transfer"].input_schema["properties"]
    assert vibe_props["model"].get("default") == "nai-diffusion-4-5-full"




def test_expected_errors_become_tool_errors():
    """NovelAI and input errors must reach the model with their message."""
    from mcp.server.mcpserver.exceptions import ToolError

    from novelai_mcp.server import novelai_generate_image

    with pytest.raises(ToolError, match="Unsupported model"):
        asyncio.run(novelai_generate_image(prompt="x", model="nai-diffusion-3"))
    with pytest.raises(ToolError, match="Unknown size preset"):
        asyncio.run(novelai_generate_image(prompt="x", size="huge"))


def test_upscale_has_no_scale_parameter():
    """The /ai/upscale schema has no scale field."""
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    props = tools["novelai_upscale"].input_schema["properties"]
    assert "scale" not in props
    assert "model" in props
