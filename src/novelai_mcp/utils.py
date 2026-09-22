"""Image handling and file utilities for NovelAI MCP."""

import base64
import binascii
import io
import os
import time
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image

from novelai_mcp.models import SIZE_PRESET_MAP

# MCP clients start the server with an arbitrary working directory, so the default must be absolute.
DEFAULT_OUTPUT_DIR = Path.home() / "Pictures" / "NovelAI"


def round_to_64(value: int) -> int:
    """Round a dimension to the nearest multiple of 64 (minimum 64)."""
    return max(64, int(round(value / 64)) * 64)


def resolve_dimensions(
    size: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    default_preset: str = "portrait"
) -> Tuple[int, int]:
    """Resolve width and height. Explicit width and height win over the size preset."""
    if width is not None and height is not None:
        return round_to_64(width), round_to_64(height)

    if size:
        key = size.lower()
        if key not in SIZE_PRESET_MAP:
            raise ValueError(f"Unknown size preset '{size}'. Options: {', '.join(SIZE_PRESET_MAP)}")
        return SIZE_PRESET_MAP[key]

    return SIZE_PRESET_MAP[default_preset]


def load_image(image_input: str) -> Tuple[bytes, Image.Image, int, int]:
    """
    Load an image from a local file path or base64 string.

    Returns:
        Tuple of (raw_bytes, PIL.Image, width, height)
    """
    path = Path(image_input.strip('"\''))
    if path.is_file():
        raw_bytes = path.read_bytes()
    elif path.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"):
        raise ValueError(f"Image file not found: '{image_input}'")
    else:
        b64_str = image_input.strip()
        if b64_str.startswith("data:") and "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(b64_str, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError(f"Image file not found: '{image_input}'")

    try:
        pil_img = Image.open(io.BytesIO(raw_bytes))
        pil_img.load()
    except Exception as e:
        raise ValueError(f"Could not decode image data: {e}")
    width, height = pil_img.size
    return raw_bytes, pil_img, width, height


def image_to_base64(image_data: Union[bytes, Image.Image], format: str = "PNG") -> str:
    """Convert raw image bytes or PIL Image to base64 string."""
    if isinstance(image_data, Image.Image):
        buf = io.BytesIO()
        image_data.save(buf, format=format)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    elif isinstance(image_data, bytes):
        return base64.b64encode(image_data).decode("utf-8")
    else:
        raise TypeError(f"Unsupported image data type: {type(image_data)}")


def fit_image(img: Image.Image, width: int, height: int, is_mask: bool = False) -> Image.Image:
    """Resize an image to the exact generation size. The API expects image size to match width/height."""
    if img.size == (width, height):
        return img
    # Nearest keeps the mask strictly black/white.
    resample = Image.Resampling.NEAREST if is_mask else Image.Resampling.LANCZOS
    return img.resize((width, height), resample)


def extract_images_from_zip(data: bytes) -> List[bytes]:
    """
    NovelAI generation endpoints typically return a ZIP archive containing PNG images.
    This extracts all image files from the archive.
    """
    if image_extension(data) is not None:
        return [data]

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            images = [
                z.read(name)
                for name in sorted(z.namelist())
                if name.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
            ]
    except zipfile.BadZipFile:
        raise ValueError("NovelAI response is neither an image nor a ZIP archive")

    if not images:
        raise ValueError("NovelAI response ZIP contains no images")
    return images


def image_extension(data: bytes) -> Optional[str]:
    """Return the file extension for image bytes, or None if the format is unknown."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    return None


def save_image(
    image_bytes: bytes,
    output_dir: Optional[str] = None,
    prefix: str = "nai"
) -> str:
    """Save image bytes to disk and return absolute path."""
    if not output_dir:
        output_dir = os.environ.get("NOVELAI_OUTPUT_DIR") or str(DEFAULT_OUTPUT_DIR)

    out_path = Path(output_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    rand_id = uuid.uuid4().hex[:6]
    ext = image_extension(image_bytes) or ".png"
    file_path = out_path / f"{prefix}_{timestamp}_{rand_id}{ext}"

    file_path.write_bytes(image_bytes)
    return str(file_path)
