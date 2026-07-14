import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

# Логирование для сервера
logging.basicConfig(level=logging.INFO)

# Безопасно подтягиваем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY в переменных окружения!")

# Инициализация Телеграм и клиента Groq
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Функция чтения файла с товарами
def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я твій інтелектуальний помічник-консультант. Готовий допомагати з вибором товарів.")

# Обработка текстовых сообщений
@dp.message(F.text)
async def handle_message(message: types.Message):
    products_info = get_products_data()
# Системный промпт для настройки характера ассистента
system_prompt = f"""Ти — професійний менеджер з продажу брендового одягу.
Ось актуальна інформація про товари:
{products_info}

Твій стиль спілкування:
1. Лаконічний, впевнений, діловий український стиль.
2. Жодних дивних зворотів, "кальки" з інших мов чи сленгу. Тільки чиста ділова українська мова.
3. Якщо клієнт запитує про розмір чи товар — давай чітку відповідь.
4. Не вигадуй зайвих питань, якщо клієнт уже назвав товар.
5. Завжди будь ввічливим, але тримай дистанцію професіонала."""


Правила для тебе:
1. Відповідай клієнту українською мовою.
2. Використовуй лише інформацію зі списку вище. Якщо товару немає — так і кажи, не вигадуй.
3. Веди діалог природно, допомагай підібрати товар та заохочуй до покупки."""

    try:
        # Запрос к Groq API (используем стабильную быструю модель)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.text}
            ]
        )
        
        reply_text = response.choices[0].message.content
        await message.answer(reply_text)
        
    except Exception as e:
        logging.error(f"Ошибка при запросе к Groq API: {e}")
        # Выводим реальный текст ошибки в чат для отладки
        await message.answer(f"Помилка: {str(e)}")

# Запуск поллинга
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
