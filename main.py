import os
import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
from groq import Groq

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем ключи
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_ТЕЛЕГРАМ_БОТА")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ТВОЙ_КЛЮЧ_GROQ")

# Инициализация бота и клиента Groq
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории диалогов пользователей
user_sessions = {}

# Функция для чтения каталога из файла
def load_catalog():
    try:
        if os.path.exists("products.txt"):
            with open("products.txt", "r", encoding="utf-8") as f:
                # Читаем строки, убираем лишние пробелы и пустые строки
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

    # Инициализируем историю для нового пользователя, если её нет
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем сообщение пользователя в историю
    user_sessions[user_id].append({"role": "user", "content": user_text})

    try:
        # ЧИТАЕМ КАТАЛОГ ИЗ ФАЙЛА НА ЛЕТУ
        catalog_text = load_catalog()

        # ФОРМИРУЕМ СИСТЕМНЫЙ ПРОМПТ С ДАННЫМИ ИЗ ФАЙЛА
        system_prompt = {
            "role": "system", 
            "content": (
                f"Ти — професійний консультант StyleHub. ТЕКУЧИЙ АСОРИМЕНТ МАГАЗИНУ: [{catalog_text}].\n"
                "ПРАВИЛА:\n"
                "1. Продавай та пропонуй покупцям ВИКЛЮЧНО товари з поточного асортименту вище. Категорично заборонено вигадувати інші моделі, бренди чи товари, яких немає в цьому списку.\n"
                "2. Якщо клієнт просить змінити деталі (адресу, розмір) у вже оформленому замовленні — внеси зміну, обов'язково напиши фразу 'ЗАМОВЛЕННЯ ОНОВЛЕНО!' та підсумуй оновлені дані.\n"
                "3. Якщо клієнт хоче менеджера: запитай номер, перепитай підтвердження, після відповіді 'Так' напиши 'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО'.\n"
                "4. Якщо клієнт кидає номер телефону без контексту — запитай, для чого він (замовлення чи менеджер).\n"
                "5. ОФОРМЛЕННЯ: Коли є всі дані (товар, розмір, телефон, адреса) — напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй.\n"
                "Пиши виключно українською мовою, лаконічно."
            )
        }

        # ЭКОНОМИЯ ТОКЕНОВ: берем только последние 6 сообщений из истории
        recent_history = user_sessions[user_id][-6:]

        # Отправляем запрос к Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[system_prompt] + recent_history,
            temperature=0.7,
            max_tokens=500
        )

        bot_response = completion.choices[0].message.content

        # Добавляем ответ бота в историю
        user_sessions[user_id].append({"role": "assistant", "content": bot_response})

        # Отправляем ответ пользователю в Telegram
        await message.answer(bot_response)

    except Exception as e:
        logging.error(f"Ошибка API или сети: {e}")
        user_sessions[user_id] = []
        await message.answer("Ой, здається, сталася невеличка технічна помилка або я втомився. Давайте почнемо з чистого аркуша! Що вас цікавить?")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

