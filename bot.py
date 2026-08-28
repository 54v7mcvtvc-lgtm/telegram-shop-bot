import sqlite3
from datetime import datetime
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ================= НАСТРОЙКИ =================
TOKEN = "8614023390:AAGQ4xtyhUH3aPmNWaXdDQeh4bbHOdsFbmQ"
ADMIN_ID = 1610696013
PAYMENT_DETAILS = "2204 3204 7177 0653"
bot = telebot.TeleBot(TOKEN)

APPLE_DENOMINATIONS = {
    "TRY": [10, 50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500],
    "USD": [1, 2, 3, 4, 5, 10, 15, 20, 50, 100],
    "EUR": [1, 5, 10, 20, 50, 100],
    "INR": [100, 200, 250, 500, 1000, 1500, 2000, 2500],
}


# ================= БАЗА ДАННЫХ ===============
def init_db():
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance"
        " INTEGER DEFAULT 0, joined_date TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS prices (item_key TEXT PRIMARY KEY, price"
        " INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY"
        " AUTOINCREMENT, item_key TEXT, code TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS history (user_id INTEGER, item_name TEXT,"
        " code TEXT, price INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS custom_categories (name TEXT PRIMARY KEY)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS custom_products (id INTEGER PRIMARY KEY"
        " AUTOINCREMENT, category_name TEXT, name TEXT, price INTEGER)"
    )

    try:
      c.execute("ALTER TABLE history ADD COLUMN purchase_time TEXT")
    except sqlite3.OperationalError:
      pass

    try:
      c.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")
    except sqlite3.OperationalError:
      pass

    c.execute('SELECT count(*) FROM settings WHERE key = "rules"')
    if c.fetchone()[0] == 0:
      default_rules = (
          "📖 **Правила магазина и FAQ**\n\n"
          "**1. Гарантия:** Мы гарантируем 100% валидность всех выдаваемых кодов"
          " на момент покупки.\n"
          "**2. Активация:** Пожалуйста, активируйте код сразу после его"
          " получения.\n"
          "**3. Предзаказ:** Если нужного номинала нет, вы можете оформить"
          " заказ. Среднее время выдачи — 15-30 минут.\n\n"
          "📞 **Поддержка:** По всем вопросам обращайтесь к нашему менеджеру:"
          " **@Djabrail050**"
      )
      c.execute(
          'INSERT INTO settings (key, value) VALUES ("rules", ?)',
          (default_rules,),
      )

    c.execute("SELECT count(*) FROM prices")
    if c.fetchone()[0] == 0:
      rates = {"TRY": 2.2, "USD": 100.0, "EUR": 150.0, "INR": 1.2}
      for curr, denoms in APPLE_DENOMINATIONS.items():
        for nom in denoms:
          item_key = f"apple_{curr}_{nom}"
          price = int(nom * rates[curr])
          c.execute(
              "INSERT INTO prices (item_key, price) VALUES (?, ?)",
              (item_key, price),
          )
    conn.commit()


def get_balance(user_id):
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    if result is None:
      current_date = datetime.now().strftime("%Y-%m-%d")
      c.execute(
          "INSERT INTO users (id, balance, joined_date) VALUES (?, 0, ?)",
          (user_id, current_date),
      )
      conn.commit()
      return 0
    return result[0]


def change_balance(user_id, amount):
  balance = get_balance(user_id)
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute(
        "UPDATE users SET balance = ? WHERE id = ?", (balance + amount, user_id)
    )
    conn.commit()


def get_price(item_key):
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute("SELECT price FROM prices WHERE item_key = ?", (item_key,))
    res = c.fetchone()
    return res[0] if res else 999999


def set_price(item_key, new_price):
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute(
        "UPDATE prices SET price = ? WHERE item_key = ?", (new_price, item_key)
    )
    conn.commit()


def get_stock_count(item_key):
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute("SELECT count(*) FROM codes WHERE item_key = ?", (item_key,))
    return c.fetchone()[0]


def get_rules():
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = "rules"')
    res = c.fetchone()
    return res[0] if res else "Правила не установлены."


def set_rules(new_rules):
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute(
        'UPDATE settings SET value = ? WHERE key = "rules"', (new_rules,)
    )
    conn.commit()


init_db()


# --- КЛАВИАТУРЫ ---
def get_main_menu():
  markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(KeyboardButton("🛒 Купить"), KeyboardButton("👤 Профиль"))
  markup.add(KeyboardButton("ℹ️ Правила магазина"))
  return markup


def get_products_menu():
  markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      KeyboardButton("App Store & iTunes 🍏"),
      KeyboardButton("PUBG Mobile UC 🔫"),
  )
  markup.add(KeyboardButton("Steam пополнение 🎮"))

  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM custom_categories")
    cats = c.fetchall()
    for cat in cats:
      markup.add(KeyboardButton(cat[0]))

  markup.add(KeyboardButton("⬅️ Главное меню"))
  return markup


def get_profile_menu():
  markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(KeyboardButton("⬇️ Пополнить"), KeyboardButton("⬆️ Вывести"))
  markup.add(
      KeyboardButton("📜 История покупок"), KeyboardButton("⬅️ Главное меню")
  )
  return markup


