import telebot
import config
import re
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# ====== /start ======
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🎲 Рандомное число"),
        types.KeyboardButton("😊 Как дела?")
    )

    username = message.from_user.first_name
    bot.send_message(
        message.chat.id,
        f"Привет, {username}! Я антиспам бот.",
        reply_markup=markup
    )


# ====== АНТИСПАМ ======

violations = {}

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


PATTERNS = [
    r"заработ",
    r"доход",
    r"инвест",
    r"крипт",
    r"пиши.*(личк|лс|директ)",
    r"http",
    r"t\.me",
    r"@\w+",
    r"\$\d+",
]


def spam_score(text):
    score = 0

    for pattern in PATTERNS:
        if re.search(pattern, text):
            score += 1

    return score


def is_spam(text):
    text = normalize(text)
    return spam_score(text) >= 1


# ====== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ======
@bot.message_handler(content_types=['text'])
def handle_message(message):

    if not message.text:
        return

    if message.from_user.is_bot:
        return

    text = message.text

    if is_spam(text):
        try:
            bot.delete_message(message.chat.id, message.message_id)

            user_id = message.from_user.id
            violations[user_id] = violations.get(user_id, 0) + 1

            bot.send_message(
                message.chat.id,
                f"{message.from_user.first_name}, спам запрещён!"
            )

            if violations[user_id] >= 2:
                bot.ban_chat_member(message.chat.id, user_id)
                bot.send_message(
                    message.chat.id,
                    f"{message.from_user.first_name} забанен 🚫"
                )

        except Exception as e:
            print("Ошибка:", e)


# ====== ЗАПУСК ======
bot.polling(none_stop=True)