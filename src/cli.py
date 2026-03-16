"""CLI entry point for the presentation generator."""

from __future__ import annotations

import argparse
import os
import sys

from .spec_parser import parse_spec
from .renderer import render


def _load_env() -> None:
    """Load a ``.env`` file from the project root if present.

    Searches (in order):
    1. ``<cwd>/.env``
    2. ``<cwd>/.azure/presentations/.env``  (azd environment)
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    cwd = os.getcwd()
    candidates = [
        os.path.join(cwd, ".env"),
        os.path.join(cwd, ".azure", "presentations", ".env"),
    ]
    for env_path in candidates:
        if os.path.isfile(env_path):
            load_dotenv(env_path, override=False)
            print(f"Loaded environment from {env_path}")


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and generate the presentation."""
    _load_env()
    parser = argparse.ArgumentParser(
        description="Generate a PowerPoint presentation from a spec file.",
    )
    parser.add_argument("spec", help="Path to the .spec.md file")
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--image-model",
        default=None,
        help=(
            "Image generation model name. "
            "Overrides the front-matter 'image_model' setting."
        ),
    )
    parser.add_argument(
        "--refetch",
        action="store_true",
        default=False,
        help=(
            "Re-fetch and regenerate all AI enrichments, "
            "even if cached results exist in the spec file."
        ),
    )
    parser.add_argument(
        "--slides",
        default=None,
        help=(
            "Slide numbers to generate (1-indexed). "
            "Examples: '5' (one slide), '3-7' (range), '1,3,5-8' (mixed). "
            "Default: all slides."
        ),
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.spec):
        sys.exit(f"Error: spec file not found: {args.spec}")

    spec = parse_spec(args.spec)
    render(
        spec,
        args.output_dir,
        image_model=args.image_model,
        refetch=args.refetch,
        spec_path=args.spec,
        slide_selection=args.slides,
    )
