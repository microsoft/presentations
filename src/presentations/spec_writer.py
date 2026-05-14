"""Serialize an enriched spec dict back to ``.spec.md`` format."""

from __future__ import annotations

import yaml


def write_spec(spec: dict, path: str) -> None:
    """Write the spec (metadata + slides) back to *path* as ``.spec.md``."""
    lines: list[str] = []

    # --- YAML front matter ---
    lines.append("---")
    fm = yaml.dump(spec["metadata"], default_flow_style=False, sort_keys=False).rstrip()
    lines.append(fm)
    lines.append("---")
    lines.append("")

    for i, slide in enumerate(spec["slides"]):
        lines.extend(_serialize_slide(slide))
        if i < len(spec["slides"]) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")

    # Ensure trailing newline
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _serialize_slide(slide: dict) -> list[str]:
    """Serialize a single slide dict into markdown lines."""
    lines: list[str] = []
    stype = slide["type"]
    title = slide["title"]

    lines.append(f"## [{stype}] {title}")
    lines.append("")

    # Subtitle (title / section-header slides)
    if "subtitle" in slide and slide["subtitle"]:
        lines.append(f"**Subtitle**: {slide['subtitle']}")
        lines.append("")

    # Position directives
    pos_map = slide.get("positions", {})
    name_order = ["title", "subtitle", "content", "left", "right", "image"]
    for name in name_order:
        pos = pos_map.get(name)
        if pos:
            vals = []
            if "left" in pos:
                vals.append(str(pos["left"]))
            if "top" in pos:
                vals.append(str(pos["top"]))
            if "width" in pos:
                vals.append(str(pos["width"]))
            if "height" in pos:
                vals.append(str(pos["height"]))
            cap = name.capitalize()
            lines.append(f"**{cap}Pos**: {', '.join(vals)}")

    if pos_map:
        lines.append("")

    # Two-column content
    if stype == "two-column":
        left = slide.get("left_bullets", [])
        right = slide.get("right_bullets", [])
        if left:
            lines.append("**Left**:")
            for b in left:
                lines.append(f"- {b}")
            lines.append("")
        if right:
            lines.append("**Right**:")
            for b in right:
                lines.append(f"- {b}")
            lines.append("")

    # Regular bullets (content slides)
    elif stype == "content":
        bullets = slide.get("bullets", [])
        if bullets:
            for b in bullets:
                lines.append(f"- {b}")
            lines.append("")

    # Resource-box content
    elif stype == "resource-box":
        ss = slide.get("slide_style", {})
        for key, val in ss.items():
            lines.append(f"**{key}**: {val}")
        if ss:
            lines.append("")
        for box in slide.get("boxes", []):
            lines.append(f"**Box**: {box['label']}")
            for row in box.get("rows", []):
                if row.get("url"):
                    lines.append(f"- {row['name']} | {row['url']}")
                else:
                    lines.append(f"- {row['name']}")
            lines.append("")

    # Image
    img = slide.get("image")
    if img:
        parts = [img["path"]]
        for k in ("left", "top", "width", "height"):
            if k in img:
                parts.append(str(img[k]))
        lines.append(f"**Image**: {', '.join(parts)}")

    # ImagePrompt
    ip = slide.get("image_prompt")
    if ip:
        parts = [ip["prompt"]]
        for k in ("left", "top", "width", "height"):
            if k in ip:
                parts.append(str(ip[k]))
        lines.append(f"**ImagePrompt**: {', '.join(parts)}")
        if "model" in ip:
            lines.append(f"**ImageModel**: {ip['model']}")

    # Animations
    for anim in slide.get("animations", []):
        target = anim["target"]
        effect = anim["effect"]
        lines.append(f"**Animation**: {target} > {effect}")

    # ContentUrls
    urls = slide.get("content_urls", [])
    if urls:
        lines.append("")
        lines.append("**ContentUrls**:")
        for url in urls:
            lines.append(f"- {url}")

    # Enriched flag
    if slide.get("enriched"):
        lines.append("")
        lines.append("**Enriched**: true")

    # Notes
    notes = slide.get("notes", "")
    if notes:
        lines.append("")
        lines.append(f"**Notes**: {notes}")

    return lines
