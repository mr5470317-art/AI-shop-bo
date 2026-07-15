import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
from groq import Groq

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и клиента Groq
BOT_TOKEN = "ТВОЙ_ТОКЕН_ТЕЛЕГРАМ_БОТА"
GROQ_API_KEY = "ТВОЙ_КЛЮЧ_GROQ"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории диалогов пользователей
user_sessions = {}

# Системный промпт (роль бота)
SYSTEM_PROMPT = {
    "role": "system", 
    "content": "Ти — ввічливий та корисний консультант інтернет-магазину одягу та взуття StyleHub. Допомагай клієнтам з вибором товарів, відповідай коротко та по суті. Якщо тебе запитують про речі, не пов'язані з магазином (наприклад, автомобілі), ввічливо відмовляй і повертай розмову до асортименту."
}

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    user_id = message.from_user.id
    # Сбрасываем историю при команде /start
    user_sessions[user_id] = []
    await message.answer("Привіт! Я твій консультант у StyleHub. Як я можу тобі допомогти сьогодні?")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_text = message.text

    # Если пользователь написал команду сброса
    if user_text.lower() == "/reset":
        user_sessions[user_id] = []
        await message.answer("Історію очищено! Давайте почнемо спочатку.")
        return

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
            model="llama-3.3-70b-versatile",  # Можешь поменять на "llama-3.1-8b-instant" для еще большей экономии
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
        # Если словили лимит токенов (429) или другую ошибку — сбрасываем битый хвост
        user_sessions[user_id] = []
        await message.answer("Ой, здається, я занадто багато думав і втомився. Давайте почнемо з чистого аркуша! Що вас цікавить з нашого асортименту?")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
