#!/usr/bin/env python3
import os
import sys
import argparse
import json
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
    parser = argparse.ArgumentParser(description="Upload images to sm.ms (and potentially other providers).")
    parser.add_argument("image_path", help="Path to the image file to upload")
    parser.add_argument("--token", help="API Token for the provider")
    
    args = parser.parse_args()
    
    # 1. Configuration Priority: CLI Args > Env Vars > Config File
    token = args.token
    
    if not token:
        token = os.environ.get('SMMS_TOKEN')
        
    if not token:
        config = load_config()
        token = config.get('smms_token')
        
    if not token:
        print("Error: Token not found. Please provide it via --token, SMMS_TOKEN env var, or config.json.")
        print(f"To create a config file, create '{CONFIG_FILE_NAME}' with content: {{ \"smms_token\": \"YOUR_TOKEN\" }}")
        sys.exit(1)

    uploader = SmMsUploader(token)
    
    print(f"Uploading {args.image_path} to sm.ms...")
    result = uploader.upload(args.image_path)
    
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
        # Debug info
        # print(json.dumps(result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
