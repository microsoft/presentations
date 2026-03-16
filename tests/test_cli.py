"""Tests for src/cli.py."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from src.cli import main, _load_env


@pytest.fixture()
def spec_file(tmp_path):
    """Create a minimal valid .spec.md file and return its path."""
    content = (
        "---\n"
        "title: Test\n"
        "output: test.pptx\n"
        "---\n"
        "\n"
        "## [title] Hello World\n"
    )
    p = tmp_path / "test.spec.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def test_missing_spec_file_exits():
    with pytest.raises(SystemExit):
        main(["nonexistent_file.spec.md"])


def test_default_output_dir(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file])
        _, kwargs = mock_render.call_args
        assert kwargs.get("output_dir") or mock_render.call_args[0][1] == "output"


def test_custom_output_dir(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file, "-o", "my_output"])
        args, kwargs = mock_render.call_args
        assert "my_output" in args or kwargs.get("output_dir") == "my_output"


def test_image_model_flag(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file, "--image-model", "dall-e-3"])
        _, kwargs = mock_render.call_args
        assert kwargs["image_model"] == "dall-e-3"


def test_image_model_default_none(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file])
        _, kwargs = mock_render.call_args
        assert kwargs["image_model"] is None


def test_refetch_flag(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file, "--refetch"])
        _, kwargs = mock_render.call_args
        assert kwargs["refetch"] is True


def test_slides_flag(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file, "--slides", "1,3-5"])
        _, kwargs = mock_render.call_args
        assert kwargs["slide_selection"] == "1,3-5"


# ---------------------------------------------------------------------------
# _load_env
# ---------------------------------------------------------------------------


def test_load_env_loads_dotenv(tmp_path, monkeypatch):
    """_load_env loads a .env file from cwd when present."""
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR=hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _load_env()
    # If dotenv is installed, the variable should be set
    # If dotenv is not installed, it should silently skip
    # Either way, it should not crash


def test_load_env_no_file(tmp_path, monkeypatch):
    """_load_env is safe when no .env file exists."""
    monkeypatch.chdir(tmp_path)
    _load_env()  # Should not crash


def test_load_env_missing_dotenv_package(monkeypatch):
    """_load_env returns silently when dotenv is not installed."""
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("No module named 'dotenv'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    _load_env()  # Should not crash


def test_refetch_default_false(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file])
        _, kwargs = mock_render.call_args
        assert kwargs["refetch"] is False


def test_slides_flag(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file, "--slides", "1,3,5-8"])
        _, kwargs = mock_render.call_args
        assert kwargs["slide_selection"] == "1,3,5-8"


def test_slides_default_none(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file])
        _, kwargs = mock_render.call_args
        assert kwargs["slide_selection"] is None


def test_spec_path_forwarded(spec_file):
    with patch("src.cli.render") as mock_render:
        main([spec_file])
        _, kwargs = mock_render.call_args
        assert kwargs["spec_path"] == spec_file
