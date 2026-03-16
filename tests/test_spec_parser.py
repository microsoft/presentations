"""Tests for src/spec_parser.py."""

from __future__ import annotations

import os
import textwrap

import pytest

from src.spec_parser import (
    parse_spec,
    _extract_bullets,
    _parse_animations,
    _parse_content_urls,
    _parse_image_field,
    _parse_image_prompt_field,
    _parse_position_field,
    _parse_positions,
    _parse_slide,
    _parse_two_column,
    _parse_resource_boxes,
    _parse_slide_style,
    _strip_directives,
    _dedupe_bullets,
)


@pytest.fixture()
def spec_path(tmp_path):
    """Write a spec file and return its path."""
    def _write(content: str) -> str:
        p = tmp_path / "test.spec.md"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return str(p)
    return _write


# ---------------------------------------------------------------------------
# parse_spec – top-level
# ---------------------------------------------------------------------------


class TestParseSpec:
    def test_metadata_parsed(self, spec_path):
        path = spec_path("""\
            ---
            title: My Deck
            output: deck.pptx
            ---

            ## [title] Hello
        """)
        spec = parse_spec(path)
        assert spec["metadata"]["title"] == "My Deck"
        assert spec["metadata"]["output"] == "deck.pptx"

    def test_slides_parsed(self, spec_path):
        path = spec_path("""\
            ---
            title: T
            ---

            ## [title] Slide One

            ---

            ## [content] Slide Two

            - Bullet A
        """)
        spec = parse_spec(path)
        assert len(spec["slides"]) == 2
        assert spec["slides"][0]["type"] == "title"
        assert spec["slides"][1]["type"] == "content"

    def test_missing_front_matter_exits(self, spec_path):
        path = spec_path("## [title] No front matter")
        with pytest.raises(SystemExit):
            parse_spec(path)

    def test_empty_body_gives_no_slides(self, spec_path):
        path = spec_path("""\
            ---
            title: Empty
            ---
        """)
        spec = parse_spec(path)
        assert spec["slides"] == []


# ---------------------------------------------------------------------------
# _parse_slide
# ---------------------------------------------------------------------------


class TestParseSlide:
    def test_title_slide(self):
        raw = "## [title] Welcome\n\n**Subtitle**: Hello World"
        slide = _parse_slide(raw)
        assert slide["type"] == "title"
        assert slide["title"] == "Welcome"
        assert slide["subtitle"] == "Hello World"

    def test_content_slide_with_bullets(self):
        raw = "## [content] Topics\n\n- Alpha\n- Beta\n- Gamma"
        slide = _parse_slide(raw)
        assert slide["type"] == "content"
        assert slide["bullets"] == ["Alpha", "Beta", "Gamma"]

    def test_section_header(self):
        raw = "## [section-header] Break\n\n**Subtitle**: Interlude"
        slide = _parse_slide(raw)
        assert slide["type"] == "section-header"
        assert slide["subtitle"] == "Interlude"

    def test_two_column(self):
        raw = (
            "## [two-column] Compare\n\n"
            "**Left**:\n- A\n- B\n\n"
            "**Right**:\n- C\n- D"
        )
        slide = _parse_slide(raw)
        assert slide["type"] == "two-column"
        assert slide["left_bullets"] == ["A", "B"]
        assert slide["right_bullets"] == ["C", "D"]

    def test_notes_extracted(self):
        raw = "## [content] Noted\n\n- Bullet\n\n**Notes**: Some speaker notes here."
        slide = _parse_slide(raw)
        assert slide["notes"] == "Some speaker notes here."

    def test_no_header_returns_none(self):
        assert _parse_slide("Just some text") is None

    def test_enriched_flag_parsed(self):
        raw = "## [content] E\n\n- X\n\n**Enriched**: true"
        slide = _parse_slide(raw)
        assert slide["enriched"] is True

    def test_enriched_flag_absent(self):
        raw = "## [content] E\n\n- X"
        slide = _parse_slide(raw)
        assert slide["enriched"] is False


# ---------------------------------------------------------------------------
# _extract_bullets
# ---------------------------------------------------------------------------


class TestExtractBullets:
    def test_dash_bullets(self):
        assert _extract_bullets("- A\n- B") == ["A", "B"]

    def test_asterisk_bullets(self):
        assert _extract_bullets("* A\n* B") == ["A", "B"]

    def test_mixed(self):
        assert _extract_bullets("- A\n* B\n- C") == ["A", "B", "C"]

    def test_empty(self):
        assert _extract_bullets("no bullets here") == []


# ---------------------------------------------------------------------------
# _parse_image_field
# ---------------------------------------------------------------------------


