import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ================= НАСТРОЙКИ =================
TOKEN = "8830470755:AAGSb6yPM7DSJc2KX5kNcmVo2W_OWDdpNYM" # ВСТАВЬ СВОЙ ТОКЕН!
ADMIN_ID = 1610696013  # Твой ID
PAYMENT_DETAILS = "Сбербанк / Т-Банк: +7 999 000-00-00 (Имя Фамилия)" 
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Настройки номиналов
APPLE_DENOMINATIONS = {
    'TRY': [10, 50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500],
    'USD': [1, 2, 3, 4, 5, 10, 15, 20, 50, 100],
    'EUR': [1, 5, 10, 20, 50, 100],
    'INR': [100, 200, 250, 500, 1000, 1500, 2000, 2500]
}
# =============================================

# ================= БАЗА ДАННЫХ ===============
def init_db():
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS prices (item_key TEXT PRIMARY KEY, price INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, item_key TEXT, code TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS history (user_id INTEGER, item_name TEXT, code TEXT, price INTEGER)')
        
        c.execute('SELECT count(*) FROM prices')
        if c.fetchone()[0] == 0:
            rates = {'TRY': 2.2, 'USD': 100.0, 'EUR': 150.0, 'INR': 1.2}
            for curr, denoms in APPLE_DENOMINATIONS.items():
                for nom in denoms:
                    item_key = f"apple_{curr}_{nom}"
                    price = int(nom * rates[curr])
                    c.execute('INSERT INTO prices (item_key, price) VALUES (?, ?)', (item_key, price))
        conn.commit()

def get_balance(user_id):
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        if result is None:
            c.execute('INSERT INTO users (id, balance) VALUES (?, 0)', (user_id,))
            conn.commit()
            return 0
        return result[0]

def change_balance(user_id, amount):
    balance = get_balance(user_id)
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET balance = ? WHERE id = ?', (balance + amount, user_id))
        conn.commit()

def get_price(item_key):
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('SELECT price FROM prices WHERE item_key = ?', (item_key,))
        res = c.fetchone()
        return res[0] if res else 999999

def set_price(item_key, new_price):
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE prices SET price = ? WHERE item_key = ?', (new_price, item_key))
        conn.commit()

def get_stock_count(item_key):
    with sqlite3.connect('shop.db') as conn:
        c = conn.cursor()
        c.execute('SELECT count(*) FROM codes WHERE item_key = ?', (item_key,))
        return c.fetchone()[0]
# =============================================

init_db()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 Купить"), KeyboardButton("👤 Профиль"))
    markup.add(KeyboardButton("ℹ️ Правила магазина"))
    return markup

def get_products_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("App Store & iTunes 🍏"), KeyboardButton("PUBG Mobile UC 🔫"))
    markup.add(KeyboardButton("Steam пополнение 🎮"), KeyboardButton("⬅️ Главное меню"))
    return markup

def get_profile_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("⬇️ Пополнить"), KeyboardButton("⬆️ Вывести"))
    markup.add(KeyboardButton("📜 История покупок"), KeyboardButton("⬅️ Главное меню"))
    return markup

def is_menu_button(text):
    menu_buttons = [
        "🛒 Купить", "👤 Профиль", "ℹ️ Правила магазина", "⬅️ Главное меню",
        "App Store & iTunes 🍏", "PUBG Mobile UC 🔫", "Steam пополнение 🎮",
        "⬇️ Пополнить", "⬆️ Вывести", "📜 История покупок"
    ]
    return text in menu_buttons or text.startswith("/")

def get_apple_currency_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Турция (TRY) 🇹🇷", callback_data="apple_curr_TRY"),
        InlineKeyboardButton("США (USD) 🇺🇸", callback_data="apple_curr_USD"),
        InlineKeyboardButton("Европа (EUR) 🇪🇺", callback_data="apple_curr_EUR"),
        InlineKeyboardButton("Индия (INR) 🇮🇳", callback_data="apple_curr_INR"),
        InlineKeyboardButton("❌ Закрыть", callback_data="close_menu")
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
        
        # Если товар есть - обычная покупка, если нет - предзаказ
        if stock > 0:
            callback = f"confirm_apple_{currency}_{nom}"
        else:
            callback = f"preconfirm_apple_{currency}_{nom}"
            
        buttons.append(InlineKeyboardButton(btn_text, callback_data=callback))
        
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("⬅️ Назад к валютам", callback_data="apple_back"))
    return markup

