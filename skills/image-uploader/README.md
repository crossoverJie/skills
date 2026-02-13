# Image Uploader Skill

A CLI tool to upload images to sm.ms, Imgur, and GitHub (with jsDelivr CDN).

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.json` with your credentials:

```json
{
    "default_provider": "smms",
    "smms_token": "YOUR_SMMS_TOKEN",
    "imgur_client_id": "YOUR_IMGUR_CLIENT_ID",
    "github_token": "YOUR_GITHUB_TOKEN",
    "github_owner": "YOUR_GITHUB_USERNAME",
    "github_repo": "YOUR_IMAGE_REPO_NAME",
    "github_path": "images",
    "github_branch": "main",
    "github_cdn": "jsdelivr"
}
```

Alternatively, use environment variables:
- `SMMS_TOKEN` — sm.ms API token
- `IMGUR_CLIENT_ID` — Imgur client ID
- `IMAGE_UPLOADER_GITHUB_TOKEN` — GitHub personal access token
- `IMAGE_UPLOADER_GITHUB_OWNER` — GitHub username / org
- `IMAGE_UPLOADER_GITHUB_REPO` — GitHub repository name
- `IMAGE_UPLOADER_PROVIDER` — default provider (`smms`, `imgur`, or `github`)

### GitHub CDN Options

The `github_cdn` field controls the CDN domain used in returned URLs:
- `"jsdelivr"` — `cdn.jsdelivr.net` (default, international)
- `"china"` — `jsd.cdn.zzko.cn` (China mirror)

## Usage

```bash
# Upload to sm.ms (default)
python3 image_uploader.py /path/to/image.png

# Upload to Imgur
python3 image_uploader.py /path/to/image.png --provider imgur

# Upload to GitHub (jsDelivr CDN)
python3 image_uploader.py /path/to/image.png --provider github

# With explicit token
python3 image_uploader.py /path/to/image.png --token YOUR_TOKEN

# Imgur with env var
IMGUR_CLIENT_ID="your_id" python3 image_uploader.py image.png --provider imgur

# GitHub with env vars
IMAGE_UPLOADER_GITHUB_TOKEN="tok" IMAGE_UPLOADER_GITHUB_OWNER="user" IMAGE_UPLOADER_GITHUB_REPO="imgs" python3 image_uploader.py image.png --provider github
```