class TestParseImageField:
    def test_full_coords(self):
        text = "**Image**: images/pic.png, 1.0, 2.0, 3.0, 4.0"
        img = _parse_image_field(text)
        assert img["path"] == "images/pic.png"
        assert img["left"] == 1.0
        assert img["top"] == 2.0
        assert img["width"] == 3.0
        assert img["height"] == 4.0

    def test_path_only(self):
        img = _parse_image_field("**Image**: photo.png")
        assert img["path"] == "photo.png"
        assert "left" not in img

    def test_partial_coords(self):
        img = _parse_image_field("**Image**: x.png, 5.0, 6.0")
        assert img["left"] == 5.0
        assert img["top"] == 6.0
        assert "width" not in img

    def test_no_image(self):
        assert _parse_image_field("no image directive") is None


# ---------------------------------------------------------------------------
# _parse_image_prompt_field
# ---------------------------------------------------------------------------


class TestParseImagePromptField:
    def test_prompt_with_coords(self):
        text = "**ImagePrompt**: A sunset over mountains, 6.5, 1.5, 3.0, 3.0"
        ip = _parse_image_prompt_field(text)
        assert ip["prompt"] == "A sunset over mountains"
        assert ip["left"] == 6.5
        assert ip["width"] == 3.0

    def test_prompt_only(self):
        ip = _parse_image_prompt_field("**ImagePrompt**: A cat sitting on a roof")
        assert ip["prompt"] == "A cat sitting on a roof"
        assert "left" not in ip

    def test_prompt_with_model_override(self):
        text = "**ImagePrompt**: A car\n**ImageModel**: dall-e-3"
        ip = _parse_image_prompt_field(text)
        assert ip["model"] == "dall-e-3"

    def test_no_prompt(self):
        assert _parse_image_prompt_field("nothing here") is None


# ---------------------------------------------------------------------------
# _parse_animations
# ---------------------------------------------------------------------------


class TestParseAnimations:
    def test_target_and_effect(self):
        text = "**Animation**: title > fade"
        anims = _parse_animations(text)
        assert len(anims) == 1
        assert anims[0]["target"] == "title"
        assert anims[0]["effect"] == "fade"

    def test_no_target_defaults_all(self):
        text = "**Animation**: appear"
        anims = _parse_animations(text)
        assert anims[0]["target"] == "all"
        assert anims[0]["effect"] == "appear"

    def test_multiple_animations(self):
        text = "**Animation**: title > fade\n**Animation**: content > fly-in"
        anims = _parse_animations(text)
        assert len(anims) == 2

    def test_no_animations(self):
        assert _parse_animations("plain text") == []


# ---------------------------------------------------------------------------
# _parse_position_field / _parse_positions
# ---------------------------------------------------------------------------


class TestParsePositions:
    def test_full_position(self):
        text = "**TitlePos**: 0.5, 2.0, 5.0, 1.5"
        pos = _parse_position_field(text, "Title")
        assert pos == {"left": 0.5, "top": 2.0, "width": 5.0, "height": 1.5}

    def test_partial_position(self):
        pos = _parse_position_field("**ContentPos**: 1.0, 2.0", "Content")
        assert pos == {"left": 1.0, "top": 2.0}

    def test_missing_position(self):
        assert _parse_position_field("nothing", "Title") is None


# ---------------------------------------------------------------------------
# _strip_directives
# ---------------------------------------------------------------------------


class TestStripDirectives:
    def test_removes_image_directive(self):
        text = "- Bullet one\n**Image**: img.png, 1.0, 2.0\n- Bullet two"
        result = _strip_directives(text)
        assert "Bullet one" in result
        assert "Bullet two" in result
        assert "**Image**" not in result

    def test_removes_animation_directive(self):
        text = "- A\n**Animation**: title > fade\n- B"
        result = _strip_directives(text)
        assert "**Animation**" not in result
        assert "A" in result
        assert "B" in result

    def test_removes_content_urls_section(self):
        text = "- Bullet\n**ContentUrls**:\n- https://example.com\n- https://other.com"
        result = _strip_directives(text)
        assert "**ContentUrls**" not in result
        assert "Bullet" in result

    def test_removes_supplemental_section(self):
        text = "- Bullet\n\n--- Supplemental (from ContentUrls) ---\n\n- Extra info"
        result = _strip_directives(text)
        assert "Bullet" in result
        assert "Supplemental" not in result

    def test_removes_enriched_directive(self):
        text = "- A\n**Enriched**: true\n- B"
        result = _strip_directives(text)
        assert "**Enriched**" not in result

    def test_removes_bare_url_bullets(self):
        text = "- Real bullet\n- https://example.com\n- Another bullet"
        result = _strip_directives(text)
        assert "Real bullet" in result
        assert "Another bullet" in result

    def test_preserves_plain_bullets(self):
        text = "- One\n- Two\n- Three"
        result = _strip_directives(text)
        bullets = _extract_bullets(result)
        assert bullets == ["One", "Two", "Three"]