# ================= ОБРАБОТЧИКИ ТЕКСТА =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    get_balance(message.from_user.id)
    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! Добро пожаловать.", reply_markup=get_main_menu())

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id != ADMIN_ID: return
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💰 Изменить цены", callback_data="admin_price_cats"),
        InlineKeyboardButton("🔑 Загрузить код", callback_data="admin_add_code"),
        InlineKeyboardButton("➕ Выдать баланс вручную", callback_data="admin_add_balance")
    )
    bot.send_message(message.chat.id, "🛠 **Админ-панель**", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    text = message.text
    
    if text == "🛒 Купить":
        bot.send_message(message.chat.id, "Выберите категорию товаров:", reply_markup=get_products_menu())
        
    elif text == "👤 Профиль":
        balance = get_balance(message.from_user.id)
        bot.send_message(message.chat.id, f"👤 **Профиль:** {message.from_user.first_name}\n🆔 **ID:** `{message.from_user.id}`\n💰 **Ваш баланс:** {balance} ₽", parse_mode="Markdown", reply_markup=get_profile_menu())
        
    elif text == "⬅️ Главное меню":
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_menu())
        
    elif text == "ℹ️ Правила магазина":
        rules_text = (
            "📖 **Правила магазина и FAQ**\n\n"
            "**1. Гарантия:** Мы гарантируем 100% валидность всех выдаваемых кодов на момент покупки.\n"
            "**2. Активация:** Пожалуйста, активируйте код сразу после его получения.\n"
            "**3. Предзаказ:** Если нужного номинала нет, вы можете оформить ручной заказ. Среднее время выдачи — 15-30 минут.\n\n"
            "📞 **Поддержка:** По всем вопросам обращайтесь к нашему менеджеру: **@Djabrail050**"
        )
        bot.send_message(message.chat.id, rules_text, parse_mode="Markdown")
        
    elif text == "📜 История покупок":
        with sqlite3.connect('shop.db') as conn:
            c = conn.cursor()
            c.execute('SELECT item_name, code, price FROM history WHERE user_id = ? ORDER BY rowid DESC LIMIT 10', (message.from_user.id,))
            rows = c.fetchall()
            if not rows: bot.send_message(message.chat.id, "Вы еще ничего не покупали в нашем магазине 😔")
            else:
                history_text = "📜 **Ваши последние покупки:**\n\n"
                for i, row in enumerate(rows, 1):
                    history_text += f"*{i}. {row[0]}* — {row[2]} ₽\nКод: `{row[1]}`\n\n"
                bot.send_message(message.chat.id, history_text, parse_mode="Markdown")

    elif text == "App Store & iTunes 🍏":
        bot.send_message(message.chat.id, "Выбери валюту для App Store & iTunes:", reply_markup=get_apple_currency_menu())
        
    elif text in ["PUBG Mobile UC 🔫", "Steam пополнение 🎮"]:
        bot.send_message(message.chat.id, "🚧 Раздел находится в разработке!")
        
    elif text == "⬇️ Пополнить":
        msg = bot.send_message(message.chat.id, "Введите сумму, на которую хотите пополнить баланс (только число):")
        bot.register_next_step_handler(msg, process_topup_amount)
        
    elif text == "⬆️ Вывести":
        balance = get_balance(message.from_user.id)
        if balance <= 0: bot.send_message(message.chat.id, "❌ На вашем балансе нет средств для вывода.")
        else:
            msg = bot.send_message(message.chat.id, f"Ваш баланс: **{balance} ₽**\n\nВведите сумму для вывода (только число):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_withdraw_amount, balance)

# ================= ОБРАБОТЧИКИ КНОПОК =================
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "close_menu":
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data == "apple_back":
        bot.edit_message_text("Выбери валюту для App Store & iTunes:", call.message.chat.id, call.message.message_id, reply_markup=get_apple_currency_menu())
        
    elif call.data.startswith("apple_curr_"):
        currency = call.data.split("_")[2]
        bot.edit_message_text(f"Выбрана валюта: {currency}. Выбери номинал:", call.message.chat.id, call.message.message_id, reply_markup=get_denominations_menu(currency))
        
    elif call.data.startswith("confirm_apple_"):
        parts = call.data.split("_")
        currency = parts[2]
        nom = int(parts[3])
        item_key = f"apple_{currency}_{nom}"
        price = get_price(item_key)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"💳 Оплатить {price} ₽", callback_data=f"pay_apple_{currency}_{nom}"))
        markup.add(InlineKeyboardButton("❌ Отмена", callback_data=f"apple_curr_{currency}"))
        
        bot.edit_message_text(f"🛒 **Подтверждение покупки**\n\nТовар: App Store & iTunes {nom} {currency}\nК списанию: **{price} ₽**", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    # НОВАЯ ЛОГИКА: ПРЕДЗАКАЗ (когда товара нет)
    elif call.data.startswith("preconfirm_apple_"):
        parts = call.data.split("_")
        currency = parts[2]
        nom = int(parts[3])
        item_key = f"apple_{currency}_{nom}"
        price = get_price(item_key)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Оформить ручной заказ ({price} ₽)", callback_data=f"manualpay_apple_{currency}_{nom}"))
        markup.add(InlineKeyboardButton("❌ Выбрать другой номинал", callback_data=f"apple_curr_{currency}"))
        
        text = (
            f"🛒 **Оформление заказа**\n\n"
            f"Товар: App Store & iTunes {nom} {currency}\n"
            f"Моментальная выдача данного номинала временно недоступна 😔\n\n"
            f"Вы можете **оформить ручной заказ**. Деньги спишутся с баланса, и наш менеджер пришлет вам рабочий код личным сообщением в течение 15-30 минут."
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    # ОПЛАТА РУЧНОГО ЗАКАЗА
    elif call.data.startswith("manualpay_apple_"):
        parts = call.data.split("_")
        currency = parts[2]
        nom = int(parts[3])
        item_key = f"apple_{currency}_{nom}"
        final_price = get_price(item_key)
        user_balance = get_balance(call.from_user.id)
        
        if user_balance < final_price:
            return bot.answer_callback_query(call.id, "❌ Недостаточно средств на балансе!", show_alert=True)
            
        # Списываем баланс и добавляем в историю с пометкой
        change_balance(call.from_user.id, -final_price)
        with sqlite3.connect('shop.db') as conn:
            c = conn.cursor()
            item_name = f"App Store & iTunes {nom} {currency} (Заказ)"
            c.execute('INSERT INTO history (user_id, item_name, code, price) VALUES (?, ?, ?, ?)', 
                      (call.from_user.id, item_name, "[Ожидает выдачи менеджером]", final_price))
            conn.commit()
            
        # Сообщение клиенту
        bot.edit_message_text(
            f"✅ **Заявка на покупку создана!**\n\n"
            f"Товар: App Store & iTunes {nom} {currency}\n"
            f"Сумма: **{final_price} ₽**\n\n"
            f"⏳ Пожалуйста, ожидайте. Наш менеджер скоро свяжется с вами и пришлет код. Если у вас возникли вопросы, пишите: @Djabrail050",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
        
        # Уведомление АДМИНУ
        username = f"@{call.from_user.username}" if call.from_user.username else "Скрыт"
        admin_text = (
            f"🚨 **НОВЫЙ РУЧНОЙ ЗАКАЗ!** 🚨\n\n"
            f"👤 Пользователь: {username}\n"
            f"🆔 ID: `{call.from_user.id}`\n"
            f"🛒 Товар: **{nom} {currency}**\n"
            f"💰 Оплачено: **{final_price} ₽**\n\n"
            f"⚡️ Найди код для этого региона и отправь его пользователю в личные сообщения (или по ID)."
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

    # ОПЛАТА АВТОМАТИЧЕСКАЯ (когда товар есть)
    elif call.data.startswith("pay_apple_"):
        parts = call.data.split("_")
        currency = parts[2]
        nom = int(parts[3])
        item_key = f"apple_{currency}_{nom}"
        final_price = get_price(item_key)
        user_balance = get_balance(call.from_user.id)
        
        if user_balance < final_price:
            return bot.answer_callback_query(call.id, "❌ Недостаточно средств на балансе!", show_alert=True)
            
        with sqlite3.connect('shop.db') as conn:
            c = conn.cursor()
            c.execute('SELECT id, code FROM codes WHERE item_key = ? LIMIT 1', (item_key,))
            product = c.fetchone()
            
            if product is None:
                return bot.answer_callback_query(call.id, "😔 Кто-то успел купить последний код перед вами. Оформите ручной заказ!", show_alert=True)
                
            code_id, secret_code = product
            c.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (final_price, call.from_user.id))
            c.execute('DELETE FROM codes WHERE id = ?', (code_id,))
            
            item_name = f"App Store & iTunes {nom} {currency}"
            c.execute('INSERT INTO history (user_id, item_name, code, price) VALUES (?, ?, ?, ?)', 
                      (call.from_user.id, item_name, secret_code, final_price))
            conn.commit()
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❓ Нужна инструкция по активации?", callback_data=f"instruct_{currency}"))
        
        bot.edit_message_text(f"✅ **Успешная покупка!**\n\nТовар: App Store & iTunes {nom} {currency}\nВаш код:\n`{secret_code}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        bot.send_message(ADMIN_ID, f"💰 Пользователь ID `{call.from_user.id}` купил {item_key} за {final_price} ₽ (Автовыдача)", parse_mode="Markdown")

    elif call.data.startswith("instruct_"):
        currency = call.data.split("_")[1]
        instructions = {
            'TRY': "🇹🇷 **Инструкция для Турции:**\n1. Включите VPN Турции.\n2. В App Store смените регион на Турцию.\n3. Введите код.",
            'USD': "🇺🇸 **Инструкция для США:**\n1. Включите VPN США.\n2. В App Store смените регион на США.\n3. Введите код.",
            'EUR': "🇪🇺 **Инструкция для Европы:**\n1. Регион Apple ID должен быть европейским.\n2. В App Store введите код.",
            'INR': "🇮🇳 **Инструкция для Индии:**\n1. Включите VPN Индии.\n2. В App Store смените регион на Индию.\n3. Введите код."
        }
        bot.send_message(call.message.chat.id, instructions.get(currency, "Инструкция скоро появится."), parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # ============ АДМИН ПАНЕЛЬ И ЗАЯВКИ ============
    elif call.data == "admin_price_cats":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Турция", callback_data="admin_price_curr_TRY"), InlineKeyboardButton("США", callback_data="admin_price_curr_USD"),
            InlineKeyboardButton("Европа", callback_data="admin_price_curr_EUR"), InlineKeyboardButton("Индия", callback_data="admin_price_curr_INR")
        )
        bot.edit_message_text("Выберите валюту:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("admin_price_curr_"):
        currency = call.data.split("_")[3]
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = [InlineKeyboardButton(f"{nom} {currency} ({get_price(f'apple_{currency}_{nom}')}₽)", callback_data=f"admin_edit_price_apple_{currency}_{nom}") for nom in APPLE_DENOMINATIONS[currency]]
        markup.add(*buttons)
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_price_cats"))
        bot.edit_message_text(f"Номиналы {currency}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("admin_edit_price_"):
        item_key = call.data.replace("admin_edit_price_", "")
        msg = bot.send_message(call.message.chat.id, f"Цена для **{item_key}**: {get_price(item_key)} ₽\nОтправьте новую цену:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_save_new_price, item_key)

    elif call.data == "admin_add_code":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Турция", callback_data="admin_code_curr_TRY"), InlineKeyboardButton("США", callback_data="admin_code_curr_USD"),
            InlineKeyboardButton("Европа", callback_data="admin_code_curr_EUR"), InlineKeyboardButton("Индия", callback_data="admin_code_curr_INR")
        )
        bot.edit_message_text("Выберите валюту для кода:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("admin_code_curr_"):
        currency = call.data.split("_")[3]
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = [InlineKeyboardButton(f"{nom} {currency}", callback_data=f"admin_code_item_apple_{currency}_{nom}") for nom in APPLE_DENOMINATIONS[currency]]
        markup.add(*buttons)
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_add_code"))
        bot.edit_message_text(f"Выберите номинал {currency}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("admin_code_item_"):
        item_key = call.data.replace("admin_code_item_", "")
        msg = bot.send_message(call.message.chat.id, f"Отправьте код для **{item_key}**:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_save_new_code, item_key)

    elif call.data == "admin_add_balance":
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя и сумму (например: 123456789 500):")
        bot.register_next_step_handler(msg, process_add_balance)

    elif call.data.startswith("topup_paid_"):
        amount = int(call.data.split("_")[2])
        bot.edit_message_text(f"⏳ Заявка на {amount} ₽ отправлена. Проверка до 12 часов.", call.message.chat.id, call.message.message_id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Выдать", callback_data=f"adm_topup_ok_{call.from_user.id}_{amount}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_topup_no_{call.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 **ПОПОЛНЕНИЕ!**\nID: `{call.from_user.id}`\nСумма: **{amount} ₽**", parse_mode="Markdown", reply_markup=markup)

    elif call.data.startswith("adm_topup_ok_"):
        parts = call.data.split("_")
        change_balance(int(parts[3]), int(parts[4]))
        bot.edit_message_text(f"✅ Выдано {parts[4]} ₽ для ID {parts[3]}", call.message.chat.id, call.message.message_id)
        try: bot.send_message(int(parts[3]), f"✅ Баланс пополнен на {parts[4]} ₽!")
        except: pass

    elif call.data.startswith("adm_topup_no_"):
        bot.edit_message_text(f"❌ Отклонено для ID {call.data.split('_')[3]}", call.message.chat.id, call.message.message_id)

    elif call.data.startswith("adm_wd_ok_"):
        parts = call.data.split("_")
        bot.edit_message_text(f"✅ Выплачено {parts[4]} ₽ для ID {parts[3]}", call.message.chat.id, call.message.message_id)
        try: bot.send_message(int(parts[3]), f"✅ Вывод {parts[4]} ₽ отправлен!")
        except: pass

    elif call.data.startswith("adm_wd_no_"):
        parts = call.data.split("_")
        change_balance(int(parts[3]), int(parts[4]))
        bot.edit_message_text(f"❌ Отклонен вывод {parts[4]} ₽ для ID {parts[3]}. Деньги возвращены.", call.message.chat.id, call.message.message_id)

# ============ ФУНКЦИИ ВВОДА ТЕКСТА ============
def process_topup_amount(message):
    if is_menu_button(message.text): return handle_text(message)
    try:
        amount = int(message.text)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Я перевел деньги", callback_data=f"topup_paid_{amount}"))
        bot.send_message(message.chat.id, f"💳 **Переведите {amount} ₽** сюда:\n`{PAYMENT_DETAILS}`\nЗатем нажмите кнопку.", parse_mode="Markdown", reply_markup=markup)
    except: bot.send_message(message.chat.id, "❌ Ошибка. Введите число.")

def process_withdraw_amount(message, balance):
    if is_menu_button(message.text): return handle_text(message)
    try:
        amount = int(message.text)
        if amount <= 0 or amount > balance: return bot.send_message(message.chat.id, "❌ Неверная сумма.")
        msg = bot.send_message(message.chat.id, f"Выводим {amount} ₽. Отправьте реквизиты:")
        bot.register_next_step_handler(msg, process_withdraw_details, amount)
    except: bot.send_message(message.chat.id, "❌ Введите число.")

def process_withdraw_details(message, amount):
    if is_menu_button(message.text): return handle_text(message)
    user_id = message.from_user.id
    change_balance(user_id, -amount)
    bot.send_message(message.chat.id, f"⏳ Заявка на вывод {amount} ₽ создана.")
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Выплачено", callback_data=f"adm_wd_ok_{user_id}_{amount}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_wd_no_{user_id}_{amount}"))
    bot.send_message(ADMIN_ID, f"💸 **ВЫВОД!**\nID: `{user_id}`\nСумма: **{amount} ₽**\nРеквизиты: `{message.text}`", parse_mode="Markdown", reply_markup=markup)

def process_save_new_price(message, item_key):
    if is_menu_button(message.text): return handle_text(message)
    try:
        set_price(item_key, int(message.text))
        bot.send_message(message.chat.id, f"✅ Цена для {item_key} изменена на {message.text} ₽!")
    except: bot.send_message(message.chat.id, "❌ Ошибка.")

def process_save_new_code(message, item_key):
    if is_menu_button(message.text): return handle_text(message)
    with sqlite3.connect('shop.db') as conn:
        conn.cursor().execute('INSERT INTO codes (item_key, code) VALUES (?, ?)', (item_key, message.text.strip()))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ Код для **{item_key}** сохранен!", parse_mode="Markdown")

def process_add_balance(message):
    if is_menu_button(message.text): return handle_text(message)
    try:
        user_id, amount = message.text.split()
        change_balance(int(user_id), int(amount))
        bot.send_message(message.chat.id, f"✅ Баланс {user_id} пополнен на {amount} ₽")
    except: bot.send_message(message.chat.id, "❌ Ошибка.")

# ============ ЗАПУСК ВЕБХУКОВ FLASK ============
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "Бот работает 24/7!"

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'error', 403
