"""NovelAI MCP Server using MCPServer (mcp SDK 2.x)."""

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Union

from dotenv import load_dotenv
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from novelai_mcp import __version__
from novelai_mcp.client import NovelAIClient, NovelAIError
from novelai_mcp.models import DEFAULT_STEPS
from novelai_mcp.utils import load_image, round_to_64, save_image

# Load environment variables from .env if present
load_dotenv()

server = MCPServer(
    name="NovelAI Image Server",
    version=__version__,
    description="MCP Server for NovelAI Image Generation (V5 Full/Curated, V4.5, Inpainting, Director Tools, Upscaling, Vibe Transfer)"
)

_client: Optional[NovelAIClient] = None


def get_client() -> NovelAIClient:
    """Get or initialize NovelAIClient."""
    global _client
    if _client is None:
        _client = NovelAIClient()
    return _client


@contextmanager
def _expected_errors() -> Iterator[None]:
    """Convert expected failures to ToolError.

    MCPServer hides the message of any other exception from the model.
    """
    try:
        yield
    except (NovelAIError, ValueError) as e:
        raise ToolError(str(e)) from e


@server.tool(
    name="novelai_generate_image",
    description=(
        "Generate anime/art images with NovelAI Diffusion models (prioritizing V5 Full/Curated, V4.5). "
        "Supports natural language, Danbooru tags, multilingual prompts, transparent background, and custom dimensions."
    ),
)
async def novelai_generate_image(
    prompt: str,
    negative_prompt: Optional[str] = None,
    model: str = "nai-diffusion-5-full",
    size: Optional[str] = "portrait",
    width: Optional[int] = None,
    height: Optional[int] = None,
    steps: int = DEFAULT_STEPS,
    scale: float = 5.0,
    sampler: str = "k_euler_ancestral",
    seed: Optional[int] = None,
    uc_preset: str = "light",
    quality_toggle: bool = True,
    transparent: bool = False,
    furry_mode: bool = False,
    background_mode: bool = False,
    characters: Optional[List[Dict[str, Any]]] = None,
    render_text: Optional[str] = None,
    allow_text: bool = False,
    comic_panels: bool = False,
    cfg_rescale: float = 0.0,
    dynamic_thresholding: bool = False,
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Generate an image from a text prompt.

    Args:
        prompt: Description of the image. Danbooru tags or natural language (English/Japanese/etc.).
        negative_prompt: Undesired content. The uc_preset tags are appended to it.
        model: Model name (defaults to 'nai-diffusion-5-full'). Options: nai-diffusion-5-full, nai-diffusion-5-curated, nai-diffusion-4-5-full, nai-diffusion-4-5-curated.
        size: Dimension preset: portrait (832x1216), landscape (1216x832), square (1024x1024), wallpaper (1920x1088), comic_page (832x1216), comic_strip (1536x640), manga_page (832x1216). Ignored when width and height are both set.
        width: Custom width (rounded to nearest multiple of 64). Requires height.
        height: Custom height (rounded to nearest multiple of 64). Requires width.
        steps: Number of diffusion steps (typically 23-35).
        scale: Prompt guidance / CFG scale (typically 4.0 - 7.0, default 5.0).
        sampler: Sampler algorithm (k_euler, k_euler_ancestral, k_dpmpp_2m, k_dpmpp_2s_ancestral, etc.).
        seed: Random seed for reproducibility. Pass a non-negative integer, or leave None for random.
        uc_preset: Undesired content preset: 'strong', 'light', 'furry_focus', 'human_focus', 'none'.
        quality_toggle: Whether to append quality tags to the prompt.
        transparent: If true, asks for a transparent background.
        furry_mode: If true, prepends 'fur dataset,' for furry/kemono style.
        background_mode: If true, prepends 'background dataset,' for scenery without characters.
        characters: Character descriptors for multi-character composition (up to 22 on V5, 6 on V4/V4.5). Each item: {'prompt': '...', 'negative_prompt': '...', 'position': [x, y]} where x,y are normalized 0.0-1.0.
        render_text: In-image text to render (e.g. signs, clothing text). Removes text suppression from the prompts.
        allow_text: Whether to allow text/words in image without negative prompt suppression.
        comic_panels: If true, adds comic/manga panel tags to the prompt.
        cfg_rescale: CFG rescale factor (0.0 to 1.0) to prevent color burning at high CFG scale.
        dynamic_thresholding: Whether to enable dynamic thresholding for high CFG scale.
        output_dir: Directory where the generated image will be saved (defaults to NOVELAI_OUTPUT_DIR or ~/Pictures/NovelAI).
    """
    final_prompt = prompt
    if comic_panels:
        if "multiple panels" not in final_prompt and "manga panels" not in final_prompt and "comic" not in final_prompt:
            final_prompt = f"comic, manga panels, multiple panels, {final_prompt}"

    with _expected_errors():
        images, meta = await get_client().generate_image(
            prompt=final_prompt,
            negative_prompt=negative_prompt,
            model=model,
            size=size,
            width=width,
            height=height,
            steps=steps,
            scale=scale,
            sampler=sampler,
            seed=seed,
            uc_preset=uc_preset,
            quality_toggle=quality_toggle,
            transparent=transparent,
            furry_mode=furry_mode,
            background_mode=background_mode,
            characters=characters,
            render_text=render_text,
            allow_text=allow_text,
            cfg_rescale=cfg_rescale,
            dynamic_thresholding=dynamic_thresholding,
        )

    saved_path = save_image(images[0], output_dir=output_dir, prefix="t2i")
    info_text = (
        f"Image generated successfully!\n"
        f"- Saved to: {saved_path}\n"
        f"- Model: {meta['model']}\n"
        f"- Dimensions: {meta['width']}x{meta['height']}\n"
        f"- Seed: {meta['seed']}\n"
        f"- Steps: {meta['steps']}, Scale: {meta['scale']}, Sampler: {meta['sampler']}\n"
        f"- Prompt: {meta['prompt']}"
    )
    return [info_text, Image(path=saved_path)]


@server.tool(
    name="novelai_img2img",
    description=(
        "Modify or restyle an existing image using NovelAI Image-to-Image. "
        "Applies new prompt with adjustable change strength (0.0 to 1.0) and optional noise."
    ),
)
async def novelai_img2img(
    image_path: str,
    prompt: str,
    strength: float = 0.6,
    noise: float = 0.0,
    negative_prompt: Optional[str] = None,
    model: str = "nai-diffusion-5-full",
    size: Optional[str] = None,
    steps: int = DEFAULT_STEPS,
    scale: float = 5.0,
    sampler: str = "k_euler_ancestral",
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Image-to-Image modification.

    Args:
        image_path: Path to source image file or base64 data.
        prompt: Description of modifications or new scene.
        strength: How much to alter the image (0.1 = subtle changes, 0.7 = heavy transformation).
        noise: Additional noise to hallucinate new details (0.0 - 0.2).
        negative_prompt: Undesired content.
        model: Diffusion model to use.
        size: Preset, or None to match the source image (rounded to a multiple of 64). The source is resized to fit.
        steps: Diffusion steps.
        scale: Guidance scale.
        sampler: Sampler algorithm.
        seed: Random seed.
        output_dir: Directory to save the output.
    """
    with _expected_errors():
        w, h = None, None
        if not size:
            _, _, src_w, src_h = load_image(image_path)
            w, h = round_to_64(src_w), round_to_64(src_h)

        images, meta = await get_client().generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            size=size,
            width=w,
            height=h,
            steps=steps,
            scale=scale,
            sampler=sampler,
            seed=seed,
            i2i_image=image_path,
            i2i_strength=strength,
            i2i_noise=noise,
        )

    saved_path = save_image(images[0], output_dir=output_dir, prefix="i2i")
    info_text = (
        f"Image modified successfully (Img2Img)!\n"
        f"- Saved to: {saved_path}\n"
        f"- Model: {meta['model']}\n"
        f"- Strength: {strength}, Noise: {noise}\n"
        f"- Dimensions: {meta['width']}x{meta['height']}\n"
        f"- Seed: {meta['seed']}"
    )
    return [info_text, Image(path=saved_path)]


