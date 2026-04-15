import telebot
import config
import re
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# =====================
# НАСТРОЙКИ
# =====================

ban_limit = 2

admin_state = {}      # состояния админа (пароль / ввод лимита)
banned_users = {}      # список банов
violations = {}        # нарушения пользователей


# =====================
# /start
# =====================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! Я антиспам бот."
    )


# =====================
# НОРМАЛИЗАЦИЯ
# =====================

def normalize(text):
    text = text.lower()

    replacements = {
        "0": "о",
        "1": "и",
        "@": "а",
        "$": "с"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r"\s+", "", text)
    return text


# =====================
# СПАМ ПАТТЕРНЫ
# =====================

PATTERNS = [
    r"заработ\w*",
    r"доход",
    r"инвест",
    r"крипт",
    r"пиши.*(личк|лс|директ)",
    r"http",
    r"t\.me",
    r"@\w+",
    r"\$\d+",
]


def is_spam(text):
    text = normalize(text)

    score = 0
    for pattern in PATTERNS:
        if re.search(pattern, text):
            score += 1

    return score >= 1


# =====================
# ADMIN PANEL UI
# =====================

def admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("⚙️ Лимит банов", callback_data="set_limit")
    btn2 = types.InlineKeyboardButton("🚫 Забаненные", callback_data="banned_list")

    markup.add(btn1)
    markup.add(btn2)

    bot.send_message(chat_id, "🔐 Админ-панель:", reply_markup=markup)


# =====================
# /admin
# =====================

@bot.message_handler(commands=['admin'])
def admin(message):
    admin_state[message.from_user.id] = "wait_password"
    bot.send_message(message.chat.id, "Введите пароль:")


# =====================
# CALLBACK КНОПКИ
# =====================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    global ban_limit

    if call.data == "set_limit":
        admin_state[call.from_user.id] = "wait_limit"
        bot.send_message(call.message.chat.id,
                         "Введите новое количество предупреждений:")
        return

    if call.data == "banned_list":

        if not banned_users:
            bot.send_message(call.message.chat.id, "Список пуст ✅")
            return

        text = "🚫 Забаненные пользователи:\n\n"

        for uid, info in banned_users.items():
            text += f"- {info['name']} (@{info['username']}) | ID: {uid}\n"

        bot.send_message(call.message.chat.id, text)


# =====================
# ГЛАВНЫЙ ОБРАБОТЧИК
# =====================

@bot.message_handler(content_types=['text'])
def handle(message):

    global ban_limit

    user_id = message.from_user.id

    # =====================
    # АДМИН ЛОГИКА
    # =====================

    if user_id in admin_state:

        state = admin_state[user_id]

        # ---- пароль ----
        if state == "wait_password":

            if message.text == config.ADMIN_PASSWORD:
                admin_state.pop(user_id)
                admin_menu(message.chat.id)
            else:
                admin_state.pop(user_id)
                bot.send_message(message.chat.id, "Неверный пароль ❌")

            return

        # ---- лимит ----
        if state == "wait_limit":

            if message.text.isdigit():
                ban_limit = int(message.text)

                admin_state.pop(user_id)

                bot.send_message(
                    message.chat.id,
                    f"Готово ✅ Бан после {ban_limit} предупреждений"
                )
            else:
                bot.send_message(message.chat.id, "Введите число")

            return

    # =====================
    # АНТИСПАМ
    # =====================

    if message.from_user.is_bot:
        return

    if not message.text:
        return

    if is_spam(message.text):

        try:
            bot.delete_message(message.chat.id, message.message_id)

            violations[user_id] = violations.get(user_id, 0) + 1

            remaining = max(0, ban_limit - violations[user_id])

            bot.send_message(
                message.chat.id,
                f"{message.from_user.first_name}, спам запрещён! Осталось попыток: {remaining}"
            )

            if violations[user_id] >= ban_limit:
                bot.ban_chat_member(message.chat.id, user_id)

                banned_users[user_id] = {
                    "name": message.from_user.first_name,
                    "username": message.from_user.username
                }

                bot.send_message(
                    message.chat.id,
                    f"{message.from_user.first_name} забанен 🚫"
                )

        except Exception as e:
            print("Ошибка:", e)


# =====================
# ЗАПУСК
# =====================

bot.polling(none_stop=True)