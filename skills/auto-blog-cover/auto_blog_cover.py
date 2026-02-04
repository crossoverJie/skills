#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
import re
import frontmatter

def get_script_path(skill_name, script_name):
    """Locate a sibling skill script."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to skills/ then down to skill_name
    path = os.path.join(current_dir, "..", skill_name, script_name)
    return os.path.abspath(path)

def generate_and_upload_cover(title, subtitle, theme):
    """Invokes cover-generator with upload enabled."""
    generator_script = get_script_path("cover-generator", "cover_generator.py")
    
    if not os.path.exists(generator_script):
        print(f"❌ Error: Could not find cover-generator at {generator_script}")
        return None

    cmd = [
        sys.executable, 
        generator_script, 
        title, 
        "--upload",
        "--theme", theme
    ]
    
    if subtitle:
        cmd.extend(["--subtitle", subtitle])

    print(f"🎨 Generating cover for: '{title}'...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse output for URL
        # Look for "URL: https://..."
        url_match = re.search(r"URL: (https?://\S+)", result.stdout)
        
        if result.returncode == 0 and url_match:
            url = url_match.group(1)
            print(f"✅ Generated and uploaded: {url}")
            return url
        else:
            print("❌ Generation or upload failed.")
            print("Output:", result.stdout)
            print("Error:", result.stderr)
            return None
            
    except Exception as e:
        print(f"❌ Execution error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Auto-generate cover for blog post and update frontmatter.")
    parser.add_argument("filepath", help="Path to the markdown file")
    parser.add_argument("--title", help="Override title")
    parser.add_argument("--subtitle", help="Override subtitle")
    parser.add_argument("--theme", help="Cover theme", default="random")
    parser.add_argument("--fields", help="Comma-separated frontmatter fields to update", default="banner_img,index_img")
    
    args = parser.parse_args()
    filepath = args.filepath
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    # 1. Parse Markdown
    try:
        post = frontmatter.load(filepath)
    except Exception as e:
        print(f"❌ Error parsing frontmatter: {e}")
        sys.exit(1)

    # 2. Determine Title
    title = args.title
    if not title:
        title = post.get('title')
    if not title:
        # Fallback: Try to find first H1 # Header
        h1_match = re.search(r'^#\s+(.+)$', post.content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1)
            
    if not title:
        print("❌ Could not determine title. Please provide --title.")
        sys.exit(1)

    # 3. Determine Subtitle
    subtitle = args.subtitle
    if not subtitle:
        subtitle = post.get('subtitle') or post.get('description')
    if not subtitle:
        # Fallback: First 50 chars of content (cleanup markdown logic omitted for simplicity)
        content_stripped = post.content.strip()
        if content_stripped:
             subtitle = content_stripped[:30] + "..."

    # 4. Generate & Upload
    url = generate_and_upload_cover(title, subtitle or "", args.theme)
    
    if not url:
        sys.exit(1)

    # 5. Update Frontmatter
    fields_to_update = [f.strip() for f in args.fields.split(',')]
    updated = False
    
    for field in fields_to_update:
        print(f"📝 Updating field '{field}'...")
        post[field] = url
        updated = True
        
    if updated:
        # Write back to file preserving order as much as possible using regex substitution
        # This avoids reordering YAML keys which python-frontmatter might do
        with open(filepath, 'r') as f:
            content = f.read()
            
        for field in fields_to_update:
            # Regex to match "key: value" pattern, supporting http/https values
            # \1: key part (e.g. "banner_img:")
            # \2: current value part (rest of line)
            pattern = fr"^({field}:\s*)(.+)$"
            replacement = fr"\1{url}"
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"🎉 Successfully updated {filepath}")

if __name__ == "__main__":
    main()