def is_menu_button(text):
  if text.startswith("/"):
    return True
  menu_buttons = [
      "🛒 Купить",
      "👤 Профиль",
      "ℹ️ Правила магазина",
      "⬅️ Главное меню",
      "App Store & iTunes 🍏",
      "PUBG Mobile UC 🔫",
      "Steam пополнение 🎮",
      "⬇️ Пополнить",
      "⬆️ Вывести",
      "📜 История покупок",
  ]
  if text in menu_buttons:
    return True

  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    c.execute("SELECT count(*) FROM custom_categories WHERE name = ?", (text,))
    if c.fetchone()[0] > 0:
      return True

  return False


def get_apple_currency_menu():
  markup = InlineKeyboardMarkup(row_width=2)
  markup.add(
      InlineKeyboardButton("Турция (TRY) 🇹🇷", callback_data="apple_curr_TRY"),
      InlineKeyboardButton("США (USD) 🇺🇸", callback_data="apple_curr_USD"),
      InlineKeyboardButton("Европа (EUR) 🇪🇺", callback_data="apple_curr_EUR"),
      InlineKeyboardButton("Индия (INR) 🇮🇳", callback_data="apple_curr_INR"),
      InlineKeyboardButton("❌ Закрыть", callback_data="close_menu"),
  )
  return markup


def get_denominations_menu(currency):
  markup = InlineKeyboardMarkup(row_width=2)
  denominations = APPLE_DENOMINATIONS[currency]

  buttons = []
  for nom in denominations:
    item_key = f"apple_{currency}_{nom}"
    price = get_price(item_key)
    stock = get_stock_count(item_key)

    btn_text = f"{nom} {currency} — {price} ₽"

    if stock > 0:
      callback = f"confirm_apple_{currency}_{nom}"
    else:
      callback = f"preconfirm_apple_{currency}_{nom}"

    buttons.append(InlineKeyboardButton(btn_text, callback_data=callback))

  markup.add(*buttons)
  markup.add(
      InlineKeyboardButton(
          "⬅️ Назад к валютам", callback_data="apple_back"
      )
  )
  return markup


# ================= ОБРАБОТЧИКИ ТЕКСТА =================
@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.clear_step_handler_by_chat_id(message.chat.id)
  get_balance(message.from_user.id)
  bot.send_message(
      message.chat.id,
      f"Привет, {message.from_user.first_name}! Добро пожаловать.",
      reply_markup=get_main_menu(),
  )


@bot.message_handler(commands=["admin"])
def admin_panel(message):
  bot.clear_step_handler_by_chat_id(message.chat.id)
  if message.from_user.id != ADMIN_ID:
    return

  markup = InlineKeyboardMarkup(row_width=2)
  markup.add(
      InlineKeyboardButton(
          "💰 Цены (Вручную)", callback_data="admin_price_cats"
      ),
      InlineKeyboardButton("💱 Изменить курс", callback_data="admin_rate_cats"),
  )
  markup.add(
      InlineKeyboardButton("🔑 Загрузить код", callback_data="admin_add_code"),
      InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
  )
  markup.add(
      InlineKeyboardButton(
          "📂 Создать категорию", callback_data="admin_add_cat"
      ),
      InlineKeyboardButton("📦 Создать товар", callback_data="admin_add_prod"),
  )
  markup.add(
      InlineKeyboardButton(
          "➕ Выдать баланс", callback_data="admin_add_balance"
      ),
      InlineKeyboardButton(
          "📝 Изменить правила", callback_data="admin_edit_rules"
      ),
  )
  bot.send_message(
      message.chat.id,
      "🛠 **Админ-панель магазина**",
      parse_mode="Markdown",
      reply_markup=markup,
  )


