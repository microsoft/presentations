"""Image generation via the Azure AI endpoint.

Uses the Azure OpenAI-compatible ``/images/generations``  Authentication
is handled through :class:`~azure.identity.DefaultAzureCredential`.

Generated images are cached under ``<output_dir>/images/`` so repeated builds
never re-generate the same prompt.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from urllib.parse import urlparse
from typing import Any

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _get_image_cache_dir(output_dir: str) -> str:
    cache_dir = os.path.join(output_dir, "images")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _prompt_cache_key(prompt: str, model: str) -> str:
    key = f"{model}::{prompt}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Azure REST-based image generation
# ---------------------------------------------------------------------------


def _get_azure_token() -> str:
    """Obtain a bearer token from ``DefaultAzureCredential``."""
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return token.token


def _generate_image_azure(
    prompt: str,
    cached_path: str,
    model: str,
    size: str,
    endpoint: str,
    deployment: str,
    api_version: str = "2025-04-01-preview",
) -> str | None:
    """Call the Azure OpenAI images/generations REST endpoint directly."""
    import urllib.request

    url = (
        f"{endpoint.rstrip('/')}/openai/deployments/{deployment}"
        f"/images/generations?api-version={api_version}"
    )

    body = json.dumps({
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": "medium",
    }).encode("utf-8")

    try:
        token = _get_azure_token()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        print(f"  [{model}] Generating image: {prompt[:80]}...")
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        b64_data = result["data"][0]["b64_json"]
        image_bytes = base64.b64decode(b64_data)
        with open(cached_path, "wb") as f:
            f.write(image_bytes)
        print(f"  Saved generated image: {cached_path}")
        return cached_path
    except Exception as exc:
        print(f"Warning: image generation failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    output_dir: str,
    model: str,
    size: str = "1024x1024",
) -> str | None:
    """Generate an image and return the local file path (or *None* on failure).

    Uses the Azure AI endpoint configured through environment variables:

    * ``AZURE_AI_PROJECT_ENDPOINT`` – Foundry project endpoint
    * ``AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME`` – deployment name (defaults to *model*)

    Generated images are cached under ``<output_dir>/images/``.
    """
    cache_dir = _get_image_cache_dir(output_dir)
    cache_name = f"{_prompt_cache_key(prompt, model)}.png"
    cached_path = os.path.join(cache_dir, cache_name)

    if os.path.isfile(cached_path):
        print(f"  Using cached image: {cached_path}")
        return cached_path

    # Derive the *.openai.azure.com endpoint from AI_PROJECT_NAME or AZURE_AI_PROJECT_ENDPOINT
    account = os.environ.get("AI_PROJECT_NAME", "").strip()
    if not account:
        raw = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()
        if raw:
            host = urlparse(raw).hostname or ""
            account = host.split(".")[0]
    if not account:
        print(
            "Warning: AI_PROJECT_NAME / AZURE_AI_PROJECT_ENDPOINT not set — cannot generate "
            f"image for prompt: {prompt[:80]}..."
        )
        return None

    endpoint = f"https://{account}.openai.azure.com"

    deployment = (
        os.environ.get("AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME", "").strip()
        or model
    )

    return _generate_image_azure(
        prompt, cached_path, model=model, size=size,
        endpoint=endpoint, deployment=deployment,
    )


def resolve_image_prompt(
    slide_data: dict,
    output_dir: str,
    default_model: str = "",
) -> None:
    """If the slide has an ``image_prompt``, generate the image and set ``image``."""
    ip = slide_data.get("image_prompt")
    if not ip:
        return
    # Don't overwrite an explicit **Image** field if the file exists
    existing = slide_data.get("image")
    if existing and os.path.isfile(existing.get("path", "")):
        return

    model = ip.get("model", default_model)
    if not model:
        return

    try:
        path = generate_image(ip["prompt"], output_dir, model=model)
    except Exception as exc:
        print(f"Warning: image generation failed for slide — {exc}")
        return
    if path:
        img: dict[str, Any] = {"path": path}
        for k in ("left", "top", "width", "height"):
            if k in ip:
                img[k] = ip[k]
        slide_data["image"] = img
