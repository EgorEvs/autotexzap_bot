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
ACTIVE_DIALOGS = 'active_dialogs.json'

def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json_file(data, filename):
    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bot.message_handler(commands=['start'])
def start(message):
    print(f"[DEBUG] Получена команда /start от {message.chat.id}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("Отправить номер телефона", request_contact=True)
    markup.add(button)
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать! Нажмите кнопку ниже и отправьте свой номер телефона:",
        reply_markup=markup
    )

@bot.message_handler(commands=['register_login'])
def register_login_manual(message):
    try:
        login = message.text.split(' ')[1].strip()
    except IndexError:
        bot.reply_to(message, "⚠️ Укажите логин менеджера, пример: /register_login ivanov")
        return

    managers = load_json_file(MANAGER_FILE)
    managers[login] = message.chat.id
    save_json_file(managers, MANAGER_FILE)

    bot.reply_to(message, f"✅ Вы зарегистрированы как менеджер: {login}")
    print(f"[DEBUG] Менеджер зарегистрирован: {login} → {message.chat.id}")

@bot.message_handler(commands=['stop'])
def stop_dialog(message):
    dialogs = load_json_file(ACTIVE_DIALOGS)
    if str(message.chat.id) in dialogs:
        del dialogs[str(message.chat.id)]
        save_json_file(dialogs, ACTIVE_DIALOGS)
        bot.send_message(message.chat.id, "❌ Диалог завершён.")
    else:
        bot.send_message(message.chat.id, "У вас нет активного диалога.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("dialog:"))
def handle_dialog_start(call):
    client_id = call.data.split(":")[1]
    manager_id = str(call.message.chat.id)

    dialogs = load_json_file(ACTIVE_DIALOGS)
    dialogs[manager_id] = client_id
    save_json_file(dialogs, ACTIVE_DIALOGS)

    bot.send_message(call.message.chat.id, f"""✅ Вы перешли в диалог с клиентом {client_id}.
Все ваши сообщения теперь будут отправляться ему.
Напишите /stop чтобы завершить диалог.""")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    raw_phone = message.contact.phone_number
    phone = raw_phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("7") and not phone.startswith("+7"):
        phone = "+7" + phone[1:]
    if phone.startswith("+7") and len(phone) == 12:
        code = phone[2:5]
        part1 = phone[5:8]
        part2 = phone[8:10]
        part3 = phone[10:]
        phone = f'+7({code}){part1}-{part2}-{part3}'

    user_id = message.chat.id
    response = requests.get(API_URL, params={'token': API_TOKEN, 'phone': phone})
    try:
        client = response.json().get('result', [None])[0]
    except:
        client = None

    if not client:
        bot.send_message(user_id, f"⚠️ Клиент с таким номером не найден: {phone}")
        print(f"[DEBUG] Клиент не найден: {phone}")
        return

    manager_login = client.get('managerLogin')
    fio = f"{client.get('surname', '')} {client.get('name', '')}".strip()
    office = client.get('officeName', 'не указано')

    managers = load_json_file(MANAGER_FILE)
    manager_id = managers.get(manager_login)

    if not manager_id:
        bot.send_message(user_id, f"⚠️ Менеджер ({manager_login}) не зарегистрирован в Telegram.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🔁 Перейти в диалог с {fio}", callback_data=f"dialog:{user_id}"))

    bot.send_message(manager_id, f"""📬 Новый клиент подключился:

👤 {fio}
📞 {phone}
🆔 Telegram ID: {user_id}
""", reply_markup=markup)

    links = load_json_file(LINKS_FILE)
    links[str(user_id)] = manager_id
    links[str(manager_id)] = user_id
    save_json_file(links, LINKS_FILE)

    bot.send_message(user_id, f"✅ Вы подключены к менеджеру {manager_login} ({office}). Можете начать общение.")
    print(f"[DEBUG] Связка установлена: клиент {user_id} ↔ менеджер {manager_id}")

@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    user_id = str(message.chat.id)
    dialogs = load_json_file(ACTIVE_DIALOGS)

    if user_id in dialogs:
        client_id = dialogs[user_id]
        bot.copy_message(client_id, message.chat.id, message.message_id)
        return

    links = load_json_file(LINKS_FILE)
    if user_id in links:
        peer_id = links[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
    else:
        bot.send_message(message.chat.id, "ℹ️ Сначала отправьте номер телефона через /start.")

bot.polling()
