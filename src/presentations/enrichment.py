"""ContentUrl fetching & speaker-note enrichment via Azure OpenAI.

Uses :class:`~openai.AzureOpenAI` with
:class:`~azure.identity.DefaultAzureCredential` so no vendor-specific key
(``OPENAI_API_KEY``) is required.
"""

from __future__ import annotations

import html.parser
import os
import re
import urllib.request
from urllib.parse import urlparse


def _get_openai_endpoint() -> str | None:
    """Derive the ``*.openai.azure.com`` endpoint from env vars."""
    account = os.environ.get("AI_PROJECT_NAME", "").strip()
    if account:
        return f"https://{account}.openai.azure.com"
    # Fallback: parse account name from AZURE_AI_PROJECT_ENDPOINT
    raw = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()
    if raw:
        host = urlparse(raw).hostname or ""
        # e.g. mlw-foundry-xxx.services.ai.azure.com -> mlw-foundry-xxx
        account = host.split(".")[0]
        if account:
            return f"https://{account}.openai.azure.com"
    return None

# ---------------------------------------------------------------------------
# HTML → plain-text extractor
# ---------------------------------------------------------------------------


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Strip tags, keep text content only."""

    _skip_tags = frozenset({
        "script", "style", "noscript", "svg", "nav", "footer", "header",
    })

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, _attrs):  # noqa: ANN001
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):  # noqa: ANN001
        if self._skip_depth == 0:
            self._pieces.append(data)

    def get_text(self) -> str:
        return " ".join(self._pieces)


# ---------------------------------------------------------------------------
# URL fetcher
# ---------------------------------------------------------------------------


def _fetch_url_text(url: str, max_chars: int = 6000) -> str:
    """Fetch *url* and return best-effort plain text (truncated)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SpecKit/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        extractor = _HTMLTextExtractor()
        extractor.feed(raw)
        text = extractor.get_text()
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as exc:
        print(f"  Warning: could not fetch {url}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Note enrichment
# ---------------------------------------------------------------------------


def enrich_notes_from_urls(slide_data: dict, text_model: str = "") -> None:
    """Fetch ContentUrls and use Azure AI to synthesise supplemental speaker notes.

    The original notes from the spec are preserved as-is.  If ContentUrls exist
    and an Azure AI endpoint is available, fetched content is sent to a text
    model to generate a supplemental section appended after the original notes.

    *text_model* is the deployment name (from spec ``text_model`` or env var
    ``AZURE_AI_TEXT_MODEL``).  Falls back to ``gpt-4o-mini`` if none is set.
    """
    urls = slide_data.get("content_urls", [])
    if not urls:
        return

    endpoint = _get_openai_endpoint()
    if not endpoint:
        print("  Skipping note enrichment (AI_PROJECT_NAME / AZURE_AI_PROJECT_ENDPOINT not set).")
        return

    # Fetch content from each URL
    fetched_parts: list[str] = []
    for url in urls:
        print(f"  Fetching content: {url}")
        text = _fetch_url_text(url)
        if text:
            fetched_parts.append(f"[Source: {url}]\n{text}")

    if not fetched_parts:
        return

    context_block = "\n\n".join(fetched_parts)
    title = slide_data.get("title", "")
    original_notes = slide_data.get("notes", "")

    prompt = (
        f'You are a presentation coach. A speaker is presenting a slide titled '
        f'"{title}". Their current speaker notes are:\n\n'
        f'{original_notes}\n\n'
        f'Below is reference content fetched from authoritative URLs. '
        f'Using ONLY the reference content, write 2-4 concise supplemental '
        f'bullet points the speaker can use. Each bullet should cite the source '
        f'URL. Do NOT repeat the original notes.\n\n'
        f'Reference content:\n{context_block}'
    )

    notes_model = (
        text_model
        or os.environ.get("AZURE_AI_TEXT_MODEL", "")
        or "gpt-4o-mini"
    )

    try:
        from azure.identity import DefaultAzureCredential
        from openai import AzureOpenAI

        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
            azure_ad_token=token.token,
        )

        print(f"  Enriching notes for: {title}")
        response = client.chat.completions.create(
            model=notes_model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=400,
        )

        supplement = response.choices[0].message.content.strip()
        if supplement:
            slide_data["notes"] = (
                f"{original_notes}\n\n--- Supplemental (from ContentUrls) ---\n\n"
                f"{supplement}"
            )
    except ImportError:
        print(
            "  Warning: 'openai' and 'azure-identity' packages needed for note enrichment. "
            "Install with: pip install openai azure-identity"
        )
    except Exception as exc:
        print(f"  Warning: note enrichment failed: {exc}")


# ---------------------------------------------------------------------------
# Slide content enrichment
# ---------------------------------------------------------------------------


