import os
import asyncio
import logging
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") # Твой ключ с OpenRouter
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Подключаемся к OpenRouter как к OpenAI
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Асортимент пустий."

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    system_instruction = f"Ти — консультант StyleHub. Асортимент: {get_products_data()}. Пиши грамотною українською."

    try:
        completion = await client.chat.completions.create(
            # Можешь менять модель на любую другую из списка OpenRouter
            model="google/gemini-2.0-flash-lite-preview-02-05:free", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message.text}
            ]
        )
        
        reply_text = completion.choices[0].message.content
        await message.answer(reply_text)
    except Exception as e:
        await message.answer(f"Помилка OpenRouter: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
