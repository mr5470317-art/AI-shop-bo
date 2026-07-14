import os
import asyncio
import logging
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") 
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Не найдены переменные окружения TELEGRAM_TOKEN или OPENROUTER_API_KEY!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Отключаем авто-повторы, чтобы не было долгих зависаний
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY.strip(),
    max_retries=0
)

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Асортимент наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    await message.answer("Привіт! Я твій інтелектуальний помічник-консультант StyleHub.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    system_instruction = f"Ти — консультант StyleHub. Асортимент: {get_products_data()}. Відповідай грамотною українською мовою."

    try:
        completion = await client.chat.completions.create(
            model="mistralai/mistral-nemo:free", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message.text}
            ]
        )
        
        reply_text = completion.choices[0].message.content
        await message.answer(reply_text)
    except Exception as e:
        logging.error(f"Ошибка OpenRouter: {e}")
        await message.answer(f"Помилка сервера: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
