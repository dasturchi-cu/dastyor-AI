from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_smart_photo_keyboard():
    """Smart actions for uploaded photos"""
    keyboard = [
        [
            InlineKeyboardButton("📄 Rasm → Word (OCR)", callback_data="smart_ocr"),
            InlineKeyboardButton("🖼 PDF ga qo'shish", callback_data="smart_img2pdf")
        ],
        [InlineKeyboardButton("🗑 Bekor qilish", callback_data="smart_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_smart_document_keyboard(file_ext):
    """Smart actions based on file extension"""
    buttons = []
    
    # Translation supports almost all docs
    buttons.append([InlineKeyboardButton("🌍 Tarjima qilish", callback_data="smart_translate")])
    
    # Word/PDF specific
    if 'pdf' in file_ext or 'doc' in file_ext:
        buttons.append([InlineKeyboardButton("📝 Obyektivka tahlili", callback_data="smart_obyektivka")])
        
    buttons.append([InlineKeyboardButton("🗑 Bekor qilish", callback_data="smart_cancel")])
    
    return InlineKeyboardMarkup(buttons)

def get_smart_audio_keyboard():
    """Smart actions for audio files"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Transkripsiya (Matn)", callback_data="smart_transcribe"),
            InlineKeyboardButton("👤 Obyektivka to'ldirish", callback_data="smart_obyektivka_audio")
        ],
        [InlineKeyboardButton("🗑 Bekor qilish", callback_data="smart_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)
