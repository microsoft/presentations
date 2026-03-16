"""Tests for src/style.py."""

from __future__ import annotations

from pptx.util import Pt

from src.style import Style, _DEFAULTS


class TestStyleDefaults:
    def test_default_title_font(self):
        s = Style()
        assert s.title_font == Pt(36)

    def test_default_body_font(self):
        s = Style()
        assert s.body_font == Pt(20)

    def test_default_heading_font(self):
        s = Style()
        assert s.heading_font == Pt(32)

    def test_default_col_heading_font(self):
        s = Style()
        assert s.col_heading_font == Pt(22)

    def test_default_col_body_font(self):
        s = Style()
        assert s.col_body_font == Pt(18)

    def test_default_badge_properties(self):
        s = Style()
        assert s.badge_width == 0.9
        assert s.badge_height == 1.1
        assert s.badge_font_size == 11

    def test_default_color_strings(self):
        s = Style()
        assert s.badge_gradient_start == "#E3008C"
        assert s.box_border_color == "#5B5FC7"
        assert s.url_color == "#0078D4"


class TestStyleOverrides:
    def test_custom_title_font(self):
        s = Style({"title_font_size": 48})
        assert s.title_font == Pt(48)

    def test_custom_body_font(self):
        s = Style({"body_font_size": 16})
        assert s.body_font == Pt(16)

    def test_partial_override_keeps_defaults(self):
        s = Style({"title_font_size": 48})
        # Other values should remain at default
        assert s.body_font == Pt(20)
        assert s.heading_font == Pt(32)

    def test_none_spec_uses_defaults(self):
        s = Style(None)
        assert s.title_font == Pt(36)

    def test_empty_dict_uses_defaults(self):
        s = Style({})
        assert s.title_font == Pt(36)

    def test_custom_badge_properties(self):
        s = Style({"badge_width": 1.5, "badge_height": 2.0, "badge_font_size": 14})
        assert s.badge_width == 1.5
        assert s.badge_height == 2.0
        assert s.badge_font_size == 14

    def test_custom_colors(self):
        s = Style({"badge_gradient_start": "#FF0000", "url_color": "#00FF00"})
        assert s.badge_gradient_start == "#FF0000"
        assert s.url_color == "#00FF00"


class TestDefaultsDict:
    def test_all_expected_keys_present(self):
        expected_keys = {
            "title_font_size", "subtitle_font_size", "body_font_size",
            "heading_font_size", "column_heading_font_size", "column_body_font_size",
            "badge_width", "badge_height", "badge_font_size", "badge_corner_radius",
            "badge_gradient_start", "badge_gradient_end", "badge_text_color",
            "box_background", "box_border_color", "box_corner_radius",
            "slide_background", "divider_color", "name_color",
            "name_font_size", "url_color", "url_font_size", "subtitle_colors",
        }
        assert expected_keys == set(_DEFAULTS.keys())
