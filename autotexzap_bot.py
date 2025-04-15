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
    return json.load(open(filename, encoding="utf-8")) if os.path.exists(filename) else {}

def save_json_file(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    is_manager = str(message.chat.id) in load_json_file(MANAGER_FILE).values()
    text = "📖 <b>Доступные команды:</b>
"
    if is_manager:
        text += "/clients - список клиентов
/stop - завершить текущий диалог"
    else:
        text += "/start - начать работу
Отправьте номер телефона для подключения"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start(message):
    is_manager = str(message.chat.id) in load_json_file(MANAGER_FILE).values()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if is_manager:
        markup.add("🧍 Мои клиенты", "⛔ Завершить диалог")
    else:
        button = types.KeyboardButton("📲 Отправить номер", request_contact=True)
        markup.add(button)
    bot.send_message(message.chat.id, "Добро пожаловать!", reply_markup=markup)

@bot.message_handler(commands=['register_login'])
def register_login(message):
    try:
        login = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Пример: /register_login ivanov")
        return
    managers = load_json_file(MANAGER_FILE)
    managers[login] = message.chat.id
    save_json_file(managers, MANAGER_FILE)
    bot.send_message(message.chat.id, f"Менеджер {login} зарегистрирован.")

@bot.message_handler(commands=['clients'])
def show_clients(message):
    links = load_json_file(LINKS_FILE)
    manager_id = str(message.chat.id)
    clients = [uid for uid, mid in links.items() if mid == int(manager_id) and uid != manager_id]
    if not clients:
        bot.send_message(message.chat.id, "Нет подключённых клиентов.")
        return
    markup = types.InlineKeyboardMarkup()
    for cid in clients:
        markup.add(types.InlineKeyboardButton(f"Клиент {cid}", callback_data=f"dialog:{cid}"))
    bot.send_message(message.chat.id, "Выберите клиента:", reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop(message):
    dialogs = load_json_file(ACTIVE_DIALOGS)
    if str(message.chat.id) in dialogs:
        del dialogs[str(message.chat.id)]
        save_json_file(dialogs, ACTIVE_DIALOGS)
        bot.send_message(message.chat.id, "❌ Диалог завершён.")
    else:
        bot.send_message(message.chat.id, "Нет активного диалога.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("dialog:"))
def start_dialog(call):
    client_id = call.data.split(":")[1]
    manager_id = str(call.message.chat.id)
    dialogs = load_json_file(ACTIVE_DIALOGS)
    dialogs[manager_id] = client_id
    save_json_file(dialogs, ACTIVE_DIALOGS)
    bot.send_message(manager_id, f"✅ Вы перешли в диалог с клиентом {client_id}.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("clientdialog:"))
def client_start_dialog(call):
    manager_id = call.data.split(":")[1]
    client_id = str(call.message.chat.id)
    dialogs = load_json_file(ACTIVE_DIALOGS)
    dialogs[client_id] = manager_id
    save_json_file(dialogs, ACTIVE_DIALOGS)
    bot.send_message(call.message.chat.id, f"✅ Вы перешли в диалог с менеджером.")

@bot.message_handler(content_types=['contact'])
def contact(message):
    phone = message.contact.phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("7") and not phone.startswith("+7"):
        phone = "+7" + phone[1:]
    if phone.startswith("+7") and len(phone) == 12:
        phone = f'+7({phone[2:5]}){phone[5:8]}-{phone[8:10]}-{phone[10:]}'

    user_id = message.chat.id
    response = requests.get(API_URL, params={'token': API_TOKEN, 'phone': phone})
    client = response.json().get('result', [None])[0]
    if not client:
        bot.send_message(user_id, "Клиент не найден.")
        return

    fio = f"{client.get('surname', '')} {client.get('name', '')}".strip()
    office = client.get('officeName', 'не указано')
    manager_login = client.get("managerLogin")
    managers = load_json_file(MANAGER_FILE)
    manager_id = managers.get(manager_login)
    if not manager_id:
        bot.send_message(user_id, "Менеджер не зарегистрирован в Telegram.")
        return

    links = load_json_file(LINKS_FILE)
    links[str(user_id)] = manager_id
    links[str(manager_id)] = user_id
    save_json_file(links, LINKS_FILE)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔁 Перейти в диалог с менеджером", callback_data=f"clientdialog:{manager_id}"))
    bot.send_message(user_id, f"✅ Вы подключены к менеджеру {manager_login} ({office}).", reply_markup=markup)

    manager_markup = types.InlineKeyboardMarkup()
    manager_markup.add(types.InlineKeyboardButton(f"🔁 Перейти в диалог с {fio}", callback_data=f"dialog:{user_id}"))
    bot.send_message(manager_id, f"""📬 Новый клиент:

👤 {fio}
📞 {phone}
🆔 Telegram ID: {user_id}
""", reply_markup=manager_markup)

@bot.message_handler(func=lambda m: True)
def relay(message):
    dialogs = load_json_file(ACTIVE_DIALOGS)
    user_id = str(message.chat.id)
    if user_id in dialogs:
        peer_id = dialogs[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
        return
    links = load_json_file(LINKS_FILE)
    if user_id in links:
        peer_id = links[user_id]
        bot.copy_message(peer_id, message.chat.id, message.message_id)
    else:
        bot.send_message(message.chat.id, "ℹ️ Сначала отправьте номер или выберите клиента.")

bot.polling()
