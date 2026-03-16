"""Tests for src/images.py."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from src.images import (
    _get_image_cache_dir,
    _generate_image_azure,
    _prompt_cache_key,
    generate_image,
    resolve_image_prompt,
)


# ---------------------------------------------------------------------------
# _get_image_cache_dir
# ---------------------------------------------------------------------------


class TestGetImageCacheDir:
    def test_creates_directory(self, tmp_path):
        d = _get_image_cache_dir(str(tmp_path))
        assert os.path.isdir(d)
        assert d == os.path.join(str(tmp_path), "images")

    def test_idempotent(self, tmp_path):
        d1 = _get_image_cache_dir(str(tmp_path))
        d2 = _get_image_cache_dir(str(tmp_path))
        assert d1 == d2


# ---------------------------------------------------------------------------
# _prompt_cache_key
# ---------------------------------------------------------------------------


class TestPromptCacheKey:
    def test_deterministic(self):
        k1 = _prompt_cache_key("A cat", "model-1")
        k2 = _prompt_cache_key("A cat", "model-1")
        assert k1 == k2

    def test_different_prompts_differ(self):
        k1 = _prompt_cache_key("A cat", "m")
        k2 = _prompt_cache_key("A dog", "m")
        assert k1 != k2

    def test_different_models_differ(self):
        k1 = _prompt_cache_key("A cat", "m1")
        k2 = _prompt_cache_key("A cat", "m2")
        assert k1 != k2

    def test_length(self):
        k = _prompt_cache_key("prompt", "model")
        assert len(k) == 16


# ---------------------------------------------------------------------------
# generate_image
# ---------------------------------------------------------------------------


class TestGenerateImage:
    def test_returns_cached_path(self, tmp_path):
        cache_dir = os.path.join(str(tmp_path), "images")
        os.makedirs(cache_dir, exist_ok=True)
        key = _prompt_cache_key("cached prompt", "test-model")
        cached_path = os.path.join(cache_dir, f"{key}.png")
        with open(cached_path, "wb") as f:
            f.write(b"fake png")

        result = generate_image("cached prompt", str(tmp_path), model="test-model")
        assert result == cached_path

    def test_no_endpoint_returns_none(self, tmp_path):
        env = {"AI_PROJECT_NAME": "", "AZURE_AI_PROJECT_ENDPOINT": ""}
        with patch.dict(os.environ, env, clear=False):
            result = generate_image("prompt", str(tmp_path), model="m")
            assert result is None

    def test_uses_ai_project_name(self, tmp_path):
        env = {
            "AI_PROJECT_NAME": "myaccount",
            "AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME": "dall-e-3",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch("src.images._generate_image_azure", return_value="/fake/path.png") as mock_gen:
            result = generate_image("a cat", str(tmp_path), model="dall-e-3")
            assert result == "/fake/path.png"
            call_kwargs = mock_gen.call_args
            assert "myaccount" in call_kwargs[1]["endpoint"] or "myaccount" in str(call_kwargs)

    def test_uses_project_endpoint_fallback(self, tmp_path):
        env = {
            "AI_PROJECT_NAME": "",
            "AZURE_AI_PROJECT_ENDPOINT": "https://myproj.services.ai.azure.com/stuff",
            "AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME": "",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch("src.images._generate_image_azure", return_value="/fake.png") as mock_gen:
            result = generate_image("a cat", str(tmp_path), model="dall-e-3")
            assert result == "/fake.png"


# ---------------------------------------------------------------------------
# resolve_image_prompt
# ---------------------------------------------------------------------------


class TestResolveImagePrompt:
    def test_no_prompt_is_noop(self):
        slide = {"image_prompt": None}
        resolve_image_prompt(slide, "output", default_model="m")
        assert slide.get("image") is None

    def test_existing_image_not_overwritten(self):
        slide = {
            "image_prompt": {"prompt": "A cat"},
            "image": {"path": "existing.png"},
        }
        resolve_image_prompt(slide, "output", default_model="m")
        assert slide["image"]["path"] == "existing.png"

    def test_no_model_skips(self):
        slide = {"image_prompt": {"prompt": "A cat"}}
        resolve_image_prompt(slide, "output", default_model="")
        assert slide.get("image") is None

    def test_sets_image_on_success(self, tmp_path):
        slide = {
            "image_prompt": {"prompt": "A cat", "left": 1.0, "top": 2.0},
        }
        with patch("src.images.generate_image", return_value="/gen.png"):
            resolve_image_prompt(slide, str(tmp_path), default_model="model")
        assert slide["image"]["path"] == "/gen.png"
        assert slide["image"]["left"] == 1.0

    def test_uses_per_slide_model(self, tmp_path):
        slide = {
            "image_prompt": {"prompt": "A cat", "model": "custom-model"},
        }
        with patch("src.images.generate_image", return_value="/gen.png") as mock_gen:
            resolve_image_prompt(slide, str(tmp_path), default_model="default-model")
        assert mock_gen.call_args[1]["model"] == "custom-model"


# ---------------------------------------------------------------------------
# _generate_image_azure
# ---------------------------------------------------------------------------


class TestGenerateImageAzure:
    def test_success_saves_file(self, tmp_path):
        cached_path = str(tmp_path / "test.png")
        import base64
        fake_b64 = base64.b64encode(b"fake image data").decode()
        response_json = {"data": [{"b64_json": fake_b64}]}
        import json

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_json).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("src.images._get_azure_token", return_value="fake_token"), \
             patch("urllib.request.urlopen", return_value=mock_resp):
            result = _generate_image_azure(
                prompt="a cat",
                cached_path=cached_path,
                model="dall-e-3",
                size="1024x1024",
                endpoint="https://acct.openai.azure.com",
                deployment="dall-e-3",
            )
        assert result == cached_path
        assert os.path.isfile(cached_path)

    def test_failure_returns_none(self, tmp_path):
        cached_path = str(tmp_path / "test.png")
        with patch("src.images._get_azure_token", side_effect=Exception("auth failed")):
            result = _generate_image_azure(
                prompt="a cat",
                cached_path=cached_path,
                model="dall-e-3",
                size="1024x1024",
                endpoint="https://acct.openai.azure.com",
                deployment="dall-e-3",
            )
        assert result is None

    def test_network_error_returns_none(self, tmp_path):
        cached_path = str(tmp_path / "test.png")
        with patch("src.images._get_azure_token", return_value="fake_token"), \
             patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = _generate_image_azure(
                prompt="a cat",
                cached_path=cached_path,
                model="dall-e-3",
                size="1024x1024",
                endpoint="https://acct.openai.azure.com",
                deployment="dall-e-3",
            )
        assert result is None
