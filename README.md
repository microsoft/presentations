# Presentation Generator

Reads a `.spec.md` file and produces a PowerPoint deck with animations, images, AI-generated visuals, and AI-enriched speaker notes.  

## Problem Statement

Building presentations is one of the most time-consuming tasks in technical communication. Teams spend hours manually crafting slides, sourcing visuals, writing speaker notes, and ensuring consistent formatting — work that is repetitive, error-prone, and disconnected from the source content. Existing tools offer either full manual control (PowerPoint) or rigid templates with little flexibility.

Key pain points this project addresses:

- **Slow iteration cycles** — updating a deck means re-editing dozens of slides by hand, making it hard to keep presentations in sync with fast-moving content.
- **Inconsistent quality** — without a repeatable process, slide design, animations, and speaker notes vary across authors and revisions.
- **No content-as-code workflow** — presentations are opaque binary files that don't fit into version control, code review, or CI/CD pipelines.
- **Manual image creation** — sourcing or designing visuals for every slide is a bottleneck, especially for technical topics where good diagrams are scarce.
- **Shallow speaker notes** — authors rarely have time to research and write thorough notes, leaving presenters underprepared.

This tool solves these problems by treating presentations as **code**: a simple Markdown spec file drives the entire build, AI generates visuals and enriches notes from reference URLs, and every run produces a versioned `.pptx` — reproducible, diffable, and fully automated.

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **pip** — included with Python; used to install dependencies
- **Azure Developer CLI (`azd`)** — required for provisioning Azure infrastructure ([Install](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd))
- **Azure CLI (`az`)** — run `az login` so `DefaultAzureCredential` can authenticate ([Install](https://learn.microsoft.com/cli/azure/install-azure-cli))
- **Azure AI Foundry resources** — run `azd up` from the `infra/` directory to provision the AI project endpoint, model deployments, and Bing Grounding connection (see [Azure Infrastructure](#azure-infrastructure))

## Quick Start

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python presentations.py .speckit/specifications/ai101.spec.md
```

```copilot
activate .venv and execute presentations.py
```

## Project Structure

```
presentations.py          # thin wrapper – delegates to src/
src/
├── __init__.py           # package exports (main, render, parse_spec)
├── cli.py                # argparse CLI entry point
├── spec_parser.py        # .spec.md → metadata + slide list
├── style.py              # Style class (font sizes from front-matter)
├── slides.py             # slide builder functions (one per layout)
├── animations.py         # Open XML animation engine
├── images.py             # image generation via Azure AI REST endpoint
├── enrichment.py         # ContentUrl fetching & note enrichment via Azure 
└── renderer.py           # orchestrates parsing → enrichment → images → 
tests/
├── test_animations.py    # animation XML verification
├── test_cli.py           # CLI argument parsing & entry point
├── test_enrichment.py    # ContentUrl fetching & note enrichment
├── test_images.py        # image generation & caching
├── test_renderer.py      # end-to-end render pipeline
├── test_slides.py        # slide builder functions
├── test_spec_parser.py   # .spec.md parsing
├── test_spec_writer.py   # spec round-trip writing
└── test_style.py         # Style resolution from front-matter
```

## Features

- **Slide types**: `title`, `content`, `section-header`, `two-column`, `resource-box`
- **Animations**: appear, fade, fly-in, fly-in-left, fly-in-right, fly-in-top, wipe, zoom, float-in, split, blinds — applied per-shape via `**Animation**` directives
- **Static images**: reference local files with `**Image**: path [, left, top, width, height]`
- **AI-generated images**: describe an image with `**ImagePrompt**` — generated via the Azure AI image endpoint and cached locally
- **ContentUrls & enrichment**: add `**ContentUrls**` per slide to fetch reference content and auto-enrich both slide bullets and speaker notes via Azure AI Inference
- **Enrichment caching**: enriched slides are written back to the spec file with `**Enriched**: true` so subsequent builds skip re-enrichment (override with `--refetch`)
- **Subtitle line breaks**: use `<br>` in `**Subtitle**` values to split text across multiple lines
- **Style from spec**: font sizes, colors, and resource-box theming are configurable in the front-matter `style:` block
- **Auto `.env` loading**: the CLI automatically loads `.env` from `<cwd>/.env` or `<cwd>/.azure/presentations/.env`
- **Versioned output**: each build creates a new versioned `.pptx` so previous runs are never overwritten

## Spec File Format

Spec files live in `.speckit/specifications/` and use Markdown with YAML front matter:

```markdown
---
title: My Presentation
subtitle: A subtitle
output: My_Presentation.pptx
text_model: gpt-5-mini
image_model: gpt-image-1.5
style:
  title_font_size: 36
  body_font_size: 20
---

## [content] Slide Title

- Bullet one
- Bullet two

**Image**: images/diagram.png, 6.5, 1.5, 3.0, 3.0
**ImagePrompt**: A futuristic cityscape at sunset, digital art style, 6.5, 1.5, 3.0, 3.0
**Animation**: content > fade

**ContentUrls**:
- https://learn.microsoft.com/azure/ai-services/openai/overview
- https://example.com/relevant-page

**Notes**: Speaker notes go here.
```

### Slide Types

| Type | Description |
|------|-------------|
| `title` | Large centred title + subtitle |
| `content` | Title bar + bullet list |
| `section-header` | Topic transition slide |
| `two-column` | Side-by-side content (`**Left**:` / `**Right**:`) |
| `resource-box` | Gradient heading + labelled resource boxes with name/URL rows |

### Image Generation

Describe an image with `**ImagePrompt**` and the generator will create it via the Azure AI endpoint.

| Field | Description |
|-------|-------------|
| `**ImagePrompt**` | Text description [, left, top, width, height] |
| `**ImageModel**` | Per-slide model override |
| `image_model` | Front-matter default for all slides |
| `--image-model` | CLI flag (highest priority) |

Generated images are cached in `<output-dir>/images/`.

### Element Positioning

Use `**<Name>Pos**` directives to move or resize any element on a slide (values in inches: `left, top, width, height`).  This prevents text/image overlap on visually dense slides.

| Directive | Applies to | Example |
|-----------|-----------|---------|
| `**TitlePos**` | Title placeholder | `**TitlePos**: 0.5, 2.2, 5.0, 1.5` |
| `**SubtitlePos**` | Subtitle placeholder | `**SubtitlePos**: 0.5, 4.0, 5.0, 1.0` |
| `**ContentPos**` | Body / bullet placeholder | `**ContentPos**: 0.5, 1.8, 5.0, 5.0` |
| `**LeftPos**` | Left column (two-column) | `**LeftPos**: 0.3, 1.8, 4.5, 5.0` |
| `**RightPos**` | Right column (two-column) | `**RightPos**: 5.2, 1.8, 4.5, 5.0` |
| `**ImagePos**` | Image (overrides coords in `**Image**` / `**ImagePrompt**`) | `**ImagePos**: 6.0, 0.5, 3.5, 3.5` |

All four values are optional — you can supply just `left, top` to move without resizing.

```markdown
## [title] My Title

**TitlePos**: 0.5, 2.2, 5.0, 1.5
**SubtitlePos**: 0.5, 4.0, 5.0, 1.0
**ImagePrompt**: A futuristic cityscape, 5.8, 0.8, 3.5, 3.5
```

### ContentUrls & Note Enrichment

Add a `**ContentUrls**` block to any slide to provide reference URLs.  At build time each URL is fetched and the content is sent to the Azure AI text model to generate supplemental speaker notes:

```markdown
**ContentUrls**:
- https://learn.microsoft.com/azure/ai-services/openai/overview
- https://learn.microsoft.com/azure/ai-services/responsible-use-of-ai-overview
```

- Requires `AZURE_AI_PROJECT_ENDPOINT` (set automatically by `azd up`)
- Uses the `text_model` from front-matter (fallback: `AZURE_AI_TEXT_MODEL` env var → `gpt-4o-mini`)
- Original notes are preserved; supplemental notes are appended

### Style

Font sizes are configurable in the front-matter `style:` block:

| Key | Default | Description |
|-----|---------|-------------|
| `title_font_size` | 36 | Title slides |
| `subtitle_font_size` | 20 | Subtitles |
| `body_font_size` | 20 | Content bullets |
| `heading_font_size` | 32 | Slide headings |
| `column_heading_font_size` | 22 | Two-column headings |
| `column_body_font_size` | 18 | Two-column body |
| `slide_background` | #FFFFFF | Slide background color |
| `subtitle_colors` | _(empty)_ | Comma-separated hex colors for gradient subtitle |
| `badge_width` | 0.9 | Resource-box badge width (inches) |
| `badge_height` | 1.1 | Resource-box badge height (inches) |
| `badge_font_size` | 11 | Badge label font size (pt) |
| `badge_corner_radius` | 12000 | Badge corner rounding (EMU) |
| `badge_gradient_start` | #E3008C | Badge gradient start color |
| `badge_gradient_end` | #6B2FA0 | Badge gradient end color |
| `badge_text_color` | #FFFFFF | Badge text color |
| `box_background` | #E8E8E8 | Resource box background color |
| `box_border_color` | #5B5FC7 | Resource box border color |
| `box_corner_radius` | 5000 | Box corner rounding (EMU) |
| `divider_color` | #D0D0D0 | Box divider line color |
| `name_color` | #000000 | Resource name text color |
| `name_font_size` | 14 | Resource name font size (pt) |
| `url_color` | #0078D4 | Resource URL text color |
| `url_font_size` | 14 | Resource URL font size (pt) |

## Azure Infrastructure

The `infra/` directory contains Bicep templates for deploying Azure AI Foundry resources using the Azure Developer CLI (`azd`).

### Structure

```
infra/
├── azure.yaml                  # azd service configuration
├── main.bicep                  # Subscription-level orchestration
├── main.parameters.json        # Parameter file for azd
├── abbreviations.json          # Azure resource naming abbreviations
├── bicepconfig.json            # Bicep configuration
├── core/
│   └── ai/
│       └── foundry.bicep       # Azure AI Foundry + model deployments + Bing Grounding
└── hooks/
    ├── postprovision.ps1       # Post-deployment hook (Windows)
    └── postprovision.sh        # Post-deployment hook (Linux/macOS)
```

### Deploy

```bash
azd auth login
azd init
azd up
```

This provisions:
- **Resource Group**
- **Azure AI Foundry** account with a default project
- **GPT chat model deployment** (GlobalStandard SKU)
- **GPT image model deployment** (GlobalStandard SKU)
- **Bing Grounding** connection for web-grounded search
- **Agents capability host**

### Environment Variables

After `azd up`, the following environment variables are populated:

| Variable | Description |
|----------|-------------|
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project endpoint (used by image gen & enrichment) |
| `AI_PROJECT_NAME` | Foundry account name |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `AZURE_LOCATION` | Azure region |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Chat model deployment name |
| `AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME` | Image model deployment name |
| `AZURE_AI_TEXT_MODEL` | Fallback text model (used when `text_model` not set in front-matter) |
| `BING_CONNECTION_NAME` | Bing connection name |
| `BING_PROJECT_CONNECTION_ID` | Bing project connection resource ID |

Authentication is handled by `DefaultAzureCredential` — run `az login` locally or use managed identity in CI.

## Requirements

- Python 3.10+
- See [requirements.txt](requirements.txt)
- For Azure deployment: [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- For AI features: `az login` (or set `AZURE_AI_PROJECT_ENDPOINT` + managed identity)

## CLI Reference

```
python presentations.py <spec-file> [options]

positional arguments:
  spec                  Path to the .spec.md file

options:
  -o, --output-dir DIR  Output directory (default: output)
  --image-model MODEL   Image generation model name (overrides front-matter)
  --refetch             Re-fetch and regenerate all AI enrichments, even if
                        cached results exist in the spec file
  --slides SELECTION    Slide numbers to generate (1-indexed). Default: all.
                        Examples: '5', '3-7', '1,3,5-8'
```
