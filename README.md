# LASHBOT — AI Hujjat Servis

Professional Telegram bot for document processing with AI capabilities.

## 🚀 Features

- ✨ **Obyektivka AI** - Intelligent resume generation via voice
- 📄 **Rasm → Word AI** - OCR with layout restoration
- 🔤 **Kirill-Lotin** - Uzbek transliteration
- 🌐 **Tarjima fayl** - Multi-language document translation
- 📑 **Rasm → PDF** - Image merging
- ✅ **Imlo tekshirish** - Spell checking
- 💎 **Premium xizmatlar** - Advanced features
- 💰 **Balans** - Payment integration
- ✉️ **Aloqa** - Support system

## 📦 Installation

```bash
# Clone repository
git clone <your-repo>
cd hujjatchi_ai_bot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your BOT_TOKEN
```

## ⚙️ Configuration

1. Get bot token from [@BotFather](https://t.me/BotFather)
2. Add token to `.env` file:
```
BOT_TOKEN=your_token_here
```

## 🏃 Run

```bash
python main.py
```

## 📁 Project Structure

```
hujjatchi_ai_bot/
├── bot/
│   ├── handlers/       # Message handlers
│   ├── keyboards/      # Reply keyboards
│   ├── utils/          # Helper functions
│   └── services/       # Business logic (future)
├── config.py           # Configuration
├── main.py             # Entry point
├── requirements.txt    # Dependencies
└── .env                # Environment variables
```

## 🔧 Tech Stack

- **Framework:** python-telegram-bot 20.7
- **Language:** Python 3.11+
- **Architecture:** Handler-based routing
- **Future:** FastAPI webhooks, PostgreSQL, Redis

## 📝 Todo

- [ ] Integrate Speech-to-Text API
- [ ] Add OCR engine (Tesseract/Google Vision)
- [ ] Implement transliteration logic
- [ ] Add AI translation service
- [ ] PDF generation from images
- [ ] Spell checker integration
- [ ] Payment gateway (Click, Payme)
- [ ] Database layer
- [ ] Admin panel

## 👨‍💻 Developer

Created with ❤️ using elite-level architecture.

## 📄 License

MIT
