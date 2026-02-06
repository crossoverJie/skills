---
name: image-uploader
description: Uploads images to image hosting services (currently supports sm.ms). Use this skill when the user wants to upload a local image file to the web and get a public URL.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "1.0"
---

# Image Uploader Skill

This skill allows uploading local image files to public image hosting services. Currently, it supports **sm.ms**.

## Prerequisites

1.  **Dependencies**: The skill requires Python 3 and the `requests` library.
    ```bash
    pip install -r skills/image-uploader/requirements.txt
    ```
2.  **Configuration**: An API token is required.
    *   **Config File**: `skills/image-uploader/config.json` (Recommended)
        ```json
        { "smms_token": "YOUR_TOKEN" }
        ```
    *   **Environment Variable**: `SMMS_TOKEN`
    *   **CLI Argument**: `--token`

## Usage

To upload an image, run the Python script:

```bash
python3 skills/image-uploader/image_uploader.py <path_to_image>
```

### Examples

**Basic Upload (using config/env token):**
```bash
python3 skills/image-uploader/image_uploader.py /Users/me/Pictures/screenshot.png
```

**Upload with explicit token:**
```bash
python3 skills/image-uploader/image_uploader.py image.png --token "YOUR_API_TOKEN"
```

## Output

The script outputs the result to stdout.

**Success:**
```text
✅ Upload Successful!
URL: https://s2.loli.net/2023/01/01/abcdefg.jpg
Delete Link: https://sm.ms/delete/xyz123
Filename: screenshot.png
```

**Already Exists:**
```text
⚠️  Image already exists.
URL: https://s2.loli.net/2023/01/01/abcdefg.jpg
```

**Failure:**
```text
❌ Upload Failed
Message: Unauthorized.
```
