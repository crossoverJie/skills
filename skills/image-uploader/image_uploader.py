#!/usr/bin/env python3
import os
import sys
import argparse
import json
import base64
import hashlib
import requests
from abc import ABC, abstractmethod

CONFIG_FILE_NAME = 'config.json'

class BaseUploader(ABC):
    """Abstract base class for image uploaders to support future providers."""
    
    @abstractmethod
    def upload(self, image_path):
        pass

class SmMsUploader(BaseUploader):
    """Uploader implementation for sm.ms."""

    API_URL = "https://sm.ms/api/v2/upload"

    def __init__(self, token):
        self.token = token

    def upload(self, image_path):
        if not self.token:
            raise ValueError("SM.MS API token is required.")

        headers = {
            'Authorization': self.token
        }

        try:
            with open(image_path, 'rb') as f:
                files = {'smfile': f}
                # User-Agent is often required by some APIs to avoid being blocked
                headers['User-Agent'] = 'Mozilla/5.0 (compatible; ImageUploaderSkill/1.0)'

                response = requests.post(self.API_URL, headers=headers, files=files)
                response.raise_for_status()

                return response.json()
        except IOError as e:
            return {"success": False, "message": f"File error: {str(e)}"}
        except requests.RequestException as e:
            return {"success": False, "message": f"Network error: {str(e)}"}

class ImgurUploader(BaseUploader):
    """Uploader implementation for Imgur."""

    API_URL = "https://api.imgur.com/3/image"

    def __init__(self, client_id):
        self.client_id = client_id

    def upload(self, image_path):
        if not self.client_id:
            raise ValueError("Imgur Client-ID is required.")

        headers = {
            'Authorization': f'Client-ID {self.client_id}'
        }

        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                response = requests.post(self.API_URL, headers=headers, files=files)
                response.raise_for_status()
                return response.json()
        except IOError as e:
            return {"success": False, "message": f"File error: {str(e)}"}
        except requests.RequestException as e:
            return {"success": False, "message": f"Network error: {str(e)}"}

class GitHubUploader(BaseUploader):
    """Uploader implementation for GitHub + jsDelivr CDN."""

    API_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    CDN_DOMAINS = {
        "jsdelivr": "cdn.jsdelivr.net",
        "china": "jsd.cdn.zzko.cn",
    }

    def __init__(self, token, owner, repo, path="images", branch="main", cdn="jsdelivr"):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.path = path.strip("/")
        self.branch = branch
        self.cdn = cdn

    def upload(self, image_path):
        if not self.token:
            raise ValueError("GitHub token is required.")

        try:
            with open(image_path, 'rb') as f:
                content = f.read()
        except IOError as e:
            return {"success": False, "message": f"File error: {str(e)}"}

        filename = os.path.basename(image_path)
        content_hash = hashlib.sha256(content).hexdigest()[:8]
        remote_path = f"{self.path}/{content_hash}_{filename}"

        encoded = base64.b64encode(content).decode('utf-8')

        url = self.API_URL.format(owner=self.owner, repo=self.repo, path=remote_path)
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
        }
        data = {
            'message': f'Upload {filename}',
            'content': encoded,
            'branch': self.branch,
        }

        try:
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            cdn_domain = self.CDN_DOMAINS.get(self.cdn, self.CDN_DOMAINS["jsdelivr"])
            cdn_url = f"https://{cdn_domain}/gh/{self.owner}/{self.repo}@{self.branch}/{remote_path}"

            return {
                "success": True,
                "cdn_url": cdn_url,
                "raw_url": result.get("content", {}).get("download_url"),
                "sha": result.get("content", {}).get("sha"),
            }
        except requests.RequestException as e:
            return {"success": False, "message": f"Network error: {str(e)}"}

def load_config():
    """
    Load configuration looking in:
    1. Current directory config.json
    2. Script directory config.json
    """
    # Check current directory
    if os.path.exists(CONFIG_FILE_NAME):
        with open(CONFIG_FILE_NAME, 'r') as f:
            return json.load(f)
            
    # Check script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_config = os.path.join(script_dir, CONFIG_FILE_NAME)
    if os.path.exists(script_config):
        with open(script_config, 'r') as f:
            return json.load(f)
            
    return {}

