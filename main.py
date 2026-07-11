
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from anthropic import Anthropic

# Логирование для сервера
logging.basicConfig(level=logging.INFO)

# Безопасно подтягиваем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или ANTHROPIC_API_KEY в переменных окружения!")

# Инициализация Телеграм и клиента Claude
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Anthropic(api_key=ANTHROPIC_API_KEY)

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
    
    # Системный промпт для настройки характера Claude
    system_prompt = f"""Ти — професійний, ввічливий та корисний продавець-консультант магазину.
Ось актуальна інформація про товари, ціни та наявність:
{products_info}

Правила для тебе:
1. Відповідай клієнту українською мовою.
2. Використовуй лише інформацію зі списку вище. Якщо товару немає — так і кажи, не вигадуй.
3. Веди діалог природно, допомагай підібрати товар та заохочуй до покупки."""

    try:
        # Запрос к Claude API (используем быструю и умную модель Haiku)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message.text}
            ]
        )
        
        reply_text = response.content[0].text
        await message.answer(reply_text)
        
    except Exception as e:
        logging.error(f"Ошибка при запросе к Claude API: {e}")
        await message.answer("Вибачте, сталася тимчасова помилка зв'язку зі штучним інтелектом. Спробуйте пізніше.")

# Запуск поллинга
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
