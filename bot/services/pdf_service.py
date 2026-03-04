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

    # Open all images and force convert to RGB
    pil_images = []
    for path in image_paths:
        try:
            img = Image.open(path)
            # Force RGB to avoid any corrupted/transparent PDF issues
            img = img.convert("RGB")
            pil_images.append(img)
        except Exception as e:
            # If an image fails to open, skip it rather than breaking the whole PDF
            pass

    if not pil_images:
        raise ValueError("Yaroqli rasmlar topilmadi.")

    first, *rest = pil_images
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    first.save(output_path, "PDF", resolution=100.0, save_all=True, append_images=rest)
    return output_path


