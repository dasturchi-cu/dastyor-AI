import os
from pathlib import Path
from PIL import Image

artifacts_dir = Path("C:/Users/User/.gemini/antigravity/brain/0cda553d-0f7b-4b6c-81c8-f1bacec0dc8c")
samples_dir = Path("c:/Users/User/hujjatchi_ai_bot/assets/samples")

def check_images():
    print("Listing files in artifacts:")
    for p in sorted(artifacts_dir.glob("media__*")):
        try:
            with Image.open(p) as img:
                print(f"File: {p.name}, Size: {p.stat().st_size} bytes, Format: {img.format}, Dimensions: {img.size}")
        except Exception as e:
            print(f"File: {p.name}, Error: {e}")

if __name__ == "__main__":
    check_images()