# ---------------------------------------------------------------------------
# _dedupe_bullets
# ---------------------------------------------------------------------------


class TestDedupeBullets:
    def test_removes_duplicates(self):
        assert _dedupe_bullets(["A", "B", "A", "C"]) == ["A", "B", "C"]

    def test_preserves_order(self):
        assert _dedupe_bullets(["C", "A", "B"]) == ["C", "A", "B"]

    def test_empty_list(self):
        assert _dedupe_bullets([]) == []

    def test_single_item(self):
        assert _dedupe_bullets(["A"]) == ["A"]

    def test_all_duplicates(self):
        assert _dedupe_bullets(["X", "X", "X"]) == ["X"]


# ---------------------------------------------------------------------------
# _parse_content_urls
# ---------------------------------------------------------------------------


class TestParseContentUrls:
    def test_parses_urls(self):
        text = "**ContentUrls**:\n- https://a.com\n- https://b.com"
        urls = _parse_content_urls(text)
        assert urls == ["https://a.com", "https://b.com"]

    def test_no_urls(self):
        assert _parse_content_urls("no urls here") == []

    def test_empty_content_urls(self):
        text = "**ContentUrls**:\n"
        urls = _parse_content_urls(text)
        assert urls == []

    def test_parse_positions_multiple(self):
        text = "**TitlePos**: 0.5, 1.0, 5.0, 1.5\n**ImagePos**: 6.0, 0.5"
        positions = _parse_positions(text)
        assert "title" in positions
        assert "image" in positions
        assert positions["title"]["left"] == 0.5
        assert positions["image"]["left"] == 6.0


# ---------------------------------------------------------------------------
# _parse_content_urls
# ---------------------------------------------------------------------------


class TestParseContentUrls:
    def test_urls_parsed(self):
        text = (
            "**ContentUrls**:\n"
            "- https://example.com/page1\n"
            "- https://example.com/page2\n"
        )
        urls = _parse_content_urls(text)
        assert urls == ["https://example.com/page1", "https://example.com/page2"]

    def test_no_urls(self):
        assert _parse_content_urls("no urls here") == []


# ---------------------------------------------------------------------------
# _parse_two_column
# ---------------------------------------------------------------------------


class TestParseTwoColumn:
    def test_both_columns(self):
        text = "**Left**:\n- A\n- B\n\n**Right**:\n- C\n- D"
        result = _parse_two_column(text)
        assert result["left_bullets"] == ["A", "B"]
        assert result["right_bullets"] == ["C", "D"]

    def test_left_only(self):
        text = "**Left**:\n- A\n- B\n"
        result = _parse_two_column(text)
        assert result["left_bullets"] == ["A", "B"]
        assert result["right_bullets"] == []


# ---------------------------------------------------------------------------
# _parse_resource_boxes
# ---------------------------------------------------------------------------


class TestParseResourceBoxes:
    def test_single_box(self):
        text = "**Box**: Tools\n- Name1 | https://url1.com\n- Name2 | https://url2.com\n"
        boxes = _parse_resource_boxes(text)
        assert len(boxes) == 1
        assert boxes[0]["label"] == "Tools"
        assert len(boxes[0]["rows"]) == 2
        assert boxes[0]["rows"][0]["name"] == "Name1"
        assert boxes[0]["rows"][0]["url"] == "https://url1.com"

    def test_no_url(self):
        text = "**Box**: Misc\n- JustAName\n"
        boxes = _parse_resource_boxes(text)
        assert boxes[0]["rows"][0]["name"] == "JustAName"
        assert boxes[0]["rows"][0]["url"] == ""


# ---------------------------------------------------------------------------
# _parse_slide_style
# ---------------------------------------------------------------------------


class TestParseSlideStyle:
    def test_style_keys(self):
        text = "**SlideBackground**: #000000\n**TitleColor**: #FFFFFF\n**TitleSize**: 40"
        ss = _parse_slide_style(text)
        assert ss["SlideBackground"] == "#000000"
        assert ss["TitleColor"] == "#FFFFFF"
        assert ss["TitleSize"] == "40"

    def test_no_style(self):
        assert _parse_slide_style("nothing") == {}
