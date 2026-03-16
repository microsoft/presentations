"""Spec-file parser: reads a ``.spec.md`` file into metadata + slide list."""

import re
import sys

import yaml


def parse_spec(path: str) -> dict:
    """Parse a presentation spec markdown file into metadata + slide list."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # Split YAML front matter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not fm_match:
        sys.exit("Error: spec file must start with YAML front matter (--- … ---)")
    metadata = yaml.safe_load(fm_match.group(1))
    body = text[fm_match.end():]

    # Split slides on horizontal rules (--- on its own line)
    raw_slides = re.split(r"\n---\s*\n", body)
    slides = []
    for raw in raw_slides:
        raw = raw.strip()
        if not raw:
            continue
        slide = _parse_slide(raw)
        if slide:
            slides.append(slide)

    return {"metadata": metadata, "slides": slides}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_slide(raw: str) -> dict | None:
    """Parse a single slide block into a structured dict."""
    header_match = re.match(r"^##\s+\[(\w[\w-]*)\]\s+(.+)", raw)
    if not header_match:
        return None
    slide_type = header_match.group(1).strip()
    title = header_match.group(2).strip()
    rest = raw[header_match.end():].strip()

    # Extract notes (everything after **Notes**: to end)
    notes = ""
    notes_match = re.split(r"\*\*Notes\*\*\s*:\s*", rest, maxsplit=1)
    if len(notes_match) == 2:
        rest = notes_match[0].strip()
        notes = notes_match[1].strip()

    slide: dict = {"type": slide_type, "title": title, "notes": notes}

    slide["content_urls"] = _parse_content_urls(rest)
    slide["image"] = _parse_image_field(rest)
    slide["image_prompt"] = _parse_image_prompt_field(rest)
    slide["animations"] = _parse_animations(rest)
    slide["positions"] = _parse_positions(rest)
    slide["enriched"] = bool(re.search(r"\*\*Enriched\*\*\s*:\s*true", rest, re.IGNORECASE))

    if slide_type == "title":
        sub_match = re.search(r"\*\*Subtitle\*\*\s*:\s*(.+)", rest)
        slide["subtitle"] = sub_match.group(1).strip() if sub_match else ""

    elif slide_type == "section-header":
        sub_match = re.search(r"\*\*Subtitle\*\*\s*:\s*(.+)", rest)
        slide["subtitle"] = sub_match.group(1).strip() if sub_match else ""

    elif slide_type == "content":
        slide["bullets"] = _dedupe_bullets(_extract_bullets(_strip_directives(rest)))

    elif slide_type == "two-column":
        slide.update(_parse_two_column(rest))

    elif slide_type == "resource-box":
        sub_match = re.search(r"\*\*Subtitle\*\*\s*:\s*(.+)", rest)
        slide["subtitle"] = sub_match.group(1).strip() if sub_match else ""
        slide["boxes"] = _parse_resource_boxes(rest)
        slide["slide_style"] = _parse_slide_style(rest)

    return slide


def _extract_bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^[-*]\s+(.+)", text, re.MULTILINE)]


def _strip_directives(text: str) -> str:
    """Remove directive blocks and metadata lines, leaving only bullet content."""
    text = re.sub(r"\*\*ContentUrls\*\*\s*:\s*\n(?:\s*-\s+\S+\n?)*", "", text)
    text = re.sub(r"---\s+Supplemental\s+\(.*?\)\s+---.*?(?=\n---|$)", "", text, flags=re.DOTALL)
    text = re.sub(
        r"\*\*(?:Image|ImagePrompt|ImageModel|Animation|Enriched|Subtitle)\*\*\s*:\s*.+",
        "", text,
    )
    text = re.sub(r"\*\*\w+Pos\*\*\s*:\s*.+", "", text)
    # Remove bare URL bullet lines (leaked from enrichment)
    text = re.sub(r"^[-*]\s+https?://\S+\s*$", "", text, flags=re.MULTILINE)
    return text


def _dedupe_bullets(bullets: list[str]) -> list[str]:
    """Remove duplicate bullets, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for b in bullets:
        if b not in seen:
            seen.add(b)
            result.append(b)
    return result


def _parse_two_column(text: str) -> dict:
    result: dict = {}
    left_match = re.search(
        r"\*\*Left\*\*\s*:\s*\n(.*?)(?=\*\*Right\*\*|\*\*Notes\*\*|\*\*Image\*\*|\*\*Animation\*\*|$)",
        text, re.DOTALL,
    )
    result["left_bullets"] = _extract_bullets(left_match.group(1)) if left_match else []
    right_match = re.search(
        r"\*\*Right\*\*\s*:\s*\n(.*?)(?=\*\*Notes\*\*|\*\*Image\*\*|\*\*Animation\*\*|$)",
        text, re.DOTALL,
    )
    result["right_bullets"] = _extract_bullets(right_match.group(1)) if right_match else []
    return result