@bot.message_handler(content_types=["text"])
def handle_text(message):
  bot.clear_step_handler_by_chat_id(message.chat.id)
  text = message.text
  get_balance(message.from_user.id)

  if text == "🛒 Купить":
    bot.send_message(
        message.chat.id,
        "Выберите категорию товаров:",
        reply_markup=get_products_menu(),
    )

  elif text == "👤 Профиль":
    balance = get_balance(message.from_user.id)
    bot.send_message(
        message.chat.id,
        f"👤 **Профиль:** {message.from_user.first_name}\n🆔 **ID:**"
        f" `{message.from_user.id}`\n💰 **Ваш баланс:** {balance} ₽",
        parse_mode="Markdown",
        reply_markup=get_profile_menu(),
    )

  elif text == "⬅️ Главное меню":
    bot.send_message(
        message.chat.id,
        "Вы вернулись в главное меню.",
        reply_markup=get_main_menu(),
    )

  elif text == "ℹ️ Правила магазина":
    rules_text = get_rules()
    bot.send_message(message.chat.id, rules_text, parse_mode="Markdown")

  elif text == "📜 История покупок":
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "SELECT item_name, code, price, purchase_time FROM history WHERE"
          " user_id = ? ORDER BY rowid DESC LIMIT 30",
          (message.from_user.id,),
      )
      rows = c.fetchall()
      if not rows:
        bot.send_message(
            message.chat.id, "Вы еще ничего не покупали в нашем магазине 😔"
        )
      else:
        history_text = "📜 **Ваши последние покупки:**\n\n"
        for i, row in enumerate(rows, 1):
          item_name = row[0].replace(" (Заказ)", "")
          code_val = row[1]
          price = row[2]
          p_time = row[3] if row[3] else "Неизвестно"

          history_text += f"*{i}. {item_name}* — {price} ₽\n📅 {p_time}\n"

          if code_val and code_val != "[Ожидает выдачи менеджером]":
            history_text += f"Код: `{code_val}`\n"

          history_text += "\n"
        bot.send_message(
            message.chat.id, history_text, parse_mode="Markdown"
        )

  elif text == "App Store & iTunes 🍏":
    bot.send_message(
        message.chat.id,
        "Выбери валюту для App Store & iTunes:",
        reply_markup=get_apple_currency_menu(),
    )

  elif text in ["PUBG Mobile UC 🔫", "Steam пополнение 🎮"]:
    bot.send_message(
        message.chat.id,
        "🚧 Раздел находится в разработке! Используйте добавление собственных"
        " категорий через админ-панель.",
    )

  elif text == "⬇️ Пополнить":
    msg = bot.send_message(
        message.chat.id,
        "Введите сумму, на которую хотите пополнить баланс (только число):",
    )
    bot.register_next_step_handler(msg, process_topup_amount)

  elif text == "⬆️ Вывести":
    balance = get_balance(message.from_user.id)
    if balance <= 0:
      bot.send_message(
          message.chat.id, "❌ На вашем балансе нет средств для вывода."
      )
    else:
      msg = bot.send_message(
          message.chat.id,
          f"Ваш баланс: **{balance} ₽**\n\nВведите сумму для вывода (только"
          " число):",
          parse_mode="Markdown",
      )
      bot.register_next_step_handler(msg, process_withdraw_amount, balance)

  else:
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name FROM custom_categories WHERE name = ?", (text,))
      if c.fetchone():
        c.execute(
            "SELECT id, name, price FROM custom_products WHERE category_name ="
            " ?",
            (text,),
        )
        products = c.fetchall()
        if not products:
          bot.send_message(
              message.chat.id,
              "В этой категории пока нет товаров. Скоро появятся!",
          )
          return

        markup = InlineKeyboardMarkup(row_width=1)
        for p in products:
          stock = get_stock_count(f"custom_{p[0]}")
          status = "✅ В наличии" if stock > 0 else "⏳ Под заказ"
          markup.add(
              InlineKeyboardButton(
                  f"{p[1]} ({p[2]} ₽) | {status}",
                  callback_data=f"buy_custom_{p[0]}",
              )
          )
        markup.add(InlineKeyboardButton("❌ Закрыть", callback_data="close_menu"))

        bot.send_message(
            message.chat.id,
            f"📦 **Категория:** {text}\nВыберите товар:",
            reply_markup=markup,
            parse_mode="Markdown",
        )