def enrich_content_from_urls(slide_data: dict, text_model: str = "") -> None:
    """Fetch ContentUrls and use Azure AI to enrich slide body content.

    For **content** slides the original bullets are preserved and up to 2
    additional bullets are appended.  For **two-column** slides both columns
    may receive an extra bullet each.  Other slide types are left unchanged.

    *text_model* is the deployment name (from spec ``text_model`` or env var
    ``AZURE_AI_TEXT_MODEL``).  Falls back to ``gpt-4o-mini`` if none is set.
    """
    stype = slide_data.get("type", "")
    if stype not in ("content", "two-column"):
        return

    urls = slide_data.get("content_urls", [])
    if not urls:
        return

    endpoint = _get_openai_endpoint()
    if not endpoint:
        print("  Skipping content enrichment (AI_PROJECT_NAME / AZURE_AI_PROJECT_ENDPOINT not set).")
        return

    # Fetch content from each URL
    fetched_parts: list[str] = []
    for url in urls:
        text = _fetch_url_text(url)
        if text:
            fetched_parts.append(f"[Source: {url}]\n{text}")

    if not fetched_parts:
        return

    context_block = "\n\n".join(fetched_parts)
    title = slide_data.get("title", "")

    content_model = (
        text_model
        or os.environ.get("AZURE_AI_TEXT_MODEL", "")
        or "gpt-4o-mini"
    )

    try:
        from azure.identity import DefaultAzureCredential
        from openai import AzureOpenAI

        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
            azure_ad_token=token.token,
        )

        if stype == "content":
            _enrich_content_bullets(
                client, content_model, slide_data, title, context_block,
            )
        elif stype == "two-column":
            _enrich_two_column_bullets(
                client, content_model, slide_data, title, context_block,
            )

    except ImportError:
        print(
            "  Warning: 'openai' and 'azure-identity' packages needed for content enrichment. "
            "Install with: pip install openai azure-identity"
        )
    except Exception as exc:
        print(f"  Warning: content enrichment failed for '{title}': {exc}")


def _enrich_content_bullets(
    client,
    model: str,
    slide_data: dict,
    title: str,
    context_block: str,
) -> None:
    """Add up to 2 supplemental bullets to a content slide."""
    existing = slide_data.get("bullets", [])
    existing_text = "\n".join(f"- {b}" for b in existing)

    prompt = (
        f'You are a presentation content expert. A slide titled "{title}" '
        f'currently has these bullet points:\n\n{existing_text}\n\n'
        f'Below is reference content fetched from authoritative URLs.\n\n'
        f'Using ONLY the reference content, write 1-2 additional concise '
        f'bullet points that add new, concrete information the audience would '
        f'find valuable. Each bullet must be one sentence (max ~15 words). '
        f'Do NOT repeat or rephrase existing bullets. '
        f'Return ONLY the new bullets as a plain list starting with "- ".\n\n'
        f'Reference content:\n{context_block}'
    )

    print(f"  Enriching content for: {title}")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=200,
    )

    raw = response.choices[0].message.content.strip()
    new_bullets = _extract_ai_bullets(raw, max_bullets=2)
    if new_bullets:
        slide_data["bullets"] = existing + new_bullets
        print(f"    Added {len(new_bullets)} supplemental bullet(s)")


def _enrich_two_column_bullets(
    client,
    model: str,
    slide_data: dict,
    title: str,
    context_block: str,
) -> None:
    """Add up to 1 supplemental bullet per column in a two-column slide."""
    left = slide_data.get("left_bullets", [])
    right = slide_data.get("right_bullets", [])
    left_text = "\n".join(f"- {b}" for b in left)
    right_text = "\n".join(f"- {b}" for b in right)

    prompt = (
        f'You are a presentation content expert. A two-column slide titled '
        f'"{title}" has:\n\n'
        f'LEFT column:\n{left_text}\n\n'
        f'RIGHT column:\n{right_text}\n\n'
        f'Below is reference content fetched from authoritative URLs.\n\n'
        f'Using ONLY the reference content, suggest exactly 1 new bullet for '
        f'each column that adds concrete, non-redundant information. Each '
        f'bullet must be one sentence (max ~15 words). '
        f'Return in this exact format:\n'
        f'LEFT: - <bullet>\n'
        f'RIGHT: - <bullet>\n\n'
        f'Reference content:\n{context_block}'
    )

    print(f"  Enriching two-column content for: {title}")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=150,
    )

    raw = response.choices[0].message.content.strip()
    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("LEFT:"):
            bullet = line.split(":", 1)[1].strip().lstrip("- ").strip()
            if bullet:
                slide_data.setdefault("left_bullets", []).append(bullet)
                print("    Added left-column bullet")
        elif line.upper().startswith("RIGHT:"):
            bullet = line.split(":", 1)[1].strip().lstrip("- ").strip()
            if bullet:
                slide_data.setdefault("right_bullets", []).append(bullet)
                print("    Added right-column bullet")


def _extract_ai_bullets(text: str, max_bullets: int = 2) -> list[str]:
    """Parse bullet lines from AI response text."""
    bullets: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            bullet = line[2:].strip()
            if bullet:
                bullets.append(bullet)
            if len(bullets) >= max_bullets:
                break
    return bullets
