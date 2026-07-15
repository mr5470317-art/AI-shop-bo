import os
import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
from groq import Groq

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем ключи (убедись, что они прописаны в переменных окружения Railway 
# или вставь их сюда прямо в кавычки для теста)
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_ТЕЛЕГРАМ_БОТА")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ТВОЙ_КЛЮЧ_GROQ")

# Инициализация бота и клиента Groq
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории диалогов пользователей
user_sessions = {}

# Системный промпт (роль бота)
SYSTEM_PROMPT = {
    "role": "system", 
  "content": "Ти — ввічливий та корисний консультант інтернет-магазину одягу та взуття StyleHub. Допомагай клієнтам з вибором товарів, відповідай коротко та по суті. Якщо тебе запитують про речі, не пов'язані з магазином (наприклад, автомобілі), ввічливо відмовляй і повертай розмову до асортименту."
   1 "Використовуй лише ті товари та моделі, які передані в базі даних (або перелічені нижче). Ніколи не вигадуй моделі чи бренди, яких немає в списку".
}

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
        # ЭКОНОМИЯ ТОКЕНОВ: берем только последние 6 сообщений из истории
        recent_history = user_sessions[user_id][-6:]

        # Отправляем запрос к Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[SYSTEM_PROMPT] + recent_history,
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
        # При любой ошибке (включая лимит токенов 429) сбрасываем историю конкретного юзера
        user_sessions[user_id] = []
        await message.answer("Ой, здається, сталася невеличка технічна помилка або я втомився. Давайте почнемо з чистого аркуша! Що вас цікавить?")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
