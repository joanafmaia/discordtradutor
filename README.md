# 🤖 Discord Translator Bot

A Discord bot that automatically translates messages using a translation API. It detects the language of each message and sends a translated version to the configured target language (default: Portuguese).

---

## ✨ Features

- 🌍 Automatic message translation  
-  Smart language detection  
-  Configurable target language (e.g., Portuguese)  
-  Commands to change language, enable/disable translation, etc.  
-  Easy to test and run locally  

---

## 📦 Requirements

- Python 3.8 or higher  
- Discord bot token  
- `pip install -r requirements.txt`

---

## 🚀 Run

```bash
git clone https://github.com/joanafmaia/discordtradutor.git
cd discordtradutor

# Add your token
echo "TOKEN=your_token_here" > .env
echo "DEFAULT_LANGUAGE=pt" >> .env

# Start the bot
python bot.py
