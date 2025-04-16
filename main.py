import os
import json
from flask import Flask, request
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

LINKS_FILE = "client_links.json"

def load_links():
    return json.load(open(LINKS_FILE, encoding="utf-8")) if os.path.exists(LINKS_FILE) else {}

def save_links(data):
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    phone = normalize_phone(data.get("phone", ""))
    chat_id = data.get("chat_id")
    if not phone or not chat_id:
        return {"status": "error", "message": "phone and chat_id required"}, 400
    links = load_links()
    links[phone] = chat_id
    save_links(links)
    return {"status": "ok"}

def normalize_phone(phone):
    return phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+7", "8").strip()

@app.route("/status_notify", methods=["POST"])
def status_notify():
    data = request.json
    phone = normalize_phone(data.get("phone", ""))
    order_id = data.get("order_id", "")
    status = data.get("status", "").strip()

    links = load_links()
    chat_id = links.get(phone)

    if not chat_id:
        return {"status": "error", "message": "Клиент не найден"}, 404

    if status == "Готов к выдаче":
        text = f"📦 Ваш заказ №{order_id} готов к выдаче. Срок хранения — 7 дней."
    elif status == "Выдано":
        text = f"✅ Заказ №{order_id} выдан. Вы можете вернуть товар в течение 7 дней."
    elif status == "Готово к выдаче 3 дня":
        text = f"🕒 Ваш заказ №{order_id} всё ещё ждёт вас на пункте выдачи."
    elif status in ["Отказ клиента", "Отказ поставщика"]:
        text = f"❗ Заказ №{order_id} отменён ({status}). Подробности уточните у менеджера."
    else:
        return {"status": "ignored", "message": "Статус не поддерживается"}, 200

    bot.send_message(chat_id, text)
    return {"status": "sent"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
