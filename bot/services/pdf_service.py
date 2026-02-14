"""
PDF generation service.

Takes a list of local image file paths and merges them into a single PDF.
Uses Pillow, which is already included in requirements.txt.
"""

import os
from typing import List

from PIL import Image


def images_to_pdf(image_paths: List[str], output_path: str) -> str:
    """
    Merge multiple images into a single PDF.

    :param image_paths: List of image file paths
    :param output_path: Destination PDF path
    :return: The PDF file path
    """
    if not image_paths:
        raise ValueError("image_paths bo‘sh bo‘lishi mumkin emas")

    # Open all images and convert to RGB
    pil_images = []
    for path in image_paths:
        img = Image.open(path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        pil_images.append(img)

    first, *rest = pil_images
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    first.save(output_path, save_all=True, append_images=rest)
    return output_path


