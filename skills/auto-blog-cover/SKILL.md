---
name: auto-blog-cover
description: Automates the process of creating and setting blog post covers. Reads a markdown file, generates a cover image based on title/subtitle, uploads it, and updates the file's frontmatter (e.g., banner_img).
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "1.0"
---

# Auto Blog Cover Skill

An end-to-end workflow automation for blog writers. It connects parsing, generation, uploading, and editing into a single command.

## Prerequisites

1.  **Dependencies**:
    ```bash
    pip install -r skills/auto-blog-cover/requirements.txt
    ```
2.  **Related Skills**: Requires `cover-generator` and `image-uploader` to be present and configured.

## Usage

```bash
python3 skills/auto-blog-cover/auto_blog_cover.py <path_to_markdown_file> [options]
```

### Options

*   `filepath`: Path to the markdown post (Required).
*   `--title`: Manually specify title (overrides file content).
*   `--subtitle`: Manually specify subtitle.
*   `--theme`: Color theme (`random`, `dark`, `light`, `blue`).
*   `--fields`: Comma-separated Frontmatter fields to update. Default: `banner_img,index_img`.

### Examples

**Auto-detect everything:**
```bash
python3 skills/auto-blog-cover/auto_blog_cover.py content/posts/my-new-post.md
```

**Override text (AI assisted scenario):**
```bash
python3 skills/auto-blog-cover/auto_blog_cover.py _posts/2024-02-01-ai.md \
  --title "AI Evolution" \
  --subtitle "From Function Call to MCP"
```

**Custom fields for different blog engine:**
```bash
python3 skills/auto-blog-cover/auto_blog_cover.py post.md --fields "cover_image,og_image"
```
