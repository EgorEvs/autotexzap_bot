import telebot
import requests
import re
import json
import os
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_TOKEN = os.getenv("API_TOKEN")
API_URL = 'https://autotechnik.store/api/v1/customers/'

bot = telebot.TeleBot(BOT_TOKEN)

LINKS_FILE = 'chat_links.json'
MANAGER_FILE = 'manager_ids.json'

def load_links():
    return json.load(open(LINKS_FILE)) if os.path.exists(LINKS_FILE) else {}

def save_links(data):
    with open(LINKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_managers():
    return json.load(open(MANAGER_FILE)) if os.path.exists(MANAGER_FILE) else {}

def save_managers(data):
    with open(MANAGER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def normalize_phone(phone):
    return re.sub(r'\D', '', phone)

def get_client_info(phone):
    try:
        response = requests.get(API_URL, params={'token': API_TOKEN, 'phone': phone})
        return response.json().get('result', [None])[0]
    except:
        return None

def get_manager_info(manager_id):
    try:
        response = requests.get(f'https://autotechnik.store/api/v2/shop/managers/{manager_id}')
        return response.json()
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("Отправить номер телефона", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "Чтобы начать, нажмите кнопку ниже и отправьте свой номер телефона:",
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    user_id = message.chat.id
    client = get_client_info(phone)

    if not client:
        bot.send_message(user_id, "Клиент с таким номером не найден.")
        return

    manager_login = client.get('managerLogin')
    managers = load_managers()
    manager_id = managers.get(manager_login)

    if not manager_id:
        bot.send_message(user_id, f"Менеджер ({manager_login}) пока не зарегистрирован в Telegram.")
        return

    fio = f"{client.get('surname', '')} {client.get('name', '')}".strip()
    office = client.get('officeName', 'не указано')

    bot.send_message(manager_id,
        f"Новое сообщение от клиента:\n\n"
        f"Имя: {fio}\n"
        f"Телефон: {phone}\n"
        f"Точка: {office}\n"
        f"Telegram ID: {user_id}"
    )
    bot.send_message(manager_id, f"(Сообщение выше пришло от клиента)")

    links = load_links()
    links[str(user_id)] = manager_id
    links[str(manager_id)] = user_id
    save_links(links)

    bot.send_message(user_id, f"Вы подключены к менеджеру {manager_login} ({office}). Можете продолжить общение.")

@bot.message_handler(commands=['register'])
def register_manager(message):
    try:
        manager_id = int(message.text.split(' ')[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Укажите ID менеджера, пример: /register 12")
        return

    data = get_manager_info(manager_id)
    if not data:
        bot.reply_to(message, "Ошибка при получении данных менеджера.")
        return

    login = data.get("managerLogin")
    name = data.get("managerName")
    office = data.get("officeName")

    if not login:
        bot.reply_to(message, "Логин менеджера не найден.")
        return

    managers = load_managers()
    managers[login] = message.chat.id
    save_managers(managers)

    bot.reply_to(
        message,
        f"Вы зарегистрированы как менеджер: {name} ({login})\nТочка: {office}"
    )

@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    links = load_links()
    user_id = str(message.chat.id)

    if user_id in links:
        peer_id = links[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
    else:
        bot.send_message(message.chat.id, "Сначала отправьте номер телефона через /start.")

bot.polling()
