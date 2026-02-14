import logging

logger = logging.getLogger(__name__)


def is_back_button(text: str) -> bool:
    """Check if the message is a back button"""
    return text and "Orqaga" in text


def format_file_size(bytes_size: int) -> str:
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    import re
    return re.sub(r'[<>:"/\\|?*]', '_', filename)
