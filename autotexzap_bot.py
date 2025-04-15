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
    return json.load(open(LINKS_FILE)) if os.path.exists(LINKS_FILE) else {}

def save_links(data):
    with open(LINKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_managers():
    return json.load(open(MANAGER_FILE)) if os.path.exists(MANAGER_FILE) else {}

def save_managers(data):
    with open(MANAGER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def format_phone_to_database_style(phone):
    phone = phone.strip()
    if phone.startswith('+7') and len(phone) == 12:
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

def get_manager_info(manager_id):
    try:
        response = requests.get(f'https://autotechnik.store/api/v2/shop/managers/{manager_id}')
        return response.json()
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("РћС‚РїСЂР°РІРёС‚СЊ РЅРѕРјРµСЂ С‚РµР»РµС„РѕРЅР°", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "Р§С‚РѕР±С‹ РЅР°С‡Р°С‚СЊ, РЅР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РЅРёР¶Рµ Рё РѕС‚РїСЂР°РІСЊС‚Рµ СЃРІРѕР№ РЅРѕРјРµСЂ С‚РµР»РµС„РѕРЅР°:",
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    raw_phone = message.contact.phone_number
    phone = format_phone_to_database_style(raw_phone)
    user_id = message.chat.id
    client = get_client_info(phone)

    if not client:
        bot.send_message(user_id, f"РљР»РёРµРЅС‚ СЃ С‚Р°РєРёРј РЅРѕРјРµСЂРѕРј РЅРµ РЅР°Р№РґРµРЅ: {phone}")
        return

    manager_login = client.get('managerLogin')
    managers = load_managers()
    manager_id = managers.get(manager_login)

    if not manager_id:
        bot.send_message(user_id, f"РњРµРЅРµРґР¶РµСЂ ({manager_login}) РїРѕРєР° РЅРµ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅ РІ Telegram.")
        return

    fio = f"{client.get('surname', '')} {client.get('name', '')}".strip()
    office = client.get('officeName', 'РЅРµ СѓРєР°Р·Р°РЅРѕ')

    bot.send_message(manager_id,
        f"РќРѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ РѕС‚ РєР»РёРµРЅС‚Р°:\n\n"
        f"РРјСЏ: {fio}\n"
        f"РўРµР»РµС„РѕРЅ: {phone}\n"
        f"РўРѕС‡РєР°: {office}\n"
        f"Telegram ID: {user_id}"
    )
    bot.send_message(manager_id, f"(РЎРѕРѕР±С‰РµРЅРёРµ РІС‹С€Рµ РїСЂРёС€Р»Рѕ РѕС‚ РєР»РёРµРЅС‚Р°)")

    links = load_links()
    links[str(user_id)] = manager_id
    links[str(manager_id)] = user_id
    save_links(links)

    bot.send_message(user_id, f"Р’С‹ РїРѕРґРєР»СЋС‡РµРЅС‹ Рє РјРµРЅРµРґР¶РµСЂСѓ {manager_login} ({office}). РњРѕР¶РµС‚Рµ РїСЂРѕРґРѕР»Р¶РёС‚СЊ РѕР±С‰РµРЅРёРµ.")

@bot.message_handler(commands=['register'])
def register_manager(message):
    try:
        manager_id = int(message.text.split(' ')[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "РЈРєР°Р¶РёС‚Рµ ID РјРµРЅРµРґР¶РµСЂР°, РїСЂРёРјРµСЂ: /register 12")
        return

    data = get_manager_info(manager_id)
    if not data:
        bot.reply_to(message, "РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РґР°РЅРЅС‹С… РјРµРЅРµРґР¶РµСЂР°.")
        return

    login = data.get("managerLogin")
    name = data.get("managerName")
    office = data.get("officeName")

    if not login:
        bot.reply_to(message, "Р›РѕРіРёРЅ РјРµРЅРµРґР¶РµСЂР° РЅРµ РЅР°Р№РґРµРЅ.")
        return

    managers = load_managers()
    managers[login] = message.chat.id
    save_managers(managers)

    bot.reply_to(
        message,
        f"Р’С‹ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅС‹ РєР°Рє РјРµРЅРµРґР¶РµСЂ: {name} ({login})\nРўРѕС‡РєР°: {office}"
    )

@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    links = load_links()
    user_id = str(message.chat.id)

    if user_id in links:
        peer_id = links[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
    else:
        bot.send_message(message.chat.id, "РЎРЅР°С‡Р°Р»Р° РѕС‚РїСЂР°РІСЊС‚Рµ РЅРѕРјРµСЂ С‚РµР»РµС„РѕРЅР° С‡РµСЂРµР· /start.")

bot.polling()