# ================= ОБРАБОТЧИКИ КНОПОК =================
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
  if call.data == "close_menu":
    bot.delete_message(call.message.chat.id, call.message.message_id)

  elif call.data == "apple_back":
    bot.edit_message_text(
        "Выбери валюту для App Store & iTunes:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_apple_currency_menu(),
    )

  elif call.data.startswith("apple_curr_"):
    currency = call.data.split("_")[2]
    bot.edit_message_text(
        f"Выбрана валюта: {currency}. Выбери номинал:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_denominations_menu(currency),
    )

  elif call.data.startswith("confirm_apple_"):
    parts = call.data.split("_")
    currency = parts[2]
    nom = int(parts[3])
    item_key = f"apple_{currency}_{nom}"
    price = get_price(item_key)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            f"💳 Оплатить {price} ₽",
            callback_data=f"pay_apple_{currency}_{nom}",
        )
    )
    markup.add(
        InlineKeyboardButton(
            "❌ Отмена", callback_data=f"apple_curr_{currency}"
        )
    )

    bot.edit_message_text(
        f"🛒 **Подтверждение покупки**\n\nТовар: App Store & iTunes {nom}"
        f" {currency}\nК списанию: **{price} ₽**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup,
    )

  elif call.data.startswith("preconfirm_apple_"):
    parts = call.data.split("_")
    currency = parts[2]
    nom = int(parts[3])
    item_key = f"apple_{currency}_{nom}"
    price = get_price(item_key)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            f"✅ Оформить заказ ({price} ₽)",
            callback_data=f"manualpay_apple_{currency}_{nom}",
        )
    )
    markup.add(
        InlineKeyboardButton(
            "❌ Отмена", callback_data=f"apple_curr_{currency}"
        )
    )

    text = (
        f"🛒 **Оформление заказа**\n\nТовар: App Store & iTunes {nom}"
        f" {currency}\nСтоимость: **{price} ₽**\n\n📦 *Данный товар выдается после"
        " обработки заказа менеджером.*"
    )
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup,
    )

  elif call.data.startswith("manualpay_apple_"):
    parts = call.data.split("_")
    currency = parts[2]
    nom = int(parts[3])
    item_key = f"apple_{currency}_{nom}"
    final_price = get_price(item_key)
    user_balance = get_balance(call.from_user.id)

    if user_balance < final_price:
      return bot.answer_callback_query(
          call.id, "❌ Недостаточно средств на балансе!", show_alert=True
      )

    change_balance(call.from_user.id, -final_price)
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      item_name = f"App Store & iTunes {nom} {currency}"
      c.execute(
          "INSERT INTO history (user_id, item_name, code, price, purchase_time)"
          " VALUES (?, ?, ?, ?, ?)",
          (call.from_user.id, item_name, "", final_price, current_time),
      )
      conn.commit()

    bot.edit_message_text(
        f"✅ **Заказ успешно оформлен!**\n\nТовар: App Store & iTunes {nom}"
        f" {currency}\nСумма: **{final_price} ₽**\n\n⏳ Ваш заказ передан в"
        " обработку.\n📞 Менеджер: @Djabrail050",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )

    username = (
        f"@{call.from_user.username}" if call.from_user.username else "Скрыт"
    )
    admin_text = (
        f"🚨 **НОВЫЙ ЗАКАЗ!** 🚨\n\n👤 Пользователь: {username}\n🆔 ID:"
        f" `{call.from_user.id}`\n🛒 Товар: **{nom} {currency}**\n💰 Оплачено:"
        f" **{final_price} ₽**\n\n⚡️ Найди код и отправь пользователю."
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

  elif call.data.startswith("pay_apple_"):
    parts = call.data.split("_")
    currency = parts[2]
    nom = int(parts[3])
    item_key = f"apple_{currency}_{nom}"
    final_price = get_price(item_key)
    user_balance = get_balance(call.from_user.id)

    if user_balance < final_price:
      return bot.answer_callback_query(
          call.id, "❌ Недостаточно средств на балансе!", show_alert=True
      )

    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "SELECT id, code FROM codes WHERE item_key = ? LIMIT 1", (item_key,)
      )
      product = c.fetchone()

      if product is None:
        return bot.answer_callback_query(
            call.id,
            "😔 Кто-то успел купить последний код перед вами. Оформите заказ!",
            show_alert=True,
        )

      code_id, secret_code = product
      c.execute(
          "UPDATE users SET balance = balance - ? WHERE id = ?",
          (final_price, call.from_user.id),
      )
      c.execute("DELETE FROM codes WHERE id = ?", (code_id,))

      current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
      item_name = f"App Store & iTunes {nom} {currency}"
      c.execute(
          "INSERT INTO history (user_id, item_name, code, price, purchase_time)"
          " VALUES (?, ?, ?, ?, ?)",
          (
              call.from_user.id,
              item_name,
              secret_code,
              final_price,
              current_time,
          ),
      )
      conn.commit()

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "❓ Нужна инструкция по активации?",
            callback_data=f"instruct_{currency}",
        )
    )
    bot.edit_message_text(
        f"✅ **Успешная покупка!**\n\nТовар: App Store & iTunes {nom}"
        f" {currency}\nВаш код:\n`{secret_code}`",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь ID `{call.from_user.id}` купил {item_key} за"
        f" {final_price} ₽ (Автовыдача)",
        parse_mode="Markdown",
    )

  elif call.data.startswith("instruct_"):
    currency = call.data.split("_")[1]
    instructions = {
        "TRY": (
            "🇹🇷 **Инструкция для Турции:**\n1. Включите VPN Турции.\n2. В App"
            " Store смените регион на Турцию.\n3. Введите код."
        ),
        "USD": (
            "🇺🇸 **Инструкция для США:**\n1. Включите VPN США.\n2. В App Store"
            " смените регион на США.\n3. Введите код."
        ),
        "EUR": (
            "🇪🇺 **Инструкция для Европы:**\n1. Регион Apple ID должен быть"
            " европейским.\n2. В App Store введите код."
        ),
        "INR": (
            "🇮🇳 **Инструкция для Индии:**\n1. Включите VPN Индии.\n2. В App"
            " Store смените регион на Индию.\n3. Введите код."
        ),
    }
    bot.send_message(
        call.message.chat.id,
        instructions.get(currency, "Инструкция скоро появится."),
        parse_mode="Markdown",
    )
    bot.answer_callback_query(call.id)

  elif call.data.startswith("buy_custom_"):
    product_id = int(call.data.replace("buy_custom_", ""))
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name, price FROM custom_products WHERE id = ?", (product_id,))
      prod = c.fetchone()
      if not prod:
        return

      prod_name, price = prod
      item_key = f"custom_{product_id}"
      stock = get_stock_count(item_key)

      markup = InlineKeyboardMarkup()
      if stock > 0:
        markup.add(
            InlineKeyboardButton(
                f"💳 Оплатить {price} ₽",
                callback_data=f"pay_custom_{product_id}",
            )
        )
        markup.add(InlineKeyboardButton("❌ Отмена", callback_data="close_menu"))
        text = (
            f"🛒 **Подтверждение покупки**\n\nТовар: {prod_name}\nК списанию:"
            f" **{price} ₽**"
        )
      else:
        markup.add(
            InlineKeyboardButton(
                f"✅ Оформить заказ ({price} ₽)",
                callback_data=f"manualpay_custom_{product_id}",
            )
        )
        markup.add(InlineKeyboardButton("❌ Отмена", callback_data="close_menu"))
        text = (
            f"🛒 **Оформление заказа**\n\nТовар: {prod_name}\nСтоимость: **{price}"
            " ₽**\n\n📦 *Данный товар выдается после обработки заказа"
            " менеджером.*"
        )

      bot.edit_message_text(
          text,
          call.message.chat.id,
          call.message.message_id,
          parse_mode="Markdown",
          reply_markup=markup,
      )

  elif call.data.startswith("manualpay_custom_"):
    product_id = int(call.data.replace("manualpay_custom_", ""))
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name, price FROM custom_products WHERE id = ?", (product_id,))
      prod = c.fetchone()
      if not prod:
        return
      prod_name, price = prod

    user_balance = get_balance(call.from_user.id)
    if user_balance < price:
      return bot.answer_callback_query(
          call.id, "❌ Недостаточно средств на балансе!", show_alert=True
      )

    change_balance(call.from_user.id, -price)
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "INSERT INTO history (user_id, item_name, code, price, purchase_time)"
          " VALUES (?, ?, ?, ?, ?)",
          (call.from_user.id, prod_name, "", price, current_time),
      )
      conn.commit()

    bot.edit_message_text(
        f"✅ **Заказ успешно оформлен!**\n\nТовар: {prod_name}\nСумма: **{price}"
        f" ₽**\n\n⏳ Ваш заказ передан в обработку.\n📞 Менеджер: @Djabrail050",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )

    username = (
        f"@{call.from_user.username}" if call.from_user.username else "Скрыт"
    )
    admin_text = (
        f"🚨 **НОВЫЙ ЗАКАЗ (СВОЙ ТОВАР)!** 🚨\n\n👤 Пользователь:"
        f" {username}\n🆔 ID: `{call.from_user.id}`\n🛒 Товар:"
        f" **{prod_name}**\n💰 Оплачено: **{price} ₽**\n\n⚡️ Свяжитесь с"
        " клиентом и выдайте товар."
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

  elif call.data.startswith("pay_custom_"):
    product_id = int(call.data.replace("pay_custom_", ""))
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name, price FROM custom_products WHERE id = ?", (product_id,))
      prod = c.fetchone()
      if not prod:
        return
      prod_name, price = prod

    user_balance = get_balance(call.from_user.id)
    if user_balance < price:
      return bot.answer_callback_query(
          call.id, "❌ Недостаточно средств на балансе!", show_alert=True
      )

    item_key = f"custom_{product_id}"
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "SELECT id, code FROM codes WHERE item_key = ? LIMIT 1", (item_key,)
      )
      product_code = c.fetchone()

      if product_code is None:
        return bot.answer_callback_query(
            call.id,
            "😔 Товары закончились. Оформите заказ!",
            show_alert=True,
        )

      code_id, secret_code = product_code
      c.execute(
          "UPDATE users SET balance = balance - ? WHERE id = ?",
          (price, call.from_user.id),
      )
      c.execute("DELETE FROM codes WHERE id = ?", (code_id,))

      current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
      c.execute(
          "INSERT INTO history (user_id, item_name, code, price, purchase_time)"
          " VALUES (?, ?, ?, ?, ?)",
          (call.from_user.id, prod_name, secret_code, price, current_time),
      )
      conn.commit()

    bot.edit_message_text(
        f"✅ **Успешная покупка!**\n\nТовар:"
        f" {prod_name}\nВаш товар/код:\n`{secret_code}`",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )
    bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь ID `{call.from_user.id}` купил {prod_name} за"
        f" {price} ₽ (Автовыдача)",
        parse_mode="Markdown",
    )

  # ============ АДМИН ПАНЕЛЬ ============
  elif call.data == "admin_stats":
    today = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m") + "%"

    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT count(*) FROM users WHERE id != ?", (ADMIN_ID,))
      total = c.fetchone()[0]

      c.execute(
          "SELECT count(*) FROM users WHERE id != ? AND joined_date = ?",
          (ADMIN_ID, today),
      )
      today_count = c.fetchone()[0]

      c.execute(
          "SELECT count(*) FROM users WHERE id != ? AND joined_date LIKE ?",
          (ADMIN_ID, this_month),
      )
      month_count = c.fetchone()[0]

    stats_text = (
        "📊 **Статистика магазина**\n\n"
        f"👥 Всего пользователей: **{total}**\n"
        f"📅 Новых за этот месяц: **{month_count}**\n"
        f"🆕 Новых за сегодня: **{today_count}**\n\n"
        f"*(Твой аккаунт администратора в статистике не учитывается)*"
    )
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")
    )
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup,
    )

  elif call.data == "back_to_admin":
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

  elif call.data == "admin_add_cat":
    msg = bot.send_message(
        call.message.chat.id,
        "📂 Отправьте название новой категории (например: Roblox 👾):",
    )
    bot.register_next_step_handler(msg, process_add_category)

  elif call.data == "admin_add_prod":
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name FROM custom_categories")
      cats = c.fetchall()
      if not cats:
        bot.send_message(
            call.message.chat.id, "❌ Сначала создайте категорию!"
        )
        return
      markup = InlineKeyboardMarkup(row_width=2)
      for cat in cats:
        markup.add(
            InlineKeyboardButton(
                cat[0], callback_data=f"adm_selcat_{cat[0]}"
            )
        )
      bot.edit_message_text(
          "📦 Выберите категорию для нового товара:",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=markup,
      )

  elif call.data.startswith("adm_selcat_"):
    cat_name = call.data.replace("adm_selcat_", "")
    msg = bot.send_message(
        call.message.chat.id,
        f"Категория: **{cat_name}**\n📝 Отправьте название нового товара:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_add_prod_name, cat_name)

  elif call.data == "admin_price_cats":
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            "Турция", callback_data="admin_price_curr_TRY"
        ),
        InlineKeyboardButton("США", callback_data="admin_price_curr_USD"),
        InlineKeyboardButton(
            "Европа", callback_data="admin_price_curr_EUR"
        ),
        InlineKeyboardButton("Индия", callback_data="admin_price_curr_INR"),
    )
    bot.edit_message_text(
        "Выберите валюту (Ручное изменение):",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

  elif call.data.startswith("admin_price_curr_"):
    currency = call.data.split("_")[3]
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            f"{nom} {currency}"
            f" ({get_price(f'apple_{currency}_{nom}')}₽)",
            callback_data=f"admin_edit_price_apple_{currency}_{nom}",
        )
        for nom in APPLE_DENOMINATIONS[currency]
    ]
    markup.add(*buttons)
    markup.add(
        InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_price_cats"
        )
    )
    bot.edit_message_text(
        f"Номиналы {currency}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

  elif call.data.startswith("admin_edit_price_"):
    item_key = call.data.replace("admin_edit_price_", "")
    msg = bot.send_message(
        call.message.chat.id,
        f"Цена для **{item_key}**: {get_price(item_key)} ₽\nОтправьте новую"
        " цену (число):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_save_new_price, item_key)

  elif call.data == "admin_rate_cats":
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            "Турция (TRY)", callback_data="admin_rate_curr_TRY"
        ),
        InlineKeyboardButton(
            "США (USD)", callback_data="admin_rate_curr_USD"
        ),
        InlineKeyboardButton(
            "Европа (EUR)", callback_data="admin_rate_curr_EUR"
        ),
        InlineKeyboardButton(
            "Индия (INR)", callback_data="admin_rate_curr_INR"
        ),
    )
    bot.edit_message_text(
        "💱 Выберите валюту для обновления цен по курсу:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

  elif call.data.startswith("admin_rate_curr_"):
    currency = call.data.split("_")[3]
    msg = bot.send_message(
        call.message.chat.id,
        f"Выбрана валюта: **{currency}**\n\nОтправьте новый курс (сколько рублей"
        f" стоит 1 {currency}):\n*(Например: 100 или 2.5)*",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_save_new_rate, currency)

  elif call.data == "admin_add_code":
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            "Турция", callback_data="admin_code_curr_TRY"
        ),
        InlineKeyboardButton("США", callback_data="admin_code_curr_USD"),
        InlineKeyboardButton(
            "Европа", callback_data="admin_code_curr_EUR"
        ),
        InlineKeyboardButton("Индия", callback_data="admin_code_curr_INR"),
    )
    markup.add(
        InlineKeyboardButton(
            "🌟 Свои товары", callback_data="admin_code_custom_cats"
        )
    )
    bot.edit_message_text(
        "Выберите раздел для загрузки кода:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

  elif call.data == "admin_code_custom_cats":
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name FROM custom_categories")
      cats = c.fetchall()
      markup = InlineKeyboardMarkup(row_width=2)
      for cat in cats:
        markup.add(
            InlineKeyboardButton(
                cat[0], callback_data=f"adm_code_selcat_{cat[0]}"
            )
        )
      markup.add(
          InlineKeyboardButton("⬅️ Назад", callback_data="admin_add_code")
      )
      bot.edit_message_text(
          "Выберите категорию своих товаров:",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=markup,
      )

  elif call.data.startswith("adm_code_selcat_"):
    cat_name = call.data.replace("adm_code_selcat_", "")
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "SELECT id, name FROM custom_products WHERE category_name = ?",
          (cat_name,),
      )
      prods = c.fetchall()
      markup = InlineKeyboardMarkup(row_width=1)
      for p in prods:
        markup.add(
            InlineKeyboardButton(
                p[1], callback_data=f"admin_code_item_custom_{p[0]}"
            )
        )
      markup.add(
          InlineKeyboardButton(
              "⬅️ Назад", callback_data="admin_code_custom_cats"
          )
      )
      bot.edit_message_text(
          "Выберите товар для загрузки кода:",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=markup,
      )

  elif call.data.startswith("admin_code_curr_"):
    currency = call.data.split("_")[3]
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            f"{nom} {currency}",
            callback_data=f"admin_code_item_apple_{currency}_{nom}",
        )
        for nom in APPLE_DENOMINATIONS[currency]
    ]
    markup.add(*buttons)
    markup.add(
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_add_code")
    )
    bot.edit_message_text(
        f"Выберите номинал {currency}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

  elif call.data.startswith("admin_code_item_"):
    item_key = call.data.replace("admin_code_item_", "")
    msg = bot.send_message(
        call.message.chat.id,
        f"🔑 Отправьте код/товар для **{item_key}** (он будет выдан клиенту"
        " после оплаты):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_save_new_code, item_key)

  elif call.data == "admin_add_balance":
    msg = bot.send_message(
        call.message.chat.id,
        "Введите ID пользователя и сумму (например: 123456789 500):",
    )
    bot.register_next_step_handler(msg, process_add_balance)

  elif call.data == "admin_edit_rules":
    msg = bot.send_message(
        call.message.chat.id,
        "Отправьте новый текст для **Правил магазина**:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_edit_rules)

  elif call.data.startswith("topup_paid_"):
    amount = int(call.data.split("_")[2])
    bot.edit_message_text(
        f"Вы указали, что перевели {amount} ₽.",
        call.message.chat.id,
        call.message.message_id,
    )
    msg = bot.send_message(
        call.message.chat.id,
        "📸 Пожалуйста, отправьте **фотографию чека** или скриншот перевода в"
        " этот чат:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_receipt_photo, amount)

  elif call.data.startswith("adm_topup_ok_"):
    parts = call.data.split("_")
    target_user_id = int(parts[3])
    amount = int(parts[4])
    change_balance(target_user_id, amount)
    bot.edit_message_text(
        f"✅ Выдано {amount} ₽ для ID {target_user_id}",
        call.message.chat.id,
        call.message.message_id,
    )
    try:
      bot.send_message(
          target_user_id,
          f"✅ **Ваше пополнение подтверждено!**\n\nНа ваш баланс зачислено"
          f" **{amount} ₽**.",
          parse_mode="Markdown",
      )
    except Exception as e:
      print(f"Не удалось отправить уведомление пользователю: {e}")

  elif call.data.startswith("adm_topup_no_"):
    target_user_id = int(call.data.split("_")[3])
    bot.edit_message_text(
        f"❌ Отклонено для ID {target_user_id}",
        call.message.chat.id,
        call.message.message_id,
    )
    try:
      bot.send_message(
          target_user_id,
          "❌ **Ваше пополнение было отклонено администратором.**\n\nПроверьте"
          " правильность чека или обратитесь к менеджеру: **@Djabrail050**",
          parse_mode="Markdown",
      )
    except Exception as e:
      print(f"Не удалось отправить уведомление пользователю: {e}")

  elif call.data.startswith("adm_wd_ok_"):
    parts = call.data.split("_")
    bot.edit_message_text(
        f"✅ Выплачено {parts[4]} ₽ для ID {parts[3]}",
        call.message.chat.id,
        call.message.message_id,
    )
    try:
      bot.send_message(int(parts[3]), f"✅ Вывод {parts[4]} ₽ отправлен!")
    except:
      pass

  elif call.data.startswith("adm_wd_no_"):
    parts = call.data.split("_")
    change_balance(int(parts[3]), int(parts[4]))
    bot.edit_message_text(
        f"❌ Отклонен вывод {parts[4]} ₽ для ID {parts[3]}. Деньги возвращены.",
        call.message.chat.id,
        call.message.message_id,
    )


# ============ ФУНКЦИИ ВВОДА ТЕКСТА ============
def process_add_category(message):
  if is_menu_button(message.text):
    return handle_text(message)
  with sqlite3.connect("shop.db") as conn:
    c = conn.cursor()
    try:
      c.execute(
          "INSERT INTO custom_categories (name) VALUES (?)", (message.text,)
      )
      conn.commit()
      bot.send_message(
          message.chat.id,
          f"✅ Категория **{message.text}** добавлена! Она появится в меню"
          " 'Купить'.",
          parse_mode="Markdown",
      )
    except sqlite3.IntegrityError:
      bot.send_message(message.chat.id, "❌ Такая категория уже существует.")


def process_add_prod_name(message, cat_name):
  if is_menu_button(message.text):
    return handle_text(message)
  prod_name = message.text
  msg = bot.send_message(
      message.chat.id,
      f"Товар: **{prod_name}**\n💰 Отправьте цену товара в рублях (только"
      " число):",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(msg, process_add_prod_price, cat_name, prod_name)


def process_add_prod_price(message, cat_name, prod_name):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    price = int(message.text)
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      c.execute(
          "INSERT INTO custom_products (category_name, name, price) VALUES"
          " (?, ?, ?)",
          (cat_name, prod_name, price),
      )
      conn.commit()
    bot.send_message(
        message.chat.id,
        f"✅ Товар **{prod_name}** за **{price} ₽** успешно добавлен в"
        f" категорию **{cat_name}**!",
        parse_mode="Markdown",
    )
  except ValueError:
    bot.send_message(message.chat.id, "❌ Ошибка. Нужно отправить число.")


def process_save_new_rate(message, currency):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    new_rate = float(message.text.replace(",", "."))
    with sqlite3.connect("shop.db") as conn:
      c = conn.cursor()
      for nom in APPLE_DENOMINATIONS[currency]:
        item_key = f"apple_{currency}_{nom}"
        new_price = int(nom * new_rate)
        c.execute(
            "UPDATE prices SET price = ? WHERE item_key = ?",
            (new_price, item_key),
        )
      conn.commit()
    bot.send_message(
        message.chat.id,
        f"✅ Курс для **{currency}** установлен: **{new_rate} ₽**.\nВсе цены в"
        " этой категории успешно пересчитаны и обновлены!",
        parse_mode="Markdown",
    )
  except ValueError:
    bot.send_message(
        message.chat.id,
        "❌ Ошибка. Введите число (например: 100 или 2.5).",
    )


def process_receipt_photo(message, amount):
  if message.text and is_menu_button(message.text):
    return handle_text(message)

  if message.content_type != "photo":
    bot.send_message(
        message.chat.id,
        "❌ Вы не отправили фотографию. Пополнение отменено, попробуйте снова"
        " через меню.",
    )
    return

  photo_id = message.photo[-1].file_id
  bot.send_message(
      message.chat.id,
      f"⏳ Чек на {amount} ₽ отправлен. Ожидайте проверки менеджером.",
  )

  markup = InlineKeyboardMarkup()
  markup.add(
      InlineKeyboardButton(
          "✅ Выдать", callback_data=f"adm_topup_ok_{message.from_user.id}_{amount}"
      ),
      InlineKeyboardButton(
          "❌ Отклонить", callback_data=f"adm_topup_no_{message.from_user.id}"
      ),
  )
  caption = (
      f"🔔 **ПРОВЕРКА ОПЛАТЫ!**\n👤 ID: `{message.from_user.id}`\n💰 Сумма:"
      f" **{amount} ₽**\n\nВнимательно проверьте чек перед выдачей:"
  )
  bot.send_photo(
      ADMIN_ID,
      photo_id,
      caption=caption,
      parse_mode="Markdown",
      reply_markup=markup,
  )


def process_topup_amount(message):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    amount = int(message.text)
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            "✅ Я перевел деньги", callback_data=f"topup_paid_{amount}"
        )
    )
    bot.send_message(
        message.chat.id,
        f"💳 **Переведите {amount} ₽** сюда:\n`{PAYMENT_DETAILS}`\nЗатем нажмите"
        " кнопку.",
        parse_mode="Markdown",
        reply_markup=markup,
    )
  except:
    bot.send_message(message.chat.id, "❌ Ошибка. Введите число.")


def process_withdraw_amount(message, balance):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    amount = int(message.text)
    if amount <= 0 or amount > balance:
      return bot.send_message(message.chat.id, "❌ Неверная сумма.")
    msg = bot.send_message(
        message.chat.id, f"Выводим {amount} ₽. Отправьте реквизиты:"
    )
    bot.register_next_step_handler(msg, process_withdraw_details, amount)
  except:
    bot.send_message(message.chat.id, "❌ Введите число.")


def process_withdraw_details(message, amount):
  if is_menu_button(message.text):
    return handle_text(message)
  user_id = message.from_user.id
  change_balance(user_id, -amount)
  bot.send_message(message.chat.id, f"⏳ Заявка на вывод {amount} ₽ создана.")
  markup = InlineKeyboardMarkup().add(
      InlineKeyboardButton(
          "✅ Выплачено", callback_data=f"adm_wd_ok_{user_id}_{amount}"
      ),
      InlineKeyboardButton(
          "❌ Отклонить", callback_data=f"adm_wd_no_{user_id}_{amount}"
      ),
  )
  bot.send_message(
      ADMIN_ID,
      f"💸 **ВЫВОД!**\nID: `{user_id}`\nСумма:"
      f" **{amount} ₽**\nРеквизиты: `{message.text}`",
      parse_mode="Markdown",
      reply_markup=markup,
  )


def process_save_new_price(message, item_key):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    set_price(item_key, int(message.text))
    bot.send_message(
        message.chat.id, f"✅ Цена для {item_key} изменена на {message.text} ₽!"
    )
  except:
    bot.send_message(message.chat.id, "❌ Ошибка.")


def process_save_new_code(message, item_key):
  if is_menu_button(message.text):
    return handle_text(message)
  with sqlite3.connect("shop.db") as conn:
    conn.cursor().execute(
        "INSERT INTO codes (item_key, code) VALUES (?, ?)",
        (item_key, message.text.strip()),
    )
    conn.commit()
  bot.send_message(
      message.chat.id,
      "✅ Товар/Код успешно загружен в базу!",
      parse_mode="Markdown",
  )


def process_add_balance(message):
  if is_menu_button(message.text):
    return handle_text(message)
  try:
    user_id, amount = message.text.split()
    change_balance(int(user_id), int(amount))
    bot.send_message(
        message.chat.id, f"✅ Баланс {user_id} пополнен на {amount} ₽"
    )
  except:
    bot.send_message(message.chat.id, "❌ Ошибка. Формат: ID СУММА")


def process_edit_rules(message):
  if is_menu_button(message.text):
    return handle_text(message)
  set_rules(message.text)
  bot.send_message(
      message.chat.id,
      "✅ Правила магазина успешно обновлены!",
      parse_mode="Markdown",
  )


# ============ ЗАПУСК БОТА ============
if __name__ == "__main__":
  bot.remove_webhook()
  print("Бот успешно запущен в режиме консоли!")
  bot.infinity_polling()
