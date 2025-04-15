import telebot
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    print(f"[DEBUG] Получена команда /start от {message.chat.id}")
    bot.send_message(message.chat.id, "👋 Привет! Бот работает ✅")

bot.polling()
