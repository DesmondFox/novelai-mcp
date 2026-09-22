"""NovelAI API Client implementation.

Request shapes follow the official schema at https://image.novelai.net/docs/doc.json.
"""

import os
import random
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from novelai_mcp import __version__
from novelai_mcp.models import (
    QUALITY_TAGS,
    UC_PRESET_INDEX,
    UC_PRESET_TAGS,
    AugmentTool,
    CharacterPrompt,
    EmotionPreset,
    ImageModel,
    Sampler,
    UCPreset,
)
from novelai_mcp.utils import (
    extract_images_from_zip,
    fit_image,
    image_to_base64,
    load_image,
    resolve_dimensions,
)

TEXT_TAGS = {"text", "words", "letters", "font", "no text"}


class NovelAIError(Exception):
    """An expected failure: bad input or an error response from NovelAI."""


def _join_tags(*parts: str) -> str:
    return ", ".join(p.strip().strip(",").strip() for p in parts if p and p.strip().strip(","))


def _max_characters(model_name: str) -> int:
    return 22 if "diffusion-5" in model_name else 6


class NovelAIClient:
    """Async client for NovelAI Image Generation API (image.novelai.net)."""

    BASE_URL = "https://image.novelai.net"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 120.0):
        self.api_key = api_key or os.environ.get("NOVELAI_API_KEY") or os.environ.get("NAI_API_KEY")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise NovelAIError(
                "NovelAI API key is missing. Please set the NOVELAI_API_KEY environment variable "
                "or pass api_key to the client."
            )
        return {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": f"NovelAI-MCP/{__version__}",
        }

    async def _request(
        self,
        method: str,
        path: str,
        name: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Send a request and turn HTTP and network failures into NovelAIError."""
        url = f"{self.BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(method, url, json=json, params=params, headers=self._get_headers())
        except httpx.HTTPError as e:
            raise NovelAIError(f"NovelAI {name} request failed: {type(e).__name__}: {e}") from e

        # The schema documents 201 for some endpoints and 200 for others.
        if not resp.is_success:
            try:
                err_msg = resp.json().get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise NovelAIError(f"NovelAI {name} failed with status {resp.status_code}: {err_msg}")
        return resp

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: Union[ImageModel, str] = ImageModel.V5_FULL,
        size: Optional[str] = "portrait",
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: int = 28,
        scale: float = 5.0,
        sampler: Union[Sampler, str] = Sampler.K_EULER_ANCESTRAL,
        seed: Optional[int] = None,
        uc_preset: Union[UCPreset, str] = UCPreset.LIGHT,
        quality_toggle: bool = True,
        transparent: bool = False,
        furry_mode: bool = False,
        background_mode: bool = False,
        characters: Optional[List[Union[CharacterPrompt, Dict[str, Any]]]] = None,
        render_text: Optional[str] = None,
        allow_text: bool = False,
        cfg_rescale: float = 0.0,
        dynamic_thresholding: bool = False,
        i2i_image: Optional[str] = None,
        i2i_strength: float = 0.6,
        i2i_noise: float = 0.0,
        inpaint_mask: Optional[str] = None,
        vibe_reference: Optional[str] = None,
        vibe_strength: float = 0.7,
        vibe_info_extracted: float = 0.7,
    ) -> Tuple[List[bytes], Dict[str, Any]]:
        """
        Generate image(s) via /ai/generate-image endpoint.
        Returns a tuple of (list of image bytes, metadata dict).
        """
        model_name = model.value if isinstance(model, ImageModel) else str(model)
        if "diffusion-5" not in model_name and "diffusion-4" not in model_name:
            raise NovelAIError(f"Unsupported model '{model_name}'. Use a V4, V4.5 or V5 model.")
        is_v5 = "diffusion-5" in model_name
        sampler_name = sampler.value if isinstance(sampler, Sampler) else str(sampler)
        try:
            uc = UCPreset(uc_preset)
        except ValueError:
            raise NovelAIError(f"Unknown uc_preset '{uc_preset}'. Options: {', '.join(p.value for p in UCPreset)}")

        w, h = resolve_dimensions(size, width, height)
        used_seed = seed if seed is not None and seed >= 0 else random.randint(0, 2**32 - 1)

        final_prompt = prompt
        if furry_mode and not final_prompt.startswith("fur dataset,"):
            final_prompt = f"fur dataset, {final_prompt}"
        elif background_mode and not final_prompt.startswith("background dataset,"):
            final_prompt = f"background dataset, {final_prompt}"

        if render_text:
            allow_text = True
            if f'"{render_text}"' not in final_prompt:
                final_prompt = f"{final_prompt}, text: \"{render_text}\""

        # The API only takes transparency as a hint; the prompt itself has to ask for it.
        if transparent and "transparent background" not in final_prompt.lower():
            final_prompt = f"{final_prompt}, transparent background"

        if quality_toggle:
            quality = [t for t in QUALITY_TAGS if not (allow_text and t in TEXT_TAGS)]
            final_prompt = _join_tags(final_prompt, *quality)

        final_neg = _join_tags(negative_prompt or "", UC_PRESET_TAGS[uc])
        if allow_text:
            neg_tags = [t.strip() for t in final_neg.split(",") if t.strip()]
            final_neg = ", ".join(t for t in neg_tags if t.lower() not in TEXT_TAGS)

        char_captions, char_neg_captions, has_coords = self._build_characters(characters or [], model_name)

        params: Dict[str, Any] = {
            "params_version": 4 if is_v5 else 3,
            "width": w,
            "height": h,
            "scale": scale,
            "sampler": sampler_name,
            "steps": steps,
            "seed": used_seed,
            "n_samples": 1,
            "ucPreset": UC_PRESET_INDEX[uc],
            "qualityToggle": quality_toggle,
            "v4_prompt": {
                "caption": {"base_caption": final_prompt, "char_captions": char_captions},
                "use_coords": has_coords,
                "use_order": True,
            },
            "v4_negative_prompt": {
                "caption": {"base_caption": final_neg, "char_captions": char_neg_captions},
                "use_coords": has_coords,
                "use_order": True,
            },
            "dynamic_thresholding": dynamic_thresholding,
            "cfg_rescale": cfg_rescale,
            "deliberate_euler_ancestral_bug": True,
            "prefer_brownian": True,
        }
        if is_v5:
            params["noise_schedule"] = "karras"
        if transparent:
            params["tag_hint_transparent_background"] = True

        action = "generate"
        if i2i_image:
            _, src_img, _, _ = load_image(i2i_image)
            params["image"] = image_to_base64(fit_image(src_img, w, h))
            params["strength"] = i2i_strength
            params["noise"] = i2i_noise
            params["extra_noise_seed"] = used_seed
            action = "img2img"

        if inpaint_mask:
            if not i2i_image:
                raise NovelAIError("Inpainting requires a source image.")
            _, mask_img, _, _ = load_image(inpaint_mask)
            params["mask"] = image_to_base64(fit_image(mask_img.convert("L"), w, h, is_mask=True))
            params["add_original_image"] = True
            action = "infill"

        if vibe_reference:
            vibe_b64 = await self.encode_vibe(vibe_reference, model_name, vibe_info_extracted)
            params["reference_image_multiple"] = [vibe_b64]
            params["reference_information_extracted_multiple"] = [vibe_info_extracted]
            params["reference_strength_multiple"] = [vibe_strength]

        payload = {
            "input": final_prompt,
            "model": model_name,
            "action": action,
            "parameters": params,
        }

        resp = await self._request("POST", "/ai/generate-image", "generation", json=payload)
        images = extract_images_from_zip(resp.content)

        metadata = {
            "model": model_name,
            "action": action,
            "prompt": final_prompt,
            "seed": used_seed,
            "width": w,
            "height": h,
            "steps": steps,
            "scale": scale,
            "sampler": sampler_name,
            "transparent": transparent,
        }
        return images, metadata

    @staticmethod
    def _build_characters(
        characters: List[Union[CharacterPrompt, Dict[str, Any]]],
        model_name: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """Build v4 char_captions for the positive and negative prompt."""
        limit = _max_characters(model_name)
        if len(characters) > limit:
            raise NovelAIError(f"Model '{model_name}' supports at most {limit} characters, got {len(characters)}.")

        char_captions: List[Dict[str, Any]] = []
        char_neg_captions: List[Dict[str, Any]] = []
        has_coords = False
        for raw in characters:
            try:
                char = raw if isinstance(raw, CharacterPrompt) else CharacterPrompt.model_validate(raw)
            except Exception as e:
                raise NovelAIError(f"Invalid character entry {raw!r}: {e}") from e

            centers: List[Dict[str, float]] = []
            if char.position is not None:
                cx, cy = char.position
                if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
                    raise NovelAIError(f"Character position must be within 0.0-1.0, got {char.position}.")
                centers = [{"x": cx, "y": cy}]
                has_coords = True

            char_captions.append({"char_caption": char.prompt, "centers": centers})
            char_neg_captions.append({"char_caption": char.negative_prompt or "", "centers": centers})

        return char_captions, char_neg_captions, has_coords

    async def augment_image(
        self,
        image_input: str,
        tool: Union[AugmentTool, str],
        emotion: Optional[Union[EmotionPreset, str]] = None,
        prompt: Optional[str] = None,
        defry: int = 0,
    ) -> Tuple[List[bytes], Dict[str, Any]]:
        """
        Director Tools: Modify an image via /ai/augment-image.

        bg-removal returns several images (masked, generated, blend); other tools return one.
        """
        try:
            tool_name = AugmentTool(tool).value
        except ValueError:
            raise NovelAIError(f"Unknown tool '{tool}'. Options: {', '.join(t.value for t in AugmentTool)}")
        if not 0 <= defry <= 5:
            raise NovelAIError(f"defry must be between 0 and 5, got {defry}.")

        raw_bytes, _, width, height = load_image(image_input)
        payload: Dict[str, Any] = {
            "req_type": tool_name,
            "image": image_to_base64(raw_bytes),
            "width": width,
            "height": height,
        }

        if tool_name == "emotion":
            try:
                emo = EmotionPreset(emotion or "neutral").value
            except ValueError:
                raise NovelAIError(
                    f"Unknown emotion '{emotion}'. Options: {', '.join(e.value for e in EmotionPreset)}"
                )
            # The web client sends the emotion as "<emotion>;;<extra prompt>" and the level as defry.
            payload["prompt"] = f"{emo};;{prompt or ''}"
            payload["defry"] = defry
        elif tool_name == "colorize":
            payload["prompt"] = prompt or ""
            payload["defry"] = defry

        resp = await self._request("POST", "/ai/augment-image", f"augment-image ({tool_name})", json=payload)
        images = extract_images_from_zip(resp.content)

        metadata = {
            "tool": tool_name,
            "width": width,
            "height": height,
            "options": {k: v for k, v in payload.items() if k != "image"},
        }
        return images, metadata

    async def upscale(
        self,
        image_input: str,
        model: Union[ImageModel, str] = ImageModel.V5_FULL,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Upscale an image via /ai/upscale. The API has no scale parameter.
        """
        model_name = model.value if isinstance(model, ImageModel) else str(model)
        raw_bytes, _, width, height = load_image(image_input)
        payload = {"image": image_to_base64(raw_bytes), "model": model_name}

        resp = await self._request("POST", "/ai/upscale", "upscale", json=payload)
        result_bytes = extract_images_from_zip(resp.content)[0]
        _, _, out_w, out_h = load_image(image_to_base64(result_bytes))

        metadata = {
            "original_width": width,
            "original_height": height,
            "target_width": out_w,
            "target_height": out_h,
        }
        return result_bytes, metadata

    async def encode_vibe(
        self,
        image_input: str,
        model: str,
        information_extracted: float = 0.7,
    ) -> str:
        """
        Encode a reference image for Vibe Transfer via /ai/encode-vibe.
        Returns the encoding as base64, ready for reference_image_multiple.
        """
        raw_bytes, _, _, _ = load_image(image_input)
        payload = {
            "image": image_to_base64(raw_bytes),
            "information_extracted": information_extracted,
            "model": model,
        }
        resp = await self._request("POST", "/ai/encode-vibe", "encode-vibe", json=payload)
        return image_to_base64(resp.content)

    async def suggest_tags(
        self,
        query: str,
        model: Union[ImageModel, str] = ImageModel.V5_FULL,
        lang: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Suggest Danbooru/NovelAI tags via /ai/generate-image/suggest-tags.
        """
        model_name = model.value if isinstance(model, ImageModel) else str(model)
        params = {"prompt": query, "model": model_name, "lang": lang}
        resp = await self._request("GET", "/ai/generate-image/suggest-tags", "suggest-tags", params=params)

        data = resp.json()
        if isinstance(data, dict):
            return data.get("tags") or []
        if isinstance(data, list):
            return data
        raise NovelAIError(f"Unexpected suggest-tags response: {data!r}")