@server.tool(
    name="novelai_inpaint",
    description=(
        "Inpaint / redraw specific parts of an image using a mask. "
        "Allows replacing clothes, faces, hair, background or fixing anatomy."
    ),
)
async def novelai_inpaint(
    image_path: str,
    mask_path: str,
    prompt: str,
    strength: float = 0.7,
    negative_prompt: Optional[str] = None,
    model: str = "nai-diffusion-5-full",
    steps: int = DEFAULT_STEPS,
    scale: float = 5.0,
    sampler: str = "k_euler_ancestral",
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Inpaint masked area.

    Args:
        image_path: Source image file path or base64. Output size is the source size rounded to a multiple of 64.
        mask_path: Mask image file path or base64 (white = area to repaint, black = keep). Resized to the output size.
        prompt: Description of what should be drawn in the masked area.
        strength: Repainting strength (0.5 to 1.0).
        negative_prompt: Undesired content.
        model: Diffusion model.
        steps: Steps.
        scale: Guidance scale.
        sampler: Sampler algorithm.
        seed: Random seed.
        output_dir: Directory to save the output.
    """
    with _expected_errors():
        _, _, src_w, src_h = load_image(image_path)

        images, meta = await get_client().generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            size=None,
            width=round_to_64(src_w),
            height=round_to_64(src_h),
            steps=steps,
            scale=scale,
            sampler=sampler,
            seed=seed,
            i2i_image=image_path,
            inpaint_mask=mask_path,
            i2i_strength=strength,
        )

    saved_path = save_image(images[0], output_dir=output_dir, prefix="inpaint")
    info_text = (
        f"Inpainting complete!\n"
        f"- Saved to: {saved_path}\n"
        f"- Model: {meta['model']}\n"
        f"- Strength: {strength}\n"
        f"- Dimensions: {meta['width']}x{meta['height']}\n"
        f"- Seed: {meta['seed']}"
    )
    return [info_text, Image(path=saved_path)]


@server.tool(
    name="novelai_augment",
    description=(
        "NovelAI Director Tools for image manipulations: remove background ('bg-removal'), "
        "extract line art ('lineart'), convert to sketch ('sketch'), colorize sketch ('colorize'), "
        "change facial expressions/emotions ('emotion'), or declutter ('declutter')."
    ),
)
async def novelai_augment(
    image_path: str,
    tool: str,
    emotion: Optional[str] = None,
    prompt: Optional[str] = None,
    defry: int = 0,
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Apply Director Tools / Augmentations to an image.

    Args:
        image_path: Path to input image file or base64.
        tool: Augmentation type. Options: 'bg-removal', 'lineart', 'sketch', 'colorize', 'emotion', 'declutter'.
        emotion: Emotion if tool='emotion'. Options: neutral, happy, sad, angry, scared, surprised, tired, excited, nervous, thinking, confused, shy, disgusted, smug, bored, laughing, irritated, aroused, embarrassed, worried, love, determined, hurt, playful.
        prompt: Extra prompt for 'colorize' or 'emotion'.
        defry: 0 to 5. For 'colorize' and 'emotion': higher values weaken the change (emotion level).
        output_dir: Directory to save the output.
    """
    with _expected_errors():
        images, meta = await get_client().augment_image(
            image_input=image_path,
            tool=tool,
            emotion=emotion,
            prompt=prompt,
            defry=defry,
        )

    saved_paths = [save_image(img, output_dir=output_dir, prefix=f"aug_{meta['tool']}") for img in images]
    info_text = (
        f"Augmentation '{meta['tool']}' applied successfully!\n"
        + "".join(f"- Saved to: {p}\n" for p in saved_paths)
        + f"- Dimensions: {meta['width']}x{meta['height']}\n"
        f"- Options: {meta['options']}"
    )
    return [info_text, *(Image(path=p) for p in saved_paths)]


@server.tool(
    name="novelai_upscale",
    description="Upscale an image with NovelAI's neural upscaler.",
)
async def novelai_upscale(
    image_path: str,
    model: str = "nai-diffusion-5-full",
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Upscale image resolution. The upscale factor is chosen by NovelAI.

    Args:
        image_path: Path to source image.
        model: Image model name the upscale is billed and run against.
        output_dir: Directory to save the output.
    """
    with _expected_errors():
        result_bytes, meta = await get_client().upscale(image_input=image_path, model=model)

    saved_path = save_image(result_bytes, output_dir=output_dir, prefix="upscale")
    info_text = (
        f"Upscale completed!\n"
        f"- Saved to: {saved_path}\n"
        f"- Original: {meta['original_width']}x{meta['original_height']}\n"
        f"- Upscaled: {meta['target_width']}x{meta['target_height']}"
    )
    return [info_text, Image(path=saved_path)]


@server.tool(
    name="novelai_vibe_transfer",
    description=(
        "Generate a new image influenced by the style, colors, and atmosphere of a reference image (Vibe Transfer)."
    ),
)
async def novelai_vibe_transfer(
    reference_image_path: str,
    prompt: str,
    reference_strength: float = 0.7,
    information_extracted: float = 0.7,
    negative_prompt: Optional[str] = None,
    model: str = "nai-diffusion-4-5-full",
    size: Optional[str] = "portrait",
    steps: int = DEFAULT_STEPS,
    scale: float = 5.0,
    sampler: str = "k_euler_ancestral",
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> List[Union[str, Image]]:
    """
    Vibe Transfer: Transfer aesthetic and color palette from reference image to a new generation.

    Args:
        reference_image_path: Path to image whose vibe should be extracted.
        prompt: Description of the new image to generate.
        reference_strength: Influence of the reference vibe (0.0 to 1.0, default 0.7).
        information_extracted: How much information to extract from the reference (0.0 to 1.0, default 0.7).
        negative_prompt: Undesired content.
        model: Diffusion model to use (defaults to 'nai-diffusion-4-5-full'). The vibe is encoded for this model.
        size: Preset dimension (e.g. portrait, landscape, square).
        steps: Diffusion steps.
        scale: Guidance scale.
        sampler: Sampler algorithm.
        seed: Random seed.
        output_dir: Directory to save the output.
    """
    with _expected_errors():
        images, meta = await get_client().generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            size=size,
            steps=steps,
            scale=scale,
            sampler=sampler,
            seed=seed,
            vibe_reference=reference_image_path,
            vibe_strength=reference_strength,
            vibe_info_extracted=information_extracted,
        )

    saved_path = save_image(images[0], output_dir=output_dir, prefix="vibe")
    info_text = (
        f"Vibe Transfer generation complete!\n"
        f"- Saved to: {saved_path}\n"
        f"- Reference Vibe: {reference_image_path} (strength={reference_strength})\n"
        f"- Model: {meta['model']}\n"
        f"- Dimensions: {meta['width']}x{meta['height']}\n"
        f"- Seed: {meta['seed']}"
    )
    return [info_text, Image(path=saved_path)]


@server.tool(
    name="novelai_suggest_tags",
    description="Search and suggest valid Danbooru/NovelAI tags matching a query string.",
)
async def novelai_suggest_tags(
    query: str,
    model: str = "nai-diffusion-5-full",
    lang: str = "en",
) -> str:
    """
    Suggest tags for prompt construction.

    Args:
        query: Tag search query (e.g. 'kimono', 'silver_h', 'sunset').
        model: Target model.
        lang: Query language: 'en' or 'jp'.
    """
    with _expected_errors():
        tags = await get_client().suggest_tags(query=query, model=model, lang=lang)
    if not tags:
        return f"No tag suggestions found for '{query}'."

    formatted = []
    for item in tags[:20]:
        if isinstance(item, dict):
            tag_name = item.get("tag", str(item))
            count = item.get("count")
            formatted.append(f"- {tag_name}" + (f" ({count} uses)" if count else ""))
        else:
            formatted.append(f"- {item}")

    return f"Tag suggestions for '{query}':\n" + "\n".join(formatted)


def main():
    """Run the MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
