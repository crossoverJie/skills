# Image Uploader Skill

A CLI tool to upload images to sm.ms (and future providers).

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Rename `config.json` if needed (it should be present).
2. Edit `config.json` and add your API token:
   ```json
   {
       "smms_token": "YOUR_TOKEN"
   }
   ```
   
   Alternatively, use environment variable `SMMS_TOKEN`.

## Usage

```bash
python3 image_uploader.py /path/to/image.png
```

Or with temporary token:
```bash
python3 image_uploader.py /path/to/image.png --token YOUR_TOKEN
```
