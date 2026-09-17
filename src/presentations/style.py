"""Style resolution: reads font sizes from spec front-matter ``style`` block."""

from pptx.util import Pt

# Fallback defaults (used when spec omits a value)
_DEFAULTS = {
    "title_font_size": 36,
    "subtitle_font_size": 20,
    "body_font_size": 20,
    "heading_font_size": 32,
    "column_heading_font_size": 22,
    "column_body_font_size": 18,
    "badge_width": 0.9,
    "badge_height": 1.1,
    "badge_font_size": 11,
    "badge_corner_radius": 12000,
    "badge_gradient_start": "#E3008C",
    "badge_gradient_end": "#6B2FA0",
    "badge_text_color": "#FFFFFF",
    "box_background": "#E8E8E8",
    "box_border_color": "#5B5FC7",
    "box_corner_radius": 5000,
    "left_column_background": "",
    "right_column_background": "",
    "column_box_border_color": "",
    "column_box_corner_radius": 5000,
    "column_box_padding": 0.15,
    "content_background": "",
    "content_box_corner_radius": 5000,
    "content_box_padding": 0.15,
    "slide_background": "#FFFFFF",
    "title_color": "",
    "title_font_name": "",
    "body_font_name": "",
    "body_color": "",
    "title_accent_color": "",
    "title_accent_height": 0.045,
    "title_accent_width": 1.6,
    "divider_color": "#D0D0D0",
    "name_color": "#000000",
    "name_font_size": 14,
    "url_color": "#0078D4",
    "url_font_size": 14,
    "subtitle_colors": "",
}


class Style:
    """Immutable bag of resolved font sizes (as ``Pt`` values)."""

    def __init__(self, spec_style: dict | None = None):
        t = {**_DEFAULTS, **(spec_style or {})}
        self.title_font = Pt(int(t["title_font_size"]))
        self.subtitle_font = Pt(int(t["subtitle_font_size"]))
        self.body_font = Pt(int(t["body_font_size"]))
        self.heading_font = Pt(int(t["heading_font_size"]))
        self.col_heading_font = Pt(int(t["column_heading_font_size"]))
        self.col_body_font = Pt(int(t["column_body_font_size"]))
        # Resource-box properties (stored as raw values, not Pt)
        self.badge_width = float(t["badge_width"])
        self.badge_height = float(t["badge_height"])
        self.badge_font_size = int(t["badge_font_size"])
        self.badge_corner_radius = int(t["badge_corner_radius"])
        self.badge_gradient_start = str(t["badge_gradient_start"])
        self.badge_gradient_end = str(t["badge_gradient_end"])
        self.badge_text_color = str(t["badge_text_color"])
        self.box_background = str(t["box_background"])
        self.box_border_color = str(t["box_border_color"])
        self.box_corner_radius = int(t["box_corner_radius"])
        self.left_column_background = str(t["left_column_background"])
        self.right_column_background = str(t["right_column_background"])
        self.column_box_border_color = str(t["column_box_border_color"])
        self.column_box_corner_radius = int(t["column_box_corner_radius"])
        self.column_box_padding = float(t["column_box_padding"])
        self.content_background = str(t["content_background"])
        self.content_box_corner_radius = int(t["content_box_corner_radius"])
        self.content_box_padding = float(t["content_box_padding"])
        self.slide_background = str(t["slide_background"])
        self.title_color = str(t["title_color"])
        self.title_font_name = str(t["title_font_name"])
        self.body_font_name = str(t["body_font_name"])
        self.body_color = str(t["body_color"])
        self.title_accent_color = str(t["title_accent_color"])
        self.title_accent_height = float(t["title_accent_height"])
        self.title_accent_width = float(t["title_accent_width"])
        self.divider_color = str(t["divider_color"])
        self.name_color = str(t["name_color"])
        self.name_font_size = int(t["name_font_size"])
        self.url_color = str(t["url_color"])
        self.url_font_size = int(t["url_font_size"])
        self.subtitle_colors = str(t["subtitle_colors"])
