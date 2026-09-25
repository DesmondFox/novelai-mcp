"""Data models, enums, and constants for NovelAI MCP."""

from enum import Enum
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field


class ImageModel(str, Enum):
    """Supported NovelAI image generation models."""
    V5_FULL = "nai-diffusion-5-full"
    V5_CURATED = "nai-diffusion-5-curated"
    V4_5_FULL = "nai-diffusion-4-5-full"
    V4_5_CURATED = "nai-diffusion-4-5-curated"
    V4_FULL = "nai-diffusion-4-full"
    V4_CURATED = "nai-diffusion-4-curated"


SIZE_PRESET_MAP: Dict[str, Tuple[int, int]] = {
    "portrait": (832, 1216),
    "landscape": (1216, 832),
    "square": (1024, 1024),
    "wallpaper": (1920, 1088),
    "portrait_normal": (512, 768),
    "landscape_normal": (768, 512),
    "square_normal": (640, 640),
    "comic_page": (832, 1216),
    "comic_strip": (1536, 640),
    "manga_page": (832, 1216),
}


class CharacterPrompt(BaseModel):
    """Individual character description and position for NovelAI multi-character prompting."""
    prompt: str = Field(description="Character description and tags (e.g. '1girl, silver hair, blue eyes, knight armor')")
    negative_prompt: Optional[str] = Field(default=None, description="Character-specific negative prompt")
    position: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Optional normalized (x, y) coordinates between 0.0 and 1.0 (e.g. (0.25, 0.5) for left side)"
    )


class Sampler(str, Enum):
    """Sampling algorithms."""
    K_EULER = "k_euler"
    K_EULER_ANCESTRAL = "k_euler_ancestral"
    K_DPMPP_2M = "k_dpmpp_2m"
    K_DPMPP_2S_ANCESTRAL = "k_dpmpp_2s_ancestral"
    K_DPMPP_SDE = "k_dpmpp_sde"
    DDIM = "ddim"


class UCPreset(str, Enum):
    """Undesired content presets."""
    STRONG = "strong"
    LIGHT = "light"
    FURRY_FOCUS = "furry_focus"
    HUMAN_FOCUS = "human_focus"
    NONE = "none"


# The API does not expand presets itself: the web client appends these tags to the
# prompt text and sends ucPreset/qualityToggle only as metadata. Values are from V4.5.
UC_PRESET_INDEX: Dict[UCPreset, int] = {
    UCPreset.STRONG: 0,
    UCPreset.LIGHT: 1,
    UCPreset.FURRY_FOCUS: 2,
    UCPreset.HUMAN_FOCUS: 3,
    UCPreset.NONE: 4,
}

UC_PRESET_TAGS: Dict[UCPreset, str] = {
    UCPreset.STRONG: (
        "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, "
        "very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, "
        "too many watermarks, negative space, blank page"
    ),
    UCPreset.LIGHT: (
        "lowres, artistic error, scan artifacts, worst quality, bad quality, jpeg artifacts, multiple views, "
        "very displeasing, too many watermarks, negative space, blank page"
    ),
    UCPreset.FURRY_FOCUS: (
        "{worst quality}, distracting watermark, unfinished, bad quality, {widescreen}, upscale, {sequence}, "
        "{{grandfathered content}}, blurred foreground, chromatic aberration, sketch, everyone, "
        "[sketch background], simple, [flat colors], ych (character), outline, multiple scenes, "
        "[[horror (theme)]], comic"
    ),
    UCPreset.HUMAN_FOCUS: (
        "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, "
        "very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, "
        "too many watermarks, negative space, blank page, @_@, mismatched pupils, glowing eyes, bad anatomy"
    ),
    UCPreset.NONE: "",
}

QUALITY_TAGS = ["very aesthetic", "masterpiece", "no text"]

# Same default as the NovelAI website.
DEFAULT_STEPS = 23


class AugmentTool(str, Enum):
    """Director Tools for image augmentation."""
    BG_REMOVAL = "bg-removal"
    LINEART = "lineart"
    SKETCH = "sketch"
    COLORIZE = "colorize"
    EMOTION = "emotion"
    DECLUTTER = "declutter"


class EmotionPreset(str, Enum):
    """Emotion presets of the Director Tools 'emotion' tool."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SCARED = "scared"
    SURPRISED = "surprised"
    TIRED = "tired"
    EXCITED = "excited"
    NERVOUS = "nervous"
    THINKING = "thinking"
    CONFUSED = "confused"
    SHY = "shy"
    DISGUSTED = "disgusted"
    SMUG = "smug"
    BORED = "bored"
    LAUGHING = "laughing"
    IRRITATED = "irritated"
    AROUSED = "aroused"
    EMBARRASSED = "embarrassed"
    WORRIED = "worried"
    LOVE = "love"
    DETERMINED = "determined"
    HURT = "hurt"
    PLAYFUL = "playful"
