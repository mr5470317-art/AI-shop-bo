import os
import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем ключи и ID администратора
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Инициализация бота и клиента Gemini
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настраиваем API ключ
genai.configure(api_key=GEMINI_API_KEY)

# Конфигурация генерации
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 500,
}

# Словарь для хранения истории диалогов
user_sessions = {}

# Функция для чтения каталога из файла
def load_catalog():
    try:
        if os.path.exists("products.txt"):
            with open("products.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return ", ".join(lines)
        return "Асортимент тимчасово відсутній."
    except Exception as e:
        logging.error(f"Ошибка чтения файла каталога: {e}")
        return "Асортимент тимчасово відсутній."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Привіт! Я твій консультант у StyleHub. Як я можу тобі допомогти сьогодні?")

@dp.message(Command("reset"))
async def cmd_reset(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Історію очищено! Давайте почнемо спочатку.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_text = message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": user_text})

    try:
        catalog_text = load_catalog()
        
        # Системные инструкции (промпт)
        system_instruction = (
            f"Ти — професійний консультант StyleHub. ТЕКУЧИЙ АСОРИМЕНТ МАГАЗИНУ: [{catalog_text}].\n"
            "ПРАВИЛА:\n"
            "1. Продавай та пропонуй покупцям ВИКЛЮЧНО товари з поточного асортименту вище. Категорично заборонено вигадувати інші моделі, бренди чи товари, яких немає в цьому списку.\n"
            "2. Якщо клієнт просить змінити деталі (адресу, розмір) у вже оформленому замовленні — внеси зміну, обов'язково напиши фразу 'ЗАМОВЛЕННЯ ОНОВЛЕНО!' та підсумуй оновлені дані.\n"
            "3. Якщо клієнт хоче менеджера: запитай номер, перепитай підтвердження, після відповіді 'Так' напиши 'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО'.\n"
            "4. Якщо клієнт кидає номер телефону без контексту — запитай, для чого він (замовлення чи менеджер).\n"
            "5. ОФОРМЛЕННЯ (СУВОРО): Коли є всі дані — товар, колір, розмір, телефон ТА адреса доставки — тоді напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй. ЗАБОРОНЕНО писати 'ЗАМОВЛЕННЯ ПРИЙНЯТО', якщо клієнт ще не назвав адресу або телефон!\n"
            "Пиши виключно українською мовою, лаконічно."
        )

        # Создаем модель со встроенной системной инструкцией
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_instruction,
            generation_config=generation_config
        )

        # Форматируем историю для Gemini
        gemini_history = []
        for msg in user_sessions[user_id][:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Запускаем чат и отправляем сообщение
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_text)

        bot_response = response.text

        # Сохраняем ответ в историю
        user_sessions[user_id].append({"role": "model", "content": bot_response})
        await message.answer(bot_response)

        # Уведомление админу
        if any(marker in bot_response for marker in ["ЗАМОВЛЕННЯ ПРИЙНЯТО", "ЗАМОВЛЕННЯ ОНОВЛЕНО!", "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО"]):
            if ADMIN_ID and ADMIN_ID != 0:
                if "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО" in bot_response:
                    alert_title = "🚨 **КЛІЄНТ ПРОСИТЬ МЕНЕДЖЕРА!**"
                elif "ЗАМОВЛЕННЯ ОНОВЛЕНО!" in bot_response:
                    alert_title = "🔄 **ЗАМОВЛЕННЯ ОНОВЛЕНО!**"
                else:
                    alert_title = "📦 **НОВЕ ЗАМОВЛЕННЯ ПРИЙНЯТО!**"

                admin_text = (
                    f"{alert_title}\n\n"
                    f"👤 **Клієнт:** {message.from_user.full_name} (@{message.from_user.username}, ID: `{user_id}`)\n\n"
                    f"📋 **Деталі:**\n{bot_response}"
                )
                try:
                    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
                except Exception as admin_err:
                    logging.error(f"Помилка відправки адміну: {admin_err}")

    except Exception as e:
        logging.error(f"Ошибка API или сети: {e}")
        user_sessions[user_id] = []
        await message.answer("Ой, здається, сталася невеличка технічна помилка або я втомився. Давайте почнемо з чистого аркуша! Що вас цікавить?")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