def main():
    parser = argparse.ArgumentParser(description="Upload images to sm.ms, Imgur, or GitHub (jsDelivr CDN).")
    parser.add_argument("image_path", help="Path to the image file to upload")
    parser.add_argument("--token", help="API token/client-ID for the provider")
    parser.add_argument("--provider", choices=["smms", "imgur", "github"], help="Image hosting provider (default: smms)")

    args = parser.parse_args()

    config = load_config()

    # Provider priority: CLI --provider > IMAGE_UPLOADER_PROVIDER env > config default_provider > "smms"
    provider = (
        args.provider
        or os.environ.get('IMAGE_UPLOADER_PROVIDER')
        or config.get('default_provider')
        or 'smms'
    )

    # Token resolution per provider: CLI --token > env var > config file
    if provider == 'imgur':
        token = args.token or os.environ.get('IMGUR_CLIENT_ID') or config.get('imgur_client_id')
        if not token:
            print("Error: Imgur Client-ID not found. Provide it via --token, IMGUR_CLIENT_ID env var, or config.json.")
            print(f"To configure, add \"imgur_client_id\": \"YOUR_CLIENT_ID\" to '{CONFIG_FILE_NAME}'.")
            sys.exit(1)
        uploader = ImgurUploader(token)
    elif provider == 'github':
        token = args.token or os.environ.get('IMAGE_UPLOADER_GITHUB_TOKEN') or config.get('github_token')
        if not token:
            print("Error: GitHub token not found. Provide via --token, IMAGE_UPLOADER_GITHUB_TOKEN env, or config.json.")
            sys.exit(1)
        owner = os.environ.get('IMAGE_UPLOADER_GITHUB_OWNER') or config.get('github_owner')
        repo = os.environ.get('IMAGE_UPLOADER_GITHUB_REPO') or config.get('github_repo')
        if not owner or not repo:
            print("Error: github_owner and github_repo are required in config.json or env vars.")
            sys.exit(1)
        path = config.get('github_path', 'images')
        branch = config.get('github_branch', 'main')
        cdn = os.environ.get('IMAGE_UPLOADER_GITHUB_CDN') or config.get('github_cdn', 'jsdelivr')
        uploader = GitHubUploader(token, owner, repo, path, branch, cdn)
    else:
        token = args.token or os.environ.get('SMMS_TOKEN') or config.get('smms_token')
        if not token:
            print("Error: SM.MS token not found. Provide it via --token, SMMS_TOKEN env var, or config.json.")
            print(f"To configure, add \"smms_token\": \"YOUR_TOKEN\" to '{CONFIG_FILE_NAME}'.")
            sys.exit(1)
        uploader = SmMsUploader(token)

    print(f"Uploading {args.image_path} to {provider}...")
    result = uploader.upload(args.image_path)

    if provider == 'imgur':
        if result.get('success') and result.get('data'):
            data = result['data']
            print("\n✅ Upload Successful!")
            print(f"URL: {data.get('link')}")
            print(f"Delete Hash: {data.get('deletehash')}")
        else:
            print("\n❌ Upload Failed")
            print(f"Message: {result.get('message', result.get('data', {}).get('error', 'Unknown error'))}")
            sys.exit(1)
    elif provider == 'github':
        if result.get('success'):
            print("\n✅ Upload Successful!")
            print(f"CDN URL: {result.get('cdn_url')}")
            print(f"Raw URL: {result.get('raw_url')}")
        else:
            print("\n❌ Upload Failed")
            print(f"Message: {result.get('message')}")
            sys.exit(1)
    else:
        if result.get('success'):
            data = result.get('data', {})
            print("\n✅ Upload Successful!")
            print(f"URL: {data.get('url')}")
            print(f"Delete Link: {data.get('delete')}")
            print(f"Filename: {data.get('filename')}")
        elif result.get('code') == 'image_repeated':
            print("\n⚠️  Image already exists.")
            print(f"URL: {result.get('images')}")
        else:
            print("\n❌ Upload Failed")
            print(f"Message: {result.get('message')}")
            sys.exit(1)

if __name__ == "__main__":
    main()
