import os
import shutil
from pathlib import Path
from PIL import Image

artifacts_dir = Path("C:/Users/User/.gemini/antigravity/brain/0cda553d-0f7b-4b6c-81c8-f1bacec0dc8c")
samples_dir = Path("c:/Users/User/hujjatchi_ai_bot/assets/samples")

# Source files
src_cv = artifacts_dir / "media__1783082305306.png"
src_oby = artifacts_dir / "media__1783082327178.jpg"

def copy_and_convert():
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Copy CV Sample (already PNG)
    dest_cv_v2 = samples_dir / "cv_sample_v2.png"
    dest_cv_v1 = samples_dir / "cv_sample.png"
    
    shutil.copy(src_cv, dest_cv_v2)
    shutil.copy(src_cv, dest_cv_v1)
    print(f"Copied CV sample to {dest_cv_v2.name} and {dest_cv_v1.name}")
    
    # 2. Convert and save Obyektivka sample as PNG
    dest_oby_v2 = samples_dir / "oby_sample_v2.png"
    dest_oby_v1 = samples_dir / "obyektivka_sample.png"
    
    with Image.open(src_oby) as img:
        img.save(dest_oby_v2, "PNG")
        img.save(dest_oby_v1, "PNG")
    print(f"Converted and saved Obyektivka sample to {dest_oby_v2.name} and {dest_oby_v1.name}")

if __name__ == "__main__":
    copy_and_convert()
