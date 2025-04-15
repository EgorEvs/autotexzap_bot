import telebot
import requests
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
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_links(data):
    with open(LINKS_FILE, 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_managers():
    if os.path.exists(MANAGER_FILE):
        with open(MANAGER_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_managers(data):
    with open(MANAGER_FILE, 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_phone_to_database_style(phone):
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("7") and not phone.startswith("+7"):
        phone = "+7" + phone[1:]
    if phone.startswith("+7") and len(phone) == 12:
        code = phone[2:5]
        part1 = phone[5:8]
        part2 = phone[8:10]
        part3 = phone[10:]
        return f'+7({code}){part1}-{part2}-{part3}'
    return phone

def get_client_info(phone):
    try:
        response = requests.get(API_URL, params={'token': API_TOKEN, 'phone': phone})
        return response.json().get('result', [None])[0]
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

@bot.message_handler(commands=['register_login'])
def register_login_manual(message):
    try:
        login = message.text.split(' ')[1].strip()
    except IndexError:
        bot.reply_to(message, "Укажите логин менеджера, пример: /register_login ivanov")
        return

    managers = load_managers()
    managers[login] = message.chat.id
    save_managers(managers)

    bot.reply_to(message, f"Вы зарегистрированы как менеджер: {login}")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    raw_phone = message.contact.phone_number
    phone = format_phone_to_database_style(raw_phone)
    user_id = message.chat.id
    client = get_client_info(phone)

    if not client:
        bot.send_message(user_id, f"Клиент с таким номером не найден: {phone}")
        return

    manager_login = client.get('managerLogin')
    managers = load_managers()
    manager_id = managers.get(manager_login)

    old_links = load_links()
    old_manager_id = old_links.get(str(user_id))
    if old_manager_id and old_manager_id != manager_id:
        bot.send_message(old_manager_id,
            f"⚠️ Клиент {phone} теперь прикреплён к другому менеджеру: {manager_login}")

    if not manager_id:
        bot.send_message(user_id, f"Менеджер ({manager_login}) пока не зарегистрирован в Telegram.")
        return

    fio = f"{client.get('surname', '')} {client.get('name', '')}".strip()
    office = client.get('officeName', 'не указано')

    bot.send_message(manager_id,
        f"📩 Новое сообщение от клиента:

"
        f"👤 Имя: {fio}
"
        f"📞 Телефон: {phone}
"
        f"🏢 Точка: {office}
"
        f"🆔 Telegram ID клиента: {user_id}"
    )
    bot.send_message(manager_id, f"(Выше — информация о клиенте)")

    old_links[str(user_id)] = manager_id
    old_links[str(manager_id)] = user_id
    save_links(old_links)

    bot.send_message(user_id, f"Вы подключены к менеджеру {manager_login} ({office}). Можете начать общение.")

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
