import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Bot, MenuButtonWebApp, WebAppInfo

# Fix for Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def setup_bot():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=token)
    
    # 1. Webhookni o'chirish
    print("Webhook o'chirilmoqda...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        me = await bot.get_me()
        print(f"Webhook o'chirildi: @{me.username}")
    except Exception as e:
        print(f"Webhook o'chirishda xato: {e}")

    # 2. Menu tugmasini o'rnatish (Input yonidagi tugma)
    print("Menu tugmasi o'rnatilmoqda...")
    web_app_url = "https://dastyor-ai.onrender.com/webapp/index.html"
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚀 Appni ochish",
                web_app=WebAppInfo(url=web_app_url)
            )
        )
        print("Menu tugmasi Web App-ga o'rnatildi!")
    except Exception as e:
        print(f"Menu tugmasini o'rnatishda xato: {e}")

if __name__ == "__main__":
    asyncio.run(setup_bot())
