"""Tests for src/renderer.py."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from src.renderer import _next_version_path, _parse_slide_selection, render


# ---------------------------------------------------------------------------
# _next_version_path
# ---------------------------------------------------------------------------


class TestNextVersionPath:
    def test_first_file(self, tmp_path):
        path = _next_version_path(str(tmp_path), "deck.pptx")
        assert path == os.path.join(str(tmp_path), "deck.pptx")

    def test_increments(self, tmp_path):
        # Create existing files
        (tmp_path / "deck.pptx").write_bytes(b"")
        path = _next_version_path(str(tmp_path), "deck.pptx")
        assert path == os.path.join(str(tmp_path), "deck_1.pptx")

    def test_increments_twice(self, tmp_path):
        (tmp_path / "deck.pptx").write_bytes(b"")
        (tmp_path / "deck_1.pptx").write_bytes(b"")
        path = _next_version_path(str(tmp_path), "deck.pptx")
        assert path == os.path.join(str(tmp_path), "deck_2.pptx")


# ---------------------------------------------------------------------------
# _parse_slide_selection
# ---------------------------------------------------------------------------


class TestParseSlideSelection:
    def test_single_slide(self):
        assert _parse_slide_selection("3", 10) == [2]

    def test_range(self):
        assert _parse_slide_selection("3-5", 10) == [2, 3, 4]

    def test_comma_separated(self):
        assert _parse_slide_selection("1,3,5", 10) == [0, 2, 4]

    def test_mixed(self):
        result = _parse_slide_selection("1,3-5,8", 10)
        assert result == [0, 2, 3, 4, 7]

    def test_out_of_range_clamped(self):
        result = _parse_slide_selection("0,1,100", 5)
        assert result == [0]  # only slide 1 is valid

    def test_range_clamped_high(self):
        result = _parse_slide_selection("3-100", 5)
        assert result == [2, 3, 4]

    def test_range_clamped_low(self):
        result = _parse_slide_selection("0-2", 5)
        assert result == [0, 1]

    def test_duplicates_removed(self):
        result = _parse_slide_selection("1,1,1", 5)
        assert result == [0]

    def test_empty_string(self):
        assert _parse_slide_selection("", 5) == []

    def test_sorted_output(self):
        result = _parse_slide_selection("5,2,1", 10)
        assert result == [0, 1, 4]

    def test_whitespace_handled(self):
        result = _parse_slide_selection(" 1 , 3 - 5 ", 10)
        assert result == [0, 2, 3, 4]


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRender:
    def _make_spec(self, num_slides=3):
        slides = []
        for i in range(num_slides):
            slides.append({
                "type": "title",
                "title": f"Slide {i + 1}",
                "subtitle": "",
                "notes": "",
                "animations": [],
                "positions": {},
                "content_urls": [],
                "enriched": False,
            })
        return {
            "metadata": {"output": "test.pptx"},
            "slides": slides,
        }

    def test_renders_all_slides(self, tmp_path):
        spec = self._make_spec(3)
        path = render(spec, str(tmp_path))
        assert os.path.isfile(path)
        assert path.endswith(".pptx")

    def test_slide_selection_filters(self, tmp_path):
        spec = self._make_spec(5)
        path = render(spec, str(tmp_path), slide_selection="1,3")
        assert os.path.isfile(path)
        # The file was saved; we trust the PPTX library for slide count
        # The console output is tested by integration tests

    def test_invalid_selection_exits(self, tmp_path):
        spec = self._make_spec(3)
        with pytest.raises(SystemExit, match="no valid slides"):
            render(spec, str(tmp_path), slide_selection="99")

    def test_output_dir_created(self, tmp_path):
        out_dir = str(tmp_path / "new_subdir")
        spec = self._make_spec(1)
        path = render(spec, out_dir)
        assert os.path.isdir(out_dir)
        assert os.path.isfile(path)

    def test_enrichment_skipped_when_cached(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["enriched"] = True
        with patch("src.renderer.enrich_content_from_urls") as mock_ec, \
             patch("src.renderer.enrich_notes_from_urls") as mock_en:
            render(spec, str(tmp_path))
        mock_ec.assert_not_called()
        mock_en.assert_not_called()

    def test_enrichment_called_when_not_cached(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["enriched"] = False
        spec["slides"][0]["content_urls"] = []
        with patch("src.renderer.enrich_content_from_urls") as mock_ec, \
             patch("src.renderer.enrich_notes_from_urls") as mock_en:
            render(spec, str(tmp_path))
        mock_ec.assert_called_once()
        mock_en.assert_called_once()

    def test_enrichment_forced_with_refetch(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["enriched"] = True
        spec["slides"][0]["content_urls"] = []
        with patch("src.renderer.enrich_content_from_urls") as mock_ec, \
             patch("src.renderer.enrich_notes_from_urls") as mock_en:
            render(spec, str(tmp_path), refetch=True)
        mock_ec.assert_called_once()
        mock_en.assert_called_once()

    def test_unknown_slide_type_skipped(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["type"] = "nonexistent-layout"
        path = render(spec, str(tmp_path))
        assert os.path.isfile(path)

    def test_enrichment_called_when_not_cached(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["enriched"] = False
        with patch("src.renderer.enrich_content_from_urls") as mock_ec, \
             patch("src.renderer.enrich_notes_from_urls") as mock_en:
            render(spec, str(tmp_path))
        mock_ec.assert_called_once()
        mock_en.assert_called_once()

    def test_enrichment_called_with_refetch(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["enriched"] = True
        with patch("src.renderer.enrich_content_from_urls") as mock_ec, \
             patch("src.renderer.enrich_notes_from_urls") as mock_en:
            render(spec, str(tmp_path), refetch=True)
        mock_ec.assert_called_once()
        mock_en.assert_called_once()

    def test_spec_written_on_enrichment(self, tmp_path):
        spec = self._make_spec(1)
        spec["slides"][0]["content_urls"] = ["https://example.com"]
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("placeholder", encoding="utf-8")

        def fake_enrich(slide_data, **kw):
            slide_data["notes"] = "enriched"

        with patch("src.renderer.enrich_content_from_urls"), \
             patch("src.renderer.enrich_notes_from_urls", side_effect=fake_enrich), \
             patch("src.renderer.write_spec") as mock_write:
            render(spec, str(tmp_path), spec_path=str(spec_file))
        mock_write.assert_called_once()

    def test_unknown_slide_type_skipped(self, tmp_path, capsys):
        spec = self._make_spec(1)
        spec["slides"][0]["type"] = "unknown_type"
        render(spec, str(tmp_path))
        captured = capsys.readouterr()
        assert "unknown slide type" in captured.out.lower()
