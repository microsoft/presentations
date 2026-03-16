"""Tests for src/spec_writer.py."""

from __future__ import annotations

import textwrap

import pytest

from src.spec_writer import write_spec, _serialize_slide


# ---------------------------------------------------------------------------
# _serialize_slide
# ---------------------------------------------------------------------------


class TestSerializeSlide:
    def test_title_slide(self):
        slide = {
            "type": "title",
            "title": "Welcome",
            "subtitle": "Intro",
            "notes": "Say hello",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "## [title] Welcome" in text
        assert "**Subtitle**: Intro" in text
        assert "**Notes**: Say hello" in text

    def test_content_slide_with_bullets(self):
        slide = {
            "type": "content",
            "title": "Topics",
            "bullets": ["Alpha", "Beta"],
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "- Alpha" in text
        assert "- Beta" in text

    def test_two_column_slide(self):
        slide = {
            "type": "two-column",
            "title": "Compare",
            "left_bullets": ["L1"],
            "right_bullets": ["R1"],
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**Left**:" in text
        assert "- L1" in text
        assert "**Right**:" in text
        assert "- R1" in text

    def test_image_serialized(self):
        slide = {
            "type": "content",
            "title": "Pic",
            "bullets": [],
            "image": {"path": "img.png", "left": 1.0, "top": 2.0, "width": 3.0, "height": 4.0},
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**Image**: img.png, 1.0, 2.0, 3.0, 4.0" in text

    def test_image_prompt_serialized(self):
        slide = {
            "type": "content",
            "title": "AI",
            "bullets": [],
            "image_prompt": {"prompt": "A cat", "left": 5.0, "top": 1.0},
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**ImagePrompt**: A cat, 5.0, 1.0" in text

    def test_image_prompt_with_model(self):
        slide = {
            "type": "content",
            "title": "AI",
            "bullets": [],
            "image_prompt": {"prompt": "A dog", "model": "dall-e-3"},
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**ImageModel**: dall-e-3" in text

    def test_animations_serialized(self):
        slide = {
            "type": "content",
            "title": "Anim",
            "bullets": [],
            "animations": [{"target": "title", "effect": "fade"}],
            "notes": "",
            "positions": {},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**Animation**: title > fade" in text

    def test_content_urls_serialized(self):
        slide = {
            "type": "content",
            "title": "Urls",
            "bullets": [],
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": ["https://example.com"],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**ContentUrls**:" in text
        assert "- https://example.com" in text

    def test_enriched_flag(self):
        slide = {
            "type": "content",
            "title": "E",
            "bullets": [],
            "notes": "",
            "animations": [],
            "positions": {},
            "content_urls": [],
            "enriched": True,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**Enriched**: true" in text

    def test_positions_serialized(self):
        slide = {
            "type": "title",
            "title": "Pos",
            "subtitle": "",
            "notes": "",
            "animations": [],
            "positions": {"title": {"left": 0.5, "top": 2.0, "width": 5.0, "height": 1.5}},
            "content_urls": [],
            "enriched": False,
        }
        lines = _serialize_slide(slide)
        text = "\n".join(lines)
        assert "**TitlePos**: 0.5, 2.0, 5.0, 1.5" in text


# ---------------------------------------------------------------------------
# write_spec – round-trip
# ---------------------------------------------------------------------------


class TestWriteSpec:
    def test_round_trip(self, tmp_path):
        spec = {
            "metadata": {"title": "Round Trip", "output": "out.pptx"},
            "slides": [
                {
                    "type": "title",
                    "title": "Hello",
                    "subtitle": "World",
                    "notes": "Test notes",
                    "animations": [],
                    "positions": {},
                    "content_urls": [],
                    "enriched": False,
                },
                {
                    "type": "content",
                    "title": "Bullets",
                    "bullets": ["A", "B"],
                    "notes": "",
                    "animations": [{"target": "content", "effect": "appear"}],
                    "positions": {},
                    "content_urls": [],
                    "enriched": False,
                },
            ],
        }
        out = tmp_path / "out.spec.md"
        write_spec(spec, str(out))
        text = out.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "title: Round Trip" in text
        assert "## [title] Hello" in text
        assert "## [content] Bullets" in text
        assert "- A" in text
        assert text.endswith("\n")

    def test_trailing_newline(self, tmp_path):
        spec = {
            "metadata": {"title": "T"},
            "slides": [
                {
                    "type": "title",
                    "title": "X",
                    "subtitle": "",
                    "notes": "",
                    "animations": [],
                    "positions": {},
                    "content_urls": [],
                    "enriched": False,
                },
            ],
        }
        out = tmp_path / "t.spec.md"
        write_spec(spec, str(out))
        assert out.read_text(encoding="utf-8").endswith("\n")

    def test_slide_separator(self, tmp_path):
        spec = {
            "metadata": {"title": "T"},
            "slides": [
                {"type": "title", "title": "A", "subtitle": "", "notes": "",
                 "animations": [], "positions": {}, "content_urls": [], "enriched": False},
                {"type": "title", "title": "B", "subtitle": "", "notes": "",
                 "animations": [], "positions": {}, "content_urls": [], "enriched": False},
            ],
        }
        out = tmp_path / "sep.spec.md"
        write_spec(spec, str(out))
        text = out.read_text(encoding="utf-8")
        # Slides separated by "---" (not the front-matter delimiter)
        body = text.split("---", 2)[2]  # skip front-matter open/close
        assert "---" in body
