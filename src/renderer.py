"""Renderer – orchestrates parsing, enrichment, image generation, and slide building."""

from __future__ import annotations

import os

from pptx import Presentation

from .animations import apply_animations
from .enrichment import enrich_content_from_urls, enrich_notes_from_urls
from .images import resolve_image_prompt
from .slides import SLIDE_BUILDERS
from .spec_writer import write_spec
from .style import Style

# ---------------------------------------------------------------------------
# Versioned output path
# ---------------------------------------------------------------------------


def _next_version_path(output_dir: str, filename: str) -> str:
    """Return a versioned path: ``file.pptx``, ``file_1.pptx``, …"""
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(output_dir, filename)
    n = 1
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{base}_{n}{ext}")
        n += 1
    return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _parse_slide_selection(selection: str, total: int) -> list[int]:
    """Parse a slide selection string into a sorted list of 0-based indices.

    *selection* uses 1-based slide numbers.  Supports single numbers (``5``),
    ranges (``3-7``), and comma-separated combinations (``1,3,5-8``).
    Out-of-range values are silently clamped.
    """
    indices: set[int] = set()
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo = max(1, int(lo_s.strip()))
            hi = min(total, int(hi_s.strip()))
            indices.update(range(lo - 1, hi))  # convert to 0-based
        else:
            n = int(part)
            if 1 <= n <= total:
                indices.add(n - 1)
    return sorted(indices)


def render(
    spec: dict,
    output_dir: str = "output",
    image_model: str | None = None,
    refetch: bool = False,
    spec_path: str | None = None,
    slide_selection: str | None = None,
) -> str:
    """Render a parsed spec into a PowerPoint file and return the output path."""
    metadata = spec["metadata"]
    slides = spec["slides"]
    out_name = metadata.get("output", "presentation.pptx")

    # Filter slides if a selection was provided
    if slide_selection:
        selected = _parse_slide_selection(slide_selection, len(slides))
        if not selected:
            raise SystemExit(f"Error: no valid slides in selection '{slide_selection}' (deck has {len(slides)} slides)")
        slides = [slides[i] for i in selected]
        print(f"Generating {len(slides)} of {len(spec['slides'])} slides (selection: {slide_selection})")

    # Image model priority: CLI flag > front-matter
    default_model = (
        image_model
        or metadata.get("image_model", "").strip().lower()
    )
    if not default_model:
        print(
            "Warning: no image_model specified in front matter or --image-model flag. "
            "ImagePrompt directives will be skipped."
        )

    # Text model for note enrichment: front-matter > env var > default
    text_model = metadata.get("text_model", "").strip()

    # Build Style from front-matter
    style = Style(metadata.get("style"))

    prs = Presentation()

    any_enriched = False

    for slide_data in slides:
        stype = slide_data["type"]
        builder = SLIDE_BUILDERS.get(stype)
        if builder is None:
            print(f"Warning: unknown slide type '{stype}', skipping.")
            continue

        # Skip enrichment if already cached (unless --refetch)
        already_enriched = slide_data.get("enriched", False)
        if already_enriched and not refetch:
            pass  # use cached content
        else:
            # Enrich slide content from ContentUrls before building
            old_bullets = list(slide_data.get("bullets", []))
            old_left = list(slide_data.get("left_bullets", []))
            old_right = list(slide_data.get("right_bullets", []))
            old_notes = slide_data.get("notes", "")

            enrich_content_from_urls(slide_data, text_model=text_model)
            enrich_notes_from_urls(slide_data, text_model=text_model)

            # Detect if enrichment actually changed anything
            new_bullets = slide_data.get("bullets", [])
            new_left = slide_data.get("left_bullets", [])
            new_right = slide_data.get("right_bullets", [])
            new_notes = slide_data.get("notes", "")
            if (new_bullets != old_bullets or new_left != old_left
                    or new_right != old_right or new_notes != old_notes):
                slide_data["enriched"] = True
                any_enriched = True

        # Resolve any ImagePrompt → generate images before building
        had_image = bool(slide_data.get("image"))
        resolve_image_prompt(slide_data, output_dir, default_model=default_model)
        if not had_image and slide_data.get("image"):
            any_enriched = True

        builder(prs, slide_data, style, apply_animations=apply_animations)

    # Write enriched spec back to disk so next run uses cached data
    if any_enriched and spec_path:
        write_spec(spec, spec_path)
        print(f"Saved enriched spec -> {spec_path}")

    os.makedirs(output_dir, exist_ok=True)
    out_path = _next_version_path(output_dir, out_name)
    prs.save(out_path)
    print(f"Saved {len(slides)} slides -> {out_path}")
    return out_path
