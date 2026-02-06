---
name: cover-generator
description: Generates simple gradient-based cover images for blogs or articles with a title and subtitle. Can optionally upload the generated image immediately.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "1.0"
---

# Cover Generator Skill

Generates elegant, minimal cover images (1200x630) with custom text and gradients. Ideal for blog posts, social media cards, and article headers.

## Prerequisites

1.  **Dependencies**:
    ```bash
    pip install -r skills/cover-generator/requirements.txt
    ```

## Usage

```bash
python3 skills/cover-generator/cover_generator.py "Your Title" [options]
```

### Options

*   `title`: Main text to display (Required).
*   `--subtitle`: Smaller text below the title.
*   `--theme`: Color theme (`random`, `dark`, `light`, `blue`). Default: `random`.
*   `--output`: Output filename. Default: `cover.png`.
*   `--upload`: Automatically upload the generated image using the `image-uploader` skill.

### Examples

**Basic Generation:**
```bash
python3 skills/cover-generator/cover_generator.py "My Awesome Blog Post" --subtitle "A deep dive into AI"
```

**Generate and Upload:**
```bash
python3 skills/cover-generator/cover_generator.py "Weekly Report" --theme blue --upload
```
