# AI Skills

A collection of useful skills for AI agents (like GitHub Copilot CLI), following the [Agent Skills specification](https://agentskills.io/specification).

## Installation

Clone this repository or copy the `skills/` directory into your project workspace.

```bash
git clone https://github.com/yourusername/ai-skills.git
```

## Skills

### Tools & Utilities

- **[Image Uploader](skills/image-uploader/SKILL.md)**: Upload local images to cloud hosting services (currently supports sm.ms).
- **[Cover Generator](skills/cover-generator/SKILL.md)**: Programmatically generate elegant, gradient-based cover images for blogs and articles.

## Usage

Each skill has its own documentation and requirements.

### Quick Start

1.  **Image Uploader**:
    ```bash
    python3 skills/image-uploader/image_uploader.py path/to/image.png
    ```

2.  **Cover Generator**:
    ```bash
    python3 skills/cover-generator/cover_generator.py "My Title" --upload
    ```
