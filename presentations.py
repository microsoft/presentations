"""Presentation generator – thin wrapper around the ``src`` package.

Usage:
    python presentation.py <spec-file>

Example:
    python presentation.py .speckit/specifications/ai_productivity_boost.spec.md

For the full implementation see the ``src/`` package.
"""

from src.cli import main

if __name__ == "__main__":
    main()
