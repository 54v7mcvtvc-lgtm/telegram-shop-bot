import sqlite3
import telebot
from telebot import types

TOKEN = "8614023390:AAGQ4xtyhUH3aPmNWaXdDQeh4bbHOdsFbmQ"  # Твой актуальный токен
ADMIN_ID = 1610696013  # Твой Telegram ID

bot = telebot.TeleBot(TOKEN)


# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()

  # Таблица пользователей и баланса
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)

  # Таблица для динамических текстов бота
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

  # Устанавливаем текст пополнения по умолчанию (без слова Сбербанк)
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
      (
          "payment_text",
          "💳 Переведите нужную сумму на карту:\n2204 3204 7177 0653"
          " (Твое Имя)\nЗатем нажмите кнопку ниже.",
      ),
  )

  conn.commit()
  conn.close()


init_db()


def get_setting(key):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
  row = cursor.fetchone()
  conn.close()
  return row[0] if row else ""


def update_setting(key, value):
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
      (key, value),
  )
  conn.commit()
  conn.close()


# --- ОБРАБОТЧИК КОМАНДЫ /START ---
@bot.message_handler(commands=["start"])
def start_command(message):
  user_id = message.from_user.id
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,)
  )
  conn.commit()
  conn.close()

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.row(types.KeyboardButton("📥 Пополнить"), types.KeyboardButton("📤 Вывести"))
  markup.row(
      types.KeyboardButton("📦 История покупок"),
      types.KeyboardButton("🏠 Главное меню"),
  )

  bot.send_message(
      message.chat.id,
      "👋 Добро пожаловать в магазин цифровых товаров!",
      reply_markup=markup,
  )


# --- ПОПОЛНЕНИЕ БАЛАНСА ---
@bot.message_handler(
    func=lambda message: message.text in ["📥 Пополнить", "Главное меню"]
)
def deposit_handler(message):
  if message.text == "Главное меню":
    return start_command(message)

  msg = bot.send_message(
      message.chat.id,
      "Введите сумму, на которую хотите пополнить баланс (только число):",
  )
  bot.register_next_step_handler(msg, process_deposit_amount)


def process_deposit_amount(message):
  if not message.text.isdigit():
    msg = bot.send_message(
        message.chat.id, "Пожалуйста, введите корректное число:"
    )
    bot.register_next_step_handler(msg, process_deposit_amount)
    return

  amount = message.text

  # Берем актуальный текст из базы данных
  pay_template = get_setting("payment_text")
  # Заменяем автоматически сумму, если в тексте заложена динамика, либо выводим как есть
  text = f"{pay_template}\n\nСумма к оплате: {amount} ₽"

  markup = types.InlineKeyboardMarkup()
  markup.add(types.InlineKeyboardButton("✅ Я перевел деньги", callback_data="paid"))

  bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "paid")
def callback_paid(call):
  bot.answer_callback_query(
      call.id,
      "Заявка отправлена! Ожидайте зачисления средств администратором.",
  )
  bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
  bot.send_message(
      call.message.chat.id,
      "⏳ Ваш платеж проверяется. Баланс обновится после подтверждения.",
  )


# --- АДМИН-ПАНЕЛЬ И УПРАВЛЕНИЕ ТЕКСТАМИ ---
@bot.message_handler(commands=["admin"])
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")

  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "✏️ Изменить текст пополнения", callback_data="edit_pay_text"
      )
  )

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("SELECT COUNT(*) FROM users")
  users_count = cursor.fetchone()[0]
  conn.close()

  bot.send_message(
      message.chat.id,
      f"⚙️ **Панель администратора**\n\nВсего пользователей: {users_count}",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: call.data == "edit_pay_text")
def edit_pay_text_callback(call):
  if call.from_user.id != ADMIN_ID:
    return
  current_text = get_setting("payment_text")
  msg = bot.send_message(
      call.message.chat.id,
      f"Текущий текст пополнения:\n\n{current_text}\n\n👉 Отправьте мне **новый текст** для пополнения:",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(msg, save_new_pay_text)


def save_new_pay_text(message):
  if message.from_user.id != ADMIN_ID:
    return
  new_text = message.text
  update_setting("payment_text", new_text)
  bot.send_message(
      message.chat.id,
      "✅ Текст пополнения успешно изменен!\n\nТеперь пользователи будут видеть"
      " его при пополнении.",
  )


# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
  print("Бот запущен...")
  bot.remove_webhook()
  bot.infinity_polling()