def _parse_slide_style(text: str) -> dict:
    """Parse inline ``**Key**: value`` style directives for resource-box slides."""
    style: dict = {}
    _STYLE_KEYS = [
        "SlideBackground", "TitleColor", "TitleSize",
        "SubtitleSize", "SubtitleColors",
        "BadgeGradientStart", "BadgeGradientEnd", "BadgeTextColor",
        "BadgeWidth", "BadgeHeight", "BadgeFontSize", "BadgeCornerRadius",
        "BoxBorderColor", "BoxBackground", "BoxCornerRadius",
        "OuterBorderColor",
        "UrlColor", "NameFontSize", "UrlFontSize",
        "NameColor", "DividerColor",
    ]
    for key in _STYLE_KEYS:
        m = re.search(rf"\*\*{key}\*\*\s*:\s*(.+)", text)
        if m:
            style[key] = m.group(1).strip()
    return style


def _parse_resource_boxes(text: str) -> list[dict]:
    """Parse ``**Box**: label`` sections followed by ``- name | url`` rows."""
    boxes = []
    for m in re.finditer(
        r"\*\*Box\*\*\s*:\s*(.+?)\n((?:\s*-\s+.+\n?)*)",
        text,
    ):
        label = m.group(1).strip()
        rows = []
        for row_m in re.finditer(r"^\s*-\s+(.+)", m.group(2), re.MULTILINE):
            parts = [p.strip() for p in row_m.group(1).split("|", 1)]
            name = parts[0]
            url = parts[1] if len(parts) > 1 else ""
            rows.append({"name": name, "url": url})
        boxes.append({"label": label, "rows": rows})
    return boxes


def _parse_image_field(text: str) -> dict | None:
    match = re.search(r"\*\*Image\*\*\s*:\s*(.+)", text)
    if not match:
        return None
    raw = match.group(1).strip()
    parts = [p.strip() for p in raw.split(",")]
    img: dict = {"path": parts[0]}
    if len(parts) >= 3:
        img["left"] = float(parts[1])
        img["top"] = float(parts[2])
    if len(parts) >= 5:
        img["width"] = float(parts[3])
        img["height"] = float(parts[4])
    return img


def _parse_image_prompt_field(text: str) -> dict | None:
    """Parse optional **ImagePrompt**: description [, left, top, width, height].

    An optional **ImageModel**: <model-name> line overrides the default model
    for this slide.
    """
    match = re.search(r"\*\*ImagePrompt\*\*\s*:\s*(.+)", text)
    if not match:
        return None
    raw = match.group(1).strip()
    parts = [p.strip() for p in raw.split(",")]
    numeric_tail = []
    for p in reversed(parts):
        try:
            numeric_tail.insert(0, float(p))
        except ValueError:
            break
    desc_parts = parts[: len(parts) - len(numeric_tail)]
    prompt: dict = {"prompt": ", ".join(desc_parts)}
    if len(numeric_tail) >= 2:
        prompt["left"] = numeric_tail[0]
        prompt["top"] = numeric_tail[1]
    if len(numeric_tail) >= 4:
        prompt["width"] = numeric_tail[2]
        prompt["height"] = numeric_tail[3]

    # Per-slide model override
    model_match = re.search(r"\*\*ImageModel\*\*\s*:\s*(\S+)", text)
    if model_match:
        prompt["model"] = model_match.group(1).strip().lower()

    return prompt


def _parse_animations(text: str) -> list[dict]:
    animations = []
    for m in re.finditer(r"\*\*Animation\*\*\s*:\s*(.+)", text):
        raw = m.group(1).strip()
        parts = [p.strip() for p in raw.split(">", 1)]
        if len(parts) == 2:
            target, effect_str = parts
        else:
            target, effect_str = "all", parts[0]
        animations.append({"target": target.lower(), "effect": effect_str.lower().strip()})
    return animations


def _parse_position_field(text: str, field: str) -> dict | None:
    """Parse ``**<field>Pos**: left, top, width, height`` (all in inches)."""
    match = re.search(rf"\*\*{re.escape(field)}Pos\*\*\s*:\s*(.+)", text)
    if not match:
        return None
    raw = match.group(1).strip()
    parts = [p.strip() for p in raw.split(",")]
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    pos: dict = {}
    if len(nums) >= 2:
        pos["left"] = nums[0]
        pos["top"] = nums[1]
    if len(nums) >= 4:
        pos["width"] = nums[2]
        pos["height"] = nums[3]
    return pos if pos else None


def _parse_positions(text: str) -> dict:
    """Parse all ``**<name>Pos**`` directives from the slide block."""
    positions: dict = {}
    for name in ("Title", "Subtitle", "Content", "Left", "Right", "Image"):
        pos = _parse_position_field(text, name)
        if pos:
            positions[name.lower()] = pos
    return positions


def _parse_content_urls(text: str) -> list[str]:
    match = re.search(
        r"\*\*ContentUrls\*\*\s*:\s*\n((?:\s*-\s+\S+\n?)+)", text
    )
    if not match:
        return []
    urls = []
    for line in match.group(1).strip().splitlines():
        url = line.strip().lstrip("- ").strip()
        if url:
            urls.append(url)
    return urls
