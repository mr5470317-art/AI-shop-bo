import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Нет токенов в настройках!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Асортимент пустий."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    await message.answer("Привіт! Я консультант StyleHub.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    products_info = get_products_data()
    
    # Инструкция для бота
    system_instruction = f"Ти — консультант StyleHub. Асортимент: {products_info}. Пиши грамотною українською."
    
    # Используем модель 002 — это железный стандарт на сегодня
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-002:generateContent?key={GEMINI_API_KEY.strip()}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{system_instruction}\n\nКлієнт: {message.text}"}]
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                
                if resp.status == 200:
                    reply_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    await message.answer(reply_text)
                else:
                    await message.answer(f"Помилка: {data.get('error', {}).get('message', 'Невідома')}")
                
    except Exception as e:
        await message.answer(f"Критична помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
