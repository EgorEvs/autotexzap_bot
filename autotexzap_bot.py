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
    print(f"[DEBUG] Исходный номер: {phone}")
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
        formatted = f'+7({code}){part1}-{part2}-{part3}'
        print(f"[DEBUG] Преобразованный номер: {formatted}")
        return formatted
    return phone

def get_client_info(phone):
    try:
        print(f"[DEBUG] Запрос клиента по номеру: {phone}")
        response = requests.get(API_URL, params={'token': API_TOKEN, 'phone': phone})
        print(f"[DEBUG] Ответ API: {response.text}")
        return response.json().get('result', [None])[0]
    except Exception as e:
        print(f"[ERROR] Ошибка API: {e}")
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
    print(f"[INFO] Пользователь {message.chat.id} начал с /start")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    raw_phone = message.contact.phone_number
    phone = format_phone_to_database_style(raw_phone)
    user_id = message.chat.id
    print(f"[INFO] Пользователь {user_id} отправил номер: {raw_phone} → {phone}")

    client = get_client_info(phone)

    if not client:
        bot.send_message(user_id, f"Клиент с таким номером не найден: {phone}")
        print(f"[INFO] Клиент не найден: {phone}")
        return

    manager_login = client.get('managerLogin')
    managers = load_managers()
    manager_id = managers.get(manager_login)

    if not manager_id:
        bot.send_message(user_id, f"Менеджер ({manager_login}) пока не зарегистрирован в Telegram.")
        print(f"[INFO] Менеджер {manager_login} не зарегистрирован.")
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
    print(f"[INFO] Чат связан: {user_id} ↔ {manager_id}")

@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    links = load_links()
    user_id = str(message.chat.id)

    if user_id in links:
        peer_id = links[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
        print(f"[INFO] Сообщение от {user_id} переслано к {peer_id}")
    else:
        bot.send_message(message.chat.id, "Сначала отправьте номер телефона через /start.")
        print(f"[INFO] Неизвестный пользователь: {user_id}")

bot.polling()
