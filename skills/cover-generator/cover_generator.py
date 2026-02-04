#!/usr/bin/env python3
import argparse
import random
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_gradient(width, height, start_color, end_color):
    """Generates a vertical gradient image."""
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def get_random_color():
    """Returns a random bright color."""
    return (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))

def create_cover(title, subtitle, output_path, theme="random"):
    width, height = 1200, 630  # Standard social media card size
    
    # 1. Background
    if theme == "random":
        color1 = get_random_color()
        color2 = get_random_color()
    elif theme == "dark":
        color1 = (30, 30, 30)
        color2 = (60, 60, 60)
    elif theme == "light":
        color1 = (240, 240, 240)
        color2 = (255, 255, 255)
    else:
        color1 = (41, 128, 185) # Blue
        color2 = (142, 68, 173) # Purple

    image = generate_gradient(width, height, color1, color2)
    
    # Add some noise/texture (optional simple overlay)
    
    draw = ImageDraw.Draw(image)
    
    # 2. Fonts
    # Try to find a system font, fallback to default
    font_path = None
    possible_fonts = [
        "/System/Library/Fonts/STHeiti Light.ttc", # macOS (Heiti)
        "/System/Library/Fonts/PingFang.ttc", # macOS
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", # Linux
        "C:\\Windows\\Fonts\\msyh.ttc" # Windows (YaHei)
    ]
    
    for p in possible_fonts:
        if os.path.exists(p):
            font_path = p
            break
            
    title_size = 80
    subtitle_size = 40
    
    try:
        if font_path:
            title_font = ImageFont.truetype(font_path, title_size)
            subtitle_font = ImageFont.truetype(font_path, subtitle_size)
        else:
            print("⚠️  Warning: No custom font found. Using default font (may not support Chinese).")
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # 3. Text Layout
    # Center text
    # Note: textbbox is newer Pillow, textsize is deprecated. Using basic math for compatibility if needed, 
    # but let's assume recent Pillow.
    
    text_color = (255, 255, 255) if theme != "light" else (30, 30, 30)

    # Title
    try:
        _, _, w, h = draw.textbbox((0, 0), title, font=title_font)
        title_x = (width - w) / 2
        title_y = (height - h) / 2 - 40
        draw.text((title_x, title_y), title, font=title_font, fill=text_color)
    except AttributeError:
        # Fallback for older Pillow
        w, h = draw.textsize(title, font=title_font)
        title_x = (width - w) / 2
        title_y = (height - h) / 2 - 40
        draw.text((title_x, title_y), title, font=title_font, fill=text_color)

    # Subtitle
    if subtitle:
        try:
            _, _, w, h = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            sub_x = (width - w) / 2
            sub_y = title_y + 100
            draw.text((sub_x, sub_y), subtitle, font=subtitle_font, fill=text_color)
        except AttributeError:
            w, h = draw.textsize(subtitle, font=subtitle_font)
            sub_x = (width - w) / 2
            sub_y = title_y + 100
            draw.text((sub_x, sub_y), subtitle, font=subtitle_font, fill=text_color)

    # Save
    image.save(output_path)
    print(f"✅ Cover image generated: {output_path}")
    return output_path

def upload_image(image_path):
    """Calls the sibling image-uploader skill."""
    # Locate the uploader script relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uploader_path = os.path.join(script_dir, "..", "image-uploader", "image_uploader.py")
    
    if not os.path.exists(uploader_path):
        print("❌ Uploader skill not found at expected location.")
        return False

    print("🚀 Starting upload...")
    # Call the python script
    result = subprocess.run([sys.executable, uploader_path, image_path], capture_output=False)
    
    if result.returncode != 0:
        print("❌ Upload failed.")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate a blog cover image and optionally upload it.")
    parser.add_argument("title", help="Main title text")
    parser.add_argument("--subtitle", help="Subtitle text", default="")
    parser.add_argument("--output", help="Output filename", default="cover.png")
    parser.add_argument("--theme", help="Color theme (random, dark, light, blue)", default="random")
    parser.add_argument("--upload", help="Upload to image host after generation", action="store_true")
    
    args = parser.parse_args()
    
    output_path = args.output
    if not output_path.endswith('.png'):
        output_path += '.png'
        
    if args.upload:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"\n🔄 Retry attempt {attempt + 1}/{max_retries}...")
                    
                create_cover(args.title, args.subtitle, output_path, args.theme)
                success = upload_image(output_path)
                
                if success:
                    break
            except Exception as e:
                print(f"Error during processing: {e}")
            finally:
                # Always clean up the local file if we are in upload mode
                if os.path.exists(output_path):
                    os.remove(output_path)
                    print(f"🧹 Cleaned up temporary file: {output_path}")
    else:
        # Just generate, don't delete
        create_cover(args.title, args.subtitle, output_path, args.theme)

if __name__ == "__main__":
    main()
