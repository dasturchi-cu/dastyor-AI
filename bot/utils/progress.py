from telegram import Message

async def send_progress(context, chat_id, text="Jarayon boshlandi..."):
    """Send initial progress message"""
    return await context.bot.send_message(chat_id=chat_id, text=f"⏳ {text} [░░░░░░░░░░] 0%")

async def update_progress(context, message: Message, percent: int, text: str):
    """Update progress bar"""
    try:
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        
        filled = int(percent / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        new_text = f"⏳ {text}\n[{bar}] {percent}%"
        
        if message.text != new_text:
            await message.edit_text(new_text)
    except Exception:
        pass # Ignore errors (e.g. message deleted)
