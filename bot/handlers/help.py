from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message with list of features"""
    help_text = (
        "🤖 **Dastyor AI - Yordamchi Boti**\n\n"
        "Quyidagi xizmatlardan foydalanishingiz mumkin:\n\n"
        
        "📄 **Rasm→Word AI ✨**\n"
        "Rasmdagi matnlarni o'qib, Word (.docx) formatiga o'tkazib beradi. Qo'lyozma yoki kitob matnlari uchun juda qulay.\n\n"

        "📝 **Obyektivka Ai ✨**\n"
        "Ovozli xabar yoki matn orqali ma'lumotlaringizni yuborasiz, bot esa tayyor Obyektivka (Ma'lumotnoma) hujjatini (Word/PDF) tayyorlab beradi.\n\n"

        "🔄 **Krill-lotin ✏️**\n"
        "Matn yoki hujjatlarni Kirilldan Lotinga va aksincha o'girish xizmati. Word va Excel fayllarni ham qo'llab-quvvatlaydi.\n\n"

        "🌍 **Tarjima fayl 📦**\n"
        "Katta hujjatlarni (Word, PDF, PPTX) asl formatini buzmasdan to'liq tarjima qiladi (O'zbek, Rus, Ingliz).\n\n"

        "🖼 **Rasm→PDF**\n"
        "Bir nechta rasmni yuborsangiz, ularni bitta PDF kitob shaklida birlashtirib beradi.\n\n"

        "✍️ **Imlo tekshirish ✏️**\n"
        "Matndagi imlo va grammatik xatolarni topib, to'g'rilab beradi.\n\n"

        "💎 **Premium xizmatlar**\n"
        "Cheklovsiz foydalanish, reklamasiz va yuqori tezlik uchun Premium xarid qilishingiz mumkin.\n\n"
        
        "Savollar bo'lsa, 'Aloqa uchun' tugmasini bosing."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_menu())
