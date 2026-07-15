import os
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

# Убедись, что эти переменные в Railway заданы верно
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Используем модель, которая сейчас есть у всех на бесплатном тарифе
model = genai.GenerativeModel('gemini-1.5-flash')

@dp.message(F.text)
async def handle(message):
    try:
        # Промпт прямо в запросе, чтобы не было конфликтов версий
        prompt = f"Ти — консультант магазину. Асортимент: {open('products.txt', 'r', encoding='utf-8').read()}. Дотримуйся правил:..."
        response = model.generate_content(f"{prompt}\n\nКлієнт: {message.text}")
        await message.answer(response.text)
    except Exception as e:
        logging.error(e)
        await message.answer("Технічна помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
